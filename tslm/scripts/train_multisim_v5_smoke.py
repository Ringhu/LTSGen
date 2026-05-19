#!/usr/bin/env python3
"""Bounded MultiSim-v5 QCC training smoke with safe channel padding."""
from __future__ import annotations

import argparse
import inspect
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import torch
from torch.utils.data import DataLoader, Sampler
from transformers import Trainer, TrainingArguments

from tsrlm.config import TSRLMConfig
from tsrlm.data.dataset import TSSFTDataset
from tsrlm.models import TSReportLM


def row_group_key(row: dict[str, Any], key: str) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    if key == "value_dim":
        values = row.get("values", [])
        first = values[0] if values else []
        return str(len(first) if isinstance(first, list) else 1)
    return str(row.get(key) or meta.get(key) or row.get("multisim_source_domain") or row.get("domain") or "unknown")


class GroupedBatchSampler(Sampler[list[int]]):
    def __init__(self, rows: list[dict[str, Any]], batch_size: int, group_key: str, seed: int, drop_last: bool) -> None:
        self.rows = rows
        self.batch_size = int(batch_size)
        self.group_key = group_key
        self.seed = int(seed)
        self.drop_last = bool(drop_last)
        groups: dict[str, list[int]] = {}
        for idx, row in enumerate(rows):
            groups.setdefault(row_group_key(row, group_key), []).append(idx)
        self.groups = groups

    def __iter__(self) -> Iterator[list[int]]:
        rng = random.Random(self.seed)
        batches: list[list[int]] = []
        for _, indices in sorted(self.groups.items()):
            local = list(indices)
            rng.shuffle(local)
            for start in range(0, len(local), self.batch_size):
                batch = local[start : start + self.batch_size]
                if len(batch) == self.batch_size or (batch and not self.drop_last):
                    batches.append(batch)
        rng.shuffle(batches)
        yield from batches

    def __len__(self) -> int:
        total = 0
        for indices in self.groups.values():
            total += len(indices) // self.batch_size
            if len(indices) % self.batch_size and not self.drop_last:
                total += 1
        return total


def pad_values(values: list[torch.Tensor], target_num_vars: int) -> dict[str, torch.Tensor]:
    lengths = torch.tensor([item.shape[0] for item in values], dtype=torch.long)
    observed_dims = [int(item.shape[1]) for item in values]
    if any(dim > target_num_vars for dim in observed_dims):
        raise ValueError(f"Observed dim exceeds target_num_vars={target_num_vars}: {observed_dims}")
    t_max = int(lengths.max().item())
    out = values[0].new_zeros((len(values), t_max, target_num_vars))
    mask = torch.zeros((len(values), t_max), dtype=torch.bool)
    var_mask = torch.zeros((len(values), target_num_vars), dtype=torch.bool)
    for idx, item in enumerate(values):
        t, d = item.shape
        out[idx, :t, :d] = item
        mask[idx, :t] = True
        var_mask[idx, :d] = True
    return {
        "values": out,
        "ts_attn_mask": mask,
        "ts_lengths": lengths,
        "value_dim": torch.tensor(observed_dims, dtype=torch.long),
        "var_mask": var_mask,
    }


@dataclass
class MultiSimV5Collator:
    tokenizer: Any
    target_num_vars: int = 4
    max_text_length: int = 512
    max_prompt_length: int = 256
    add_eos: bool = True

    def _bos_id(self) -> int:
        if self.tokenizer.bos_token_id is not None:
            return int(self.tokenizer.bos_token_id)
        if self.tokenizer.eos_token_id is not None:
            return int(self.tokenizer.eos_token_id)
        raise ValueError("Tokenizer has neither BOS nor EOS token.")

    def _eos_id(self) -> int:
        if self.tokenizer.eos_token_id is not None:
            return int(self.tokenizer.eos_token_id)
        return self._bos_id()

    def _encode(self, prompt: str, output: str) -> dict[str, torch.Tensor]:
        prompt_ids = self.tokenizer(prompt, add_special_tokens=False)["input_ids"][: self.max_prompt_length]
        output_ids = self.tokenizer(output, add_special_tokens=False)["input_ids"]
        reserve = 1 + len(prompt_ids) + (1 if self.add_eos else 0)
        output_ids = output_ids[: max(self.max_text_length - reserve, 0)]
        ids = [self._bos_id()] + prompt_ids + output_ids
        labels = [-100] * (1 + len(prompt_ids)) + output_ids
        if self.add_eos:
            ids.append(self._eos_id())
            labels.append(self._eos_id())
        return {
            "input_ids": torch.tensor(ids, dtype=torch.long),
            "attention_mask": torch.ones(len(ids), dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
            "prompt_len": torch.tensor(1 + len(prompt_ids), dtype=torch.long),
        }

    def __call__(self, batch: list[dict[str, Any]]) -> dict[str, Any]:
        ts = pad_values([item["values"] for item in batch], self.target_num_vars)
        encoded = [self._encode(item["prompt"], item["output"]) for item in batch]
        input_ids = torch.nn.utils.rnn.pad_sequence(
            [item["input_ids"] for item in encoded],
            batch_first=True,
            padding_value=int(self.tokenizer.pad_token_id),
        )
        attention_mask = torch.nn.utils.rnn.pad_sequence(
            [item["attention_mask"] for item in encoded],
            batch_first=True,
            padding_value=0,
        )
        labels = torch.nn.utils.rnn.pad_sequence(
            [item["labels"] for item in encoded],
            batch_first=True,
            padding_value=-100,
        )
        return {
            **ts,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
            "prompt_lens": torch.stack([item["prompt_len"] for item in encoded]),
            "ids": [item["id"] for item in batch],
            "meta": [item.get("meta") for item in batch],
        }


class MultiSimGroupedTrainer(Trainer):
    def __init__(self, *args, source_group_key: str = "", sampler_seed: int = 42, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.source_group_key = source_group_key
        self.sampler_seed = int(sampler_seed)

    def get_train_dataloader(self):
        if not self.source_group_key:
            return super().get_train_dataloader()
        if self.train_dataset is None:
            raise ValueError("training requires a train_dataset")
        return DataLoader(
            self.train_dataset,
            batch_sampler=GroupedBatchSampler(
                self.train_dataset.rows,
                batch_size=self.args.train_batch_size,
                group_key=self.source_group_key,
                seed=self.sampler_seed,
                drop_last=self.args.dataloader_drop_last,
            ),
            collate_fn=self.data_collator,
            num_workers=self.args.dataloader_num_workers,
            pin_memory=self.args.dataloader_pin_memory,
        )


def maybe_apply_lora(model: TSReportLM, args: argparse.Namespace) -> Optional[dict[str, Any]]:
    if args.lora_r <= 0:
        return None
    try:
        from peft import LoraConfig, TaskType, get_peft_model
    except Exception as exc:  # noqa: BLE001
        raise ImportError("peft is required for LoRA training") from exc
    target_modules = [item.strip() for item in args.lora_target_modules.split(",") if item.strip()]
    cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=target_modules,
        bias="none",
    )
    model.llm = get_peft_model(model.llm, cfg)
    model.llm.print_trainable_parameters()
    return {
        "r": args.lora_r,
        "alpha": args.lora_alpha,
        "dropout": args.lora_dropout,
        "target_modules": target_modules,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_jsonl", required=True)
    parser.add_argument("--eval_jsonl", default="")
    parser.add_argument("--llm_name_or_path", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--trust_remote_code", action="store_true")
    parser.add_argument("--encoder_type", default="patchtst", choices=["patchtst", "chronos2"])
    parser.add_argument("--bridge_type", default="prefix", choices=["prefix", "xattn"])
    parser.add_argument("--ts_num_vars", type=int, default=4)
    parser.add_argument("--target_num_vars", type=int, default=4)
    parser.add_argument("--ts_patch_len", type=int, default=16)
    parser.add_argument("--ts_d_model", type=int, default=128)
    parser.add_argument("--ts_layers", type=int, default=2)
    parser.add_argument("--ts_heads", type=int, default=4)
    parser.add_argument("--prefix_tokens", type=int, default=8)
    parser.add_argument("--resampler_layers", type=int, default=1)
    parser.add_argument("--resampler_heads", type=int, default=4)
    parser.add_argument("--n_stat_tokens", type=int, default=2)
    parser.add_argument("--prefix_alpha_init", type=float, default=0.1)
    parser.add_argument("--num_train_epochs", type=float, default=1.0)
    parser.add_argument("--max_steps", type=int, default=-1)
    parser.add_argument("--per_device_train_batch_size", type=int, default=1)
    parser.add_argument("--per_device_eval_batch_size", type=int, default=1)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=1)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--warmup_ratio", type=float, default=0.03)
    parser.add_argument("--max_text_length", type=int, default=224)
    parser.add_argument("--max_prompt_length", type=int, default=320)
    parser.add_argument("--logging_steps", type=int, default=1)
    parser.add_argument("--eval_steps", type=int, default=50)
    parser.add_argument("--save_strategy", default="no", choices=["no", "steps", "epoch"])
    parser.add_argument("--save_steps", type=int, default=500)
    parser.add_argument("--save_total_limit", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--source_group_key", default="merge_source_name", choices=["", "merge_source_name", "multisim_source_domain", "domain", "value_dim"])
    parser.add_argument("--max_train_samples", type=int, default=0)
    parser.add_argument("--max_eval_samples", type=int, default=0)
    parser.add_argument("--freeze_llm", action="store_true")
    parser.add_argument("--save_trainable_only", action="store_true")
    parser.add_argument("--gradient_checkpointing", action="store_true")
    parser.add_argument("--bf16", action="store_true")
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--lora_r", type=int, default=8)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--lora_target_modules", default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    cfg = TSRLMConfig(
        llm_name_or_path=args.llm_name_or_path,
        encoder_type=args.encoder_type,
        bridge_type=args.bridge_type,
        ts_num_vars=args.ts_num_vars,
        ts_patch_len=args.ts_patch_len,
        ts_d_model=args.ts_d_model,
        ts_layers=args.ts_layers,
        ts_heads=args.ts_heads,
        prefix_tokens=args.prefix_tokens,
        resampler_layers=args.resampler_layers,
        resampler_heads=args.resampler_heads,
        n_stat_tokens=args.n_stat_tokens,
        prefix_alpha_init=args.prefix_alpha_init,
        max_text_length=args.max_text_length,
    )
    dtype = torch.bfloat16 if args.bf16 else (torch.float16 if args.fp16 else None)
    model = TSReportLM(cfg, freeze_llm=args.freeze_llm, trust_remote_code=args.trust_remote_code, torch_dtype=dtype)
    lora_cfg = maybe_apply_lora(model, args)

    if args.gradient_checkpointing:
        try:
            model.llm.gradient_checkpointing_enable()
        except Exception:
            pass
        model.llm.config.use_cache = False

    train_ds = TSSFTDataset(args.train_jsonl, max_samples=args.max_train_samples or None)
    eval_ds = TSSFTDataset(args.eval_jsonl, max_samples=args.max_eval_samples or None) if args.eval_jsonl else None
    collator = MultiSimV5Collator(
        tokenizer=model.tokenizer,
        target_num_vars=args.target_num_vars,
        max_text_length=args.max_text_length,
        max_prompt_length=args.max_prompt_length,
    )
    ta_kwargs = dict(
        output_dir=str(outdir),
        num_train_epochs=args.num_train_epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_strategy=args.save_strategy,
        eval_steps=args.eval_steps if eval_ds is not None else None,
        save_total_limit=args.save_total_limit,
        fp16=args.fp16,
        bf16=args.bf16,
        seed=args.seed,
        remove_unused_columns=False,
        report_to=[],
        dataloader_pin_memory=True,
    )
    sig = inspect.signature(TrainingArguments.__init__)
    ta_kwargs["eval_strategy" if "eval_strategy" in sig.parameters else "evaluation_strategy"] = "steps" if eval_ds is not None else "no"
    if "save_safetensors" in sig.parameters:
        ta_kwargs["save_safetensors"] = False
    trainer = MultiSimGroupedTrainer(
        model=model,
        args=TrainingArguments(**ta_kwargs),
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
        source_group_key=args.source_group_key,
        sampler_seed=args.seed,
    )
    trainer.train()

    final_dir = outdir / "final_model"
    final_dir.mkdir(parents=True, exist_ok=True)
    state = {name: param.detach().cpu() for name, param in model.named_parameters() if param.requires_grad} if args.save_trainable_only else model.state_dict()
    torch.save(state, final_dir / "pytorch_model.bin")
    cfg.save(final_dir / "tsrlm_config.json")
    if lora_cfg is not None:
        (final_dir / "lora_config.json").write_text(json.dumps(lora_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    model.tokenizer.save_pretrained(final_dir)
    run_report = {
        "train_jsonl": args.train_jsonl,
        "eval_jsonl": args.eval_jsonl,
        "output_dir": args.output_dir,
        "source_group_key": args.source_group_key,
        "target_num_vars": args.target_num_vars,
        "ts_num_vars": args.ts_num_vars,
        "max_steps": args.max_steps,
        "train_rows": len(train_ds),
        "eval_rows": len(eval_ds) if eval_ds is not None else 0,
        "final_model": str(final_dir),
    }
    (outdir / "multisim_v5_train_smoke_report.json").write_text(json.dumps(run_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(run_report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
