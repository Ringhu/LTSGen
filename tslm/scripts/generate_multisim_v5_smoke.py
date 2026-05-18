#!/usr/bin/env python3
"""Generate captions from a MultiSim-v5 smoke checkpoint with channel padding."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import torch

from tsrlm.config import TSRLMConfig
from tsrlm.models import TSReportLM


ARTIFACT_MARKERS = [
    re.compile(r"\bHuman\b\s*:?", re.IGNORECASE),
    re.compile(r"\bAssistant\b\s*:?", re.IGNORECASE),
    re.compile(r"\bUser\b\s*:?", re.IGNORECASE),
    re.compile(r"\bQuestion\b\s*:?", re.IGNORECASE),
    re.compile(r"\bOptions?\b\s*:?", re.IGNORECASE),
    re.compile(r"\bAnswer\b\s*:?", re.IGNORECASE),
]


def load_jsonl(path: Path, *, limit: int = 0) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
                if limit and len(rows) >= limit:
                    break
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or row.get("multisim_source_domain") or row.get("domain") or "unknown")


def pad_values(rows: list[dict[str, Any]], target_num_vars: int) -> tuple[torch.Tensor, torch.Tensor]:
    seqs = [torch.tensor(row["values"], dtype=torch.float32) for row in rows]
    lengths = [seq.shape[0] for seq in seqs]
    dims = [int(seq.shape[-1]) for seq in seqs]
    if any(dim > target_num_vars for dim in dims):
        raise ValueError(f"Observed dim exceeds target_num_vars={target_num_vars}: {dims}")
    out = torch.zeros((len(seqs), max(lengths), target_num_vars), dtype=torch.float32)
    mask = torch.zeros((len(seqs), max(lengths)), dtype=torch.bool)
    for idx, seq in enumerate(seqs):
        out[idx, : seq.shape[0], : seq.shape[-1]] = seq
        mask[idx, : seq.shape[0]] = True
    return out, mask


def chunks(rows: list[dict[str, Any]], batch_size: int):
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


def clean_caption(text: str, max_sentences: int = 1) -> str:
    text = (text or "").strip()
    for marker in ARTIFACT_MARKERS:
        match = marker.search(text)
        if match and match.start() > 0:
            text = text[: match.start()].strip()
    for sep in ("\n", "\r"):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
    text = re.sub(r"\s+", " ", text)
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return " ".join(parts[: max(max_sentences, 1)]).strip()


def maybe_apply_lora_from_ckpt(model: TSReportLM, ckpt_dir: Path) -> None:
    lora_path = ckpt_dir / "lora_config.json"
    if not lora_path.exists():
        return
    try:
        from peft import LoraConfig, TaskType, get_peft_model
    except Exception as exc:  # noqa: BLE001
        raise ImportError("peft is required to load LoRA checkpoint.") from exc
    cfg = json.loads(lora_path.read_text(encoding="utf-8"))
    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=int(cfg["r"]),
        lora_alpha=int(cfg["alpha"]),
        lora_dropout=float(cfg["dropout"]),
        target_modules=list(cfg["target_modules"]),
        bias="none",
    )
    model.llm = get_peft_model(model.llm, lora_cfg)


def summarize(preds: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, int] = {}
    empty = 0
    for pred in preds:
        by_source[pred["merge_source_name"]] = by_source.get(pred["merge_source_name"], 0) + 1
        if not pred["pred_caption"]:
            empty += 1
    return {
        "n": len(preds),
        "by_source": by_source,
        "empty_caption_rate": round(empty / len(preds), 4) if preds else 0.0,
        "mean_caption_chars": round(sum(len(pred["pred_caption"]) for pred in preds) / len(preds), 1) if preds else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_jsonl", required=True)
    parser.add_argument("--checkpoint_dir", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--max_new_tokens", type=int, default=48)
    parser.add_argument("--repetition_penalty", type=float, default=1.12)
    parser.add_argument("--no_repeat_ngram_size", type=int, default=4)
    parser.add_argument("--clean_max_sentences", type=int, default=1)
    parser.add_argument("--device", default="")
    args = parser.parse_args()

    ckpt = Path(args.checkpoint_dir)
    cfg = TSRLMConfig.load(ckpt / "tsrlm_config.json")
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
    model = TSReportLM(cfg, freeze_llm=False, torch_dtype=dtype).to(device)
    maybe_apply_lora_from_ckpt(model, ckpt)
    state = torch.load(ckpt / "pytorch_model.bin", map_location="cpu")
    keys = model.load_state_dict(state, strict=False)
    model.eval()
    torch.set_grad_enabled(False)

    rows = load_jsonl(Path(args.raw_jsonl), limit=args.limit)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    preds = []
    for batch in chunks(rows, args.batch_size):
        values, mask = pad_values(batch, target_num_vars=cfg.ts_num_vars)
        prompts = [row["prompt"] for row in batch]
        outs = model.generate(
            values=values.to(device),
            ts_attn_mask=mask.to(device),
            prompt=prompts,
            max_new_tokens=args.max_new_tokens,
            temperature=0.0,
            top_p=1.0,
            top_k=0,
            repetition_penalty=args.repetition_penalty,
            no_repeat_ngram_size=args.no_repeat_ngram_size,
        )
        if isinstance(outs, str):
            outs = [outs]
        for row, raw_caption in zip(batch, outs):
            preds.append(
                {
                    "id": row["id"],
                    "split": row["split"],
                    "domain": row.get("domain", ""),
                    "merge_source_name": source_name(row),
                    "multisim_source_domain": row.get("multisim_source_domain", ""),
                    "task_family": row["task_family"],
                    "question": row["question"],
                    "options": row["options"],
                    "gold_answer": row["answer"],
                    "gold_answer_label": row["answer_label"],
                    "target_caption": row.get("target_caption") or row.get("oracle_evidence_caption") or row.get("output", ""),
                    "pred_caption": clean_caption(raw_caption, max_sentences=args.clean_max_sentences),
                    "pred_caption_raw": raw_caption,
                }
            )
    write_jsonl(out_dir / "predictions.jsonl", preds)
    report = {
        "raw_jsonl": args.raw_jsonl,
        "checkpoint_dir": args.checkpoint_dir,
        "load_state": {
            "missing_keys": len(keys.missing_keys),
            "unexpected_keys": len(keys.unexpected_keys),
            "loaded_state_keys": len(state),
        },
        "caption_metrics": summarize(preds),
    }
    (out_dir / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
