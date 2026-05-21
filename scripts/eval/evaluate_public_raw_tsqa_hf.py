#!/usr/bin/env python3
"""Evaluate Public Raw TSQA v4 with local HuggingFace causal LMs.

This is the fallback path for A100 Qwen evaluation when an OpenAI-compatible
vLLM/SWIFT endpoint is unavailable or incompatible with the installed Qwen
model family. It preserves the same prediction/metrics schema as
``evaluate_public_raw_tsqa_llm.py`` so downstream summary and comparison scripts
can be reused unchanged.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from evaluate_public_raw_tsqa_llm import (  # type: ignore
    DEFAULT_CANONICAL,
    DEFAULT_LLM_VIEW,
    DEFAULT_OUT_BASE,
    ROOT,
    SYSTEM_PROMPT,
    aggregate,
    build_eval_items,
    canonical_by_id,
    load_jsonl,
    merge_rows,
    parse_answer,
    safe_name,
    select_rows,
    write_json,
    write_jsonl,
)


def prompt_report(items: list[dict[str, Any]], rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    lengths = [len(item["prompt"]) for item in items]
    by_lang = Counter(item["language"] for item in items)
    dataset = str(args.llm_view.relative_to(ROOT) if args.llm_view.is_relative_to(ROOT) else args.llm_view)
    return {
        "dataset": dataset,
        "provider": "hf",
        "model": args.model_name or args.model_path,
        "model_path": args.model_path,
        "n_rows": len(rows),
        "n_prompts": len(items),
        "languages": dict(by_lang),
        "prompt_chars": {
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "mean": round(statistics.mean(lengths), 1) if lengths else 0,
        },
        "by_domain": dict(Counter(row["domain"] for row in rows)),
        "answer_distribution": dict(Counter(row["answer"] for row in rows)),
        "dry_run": bool(args.dry_run),
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "torch_dtype": args.torch_dtype,
    }


def dtype_from_arg(torch_module: Any, value: str) -> Any:
    if value == "auto":
        return "auto"
    mapping = {
        "float16": torch_module.float16,
        "bfloat16": torch_module.bfloat16,
        "float32": torch_module.float32,
    }
    if value not in mapping:
        raise SystemExit(f"unsupported --torch_dtype={value}")
    return mapping[value]


def load_model(args: argparse.Namespace) -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    dtype = dtype_from_arg(torch, args.torch_dtype)
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
    model_kwargs: dict[str, Any] = {
        "trust_remote_code": True,
        "device_map": args.device_map,
    }
    if dtype != "auto":
        model_kwargs["torch_dtype"] = dtype
    else:
        model_kwargs["torch_dtype"] = "auto"
    model = AutoModelForCausalLM.from_pretrained(args.model_path, **model_kwargs)
    model.eval()
    return tokenizer, model


def build_chat_input(tokenizer: Any, item: dict[str, Any]) -> Any:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": item["prompt"]},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return f"{SYSTEM_PROMPT}\n\n{item['prompt']}\n\nAnswer JSON:"


def generate_one(tokenizer: Any, model: Any, item: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    import torch

    text = build_chat_input(tokenizer, item)
    started = time.time()
    encoded = tokenizer(text, return_tensors="pt", truncation=args.truncate, max_length=args.max_input_tokens)
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    input_len = int(encoded["input_ids"].shape[-1])
    gen_kwargs: dict[str, Any] = {
        "max_new_tokens": args.max_new_tokens,
        "do_sample": args.temperature > 0,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if args.temperature > 0:
        gen_kwargs["temperature"] = args.temperature
        gen_kwargs["top_p"] = args.top_p
    with torch.inference_mode():
        output = model.generate(**encoded, **gen_kwargs)
    raw_text = tokenizer.decode(output[0][input_len:], skip_special_tokens=True).strip()
    pred, pred_label, reason = parse_answer(raw_text)
    latency = time.time() - started
    return {
        **{key: item[key] for key in ("id", "source_canonical_id", "language", "domain", "task_family")},
        "model": args.model_name or args.model_path,
        "provider": "hf",
        "gold_answer": item["gold_answer"],
        "gold_answer_label": item["gold_answer_label"],
        "pred_answer": pred,
        "pred_answer_label": pred_label,
        "correct": pred == item["gold_answer"],
        "reason": reason[:1000],
        "raw_response": raw_text,
        "prompt_chars": len(item["prompt"]),
        "input_tokens": input_len,
        "latency_sec": round(latency, 3),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    llm_rows = load_jsonl(args.llm_view)
    rows = merge_rows(llm_rows, canonical_by_id(args.canonical))
    rows = select_rows(rows, max_items=args.max_items, per_domain=args.per_domain, seed=args.seed)
    languages = ["en", "zh"] if args.languages == "both" else [args.languages]
    items = build_eval_items(rows, languages)
    report = prompt_report(items, rows, args)

    run_name = args.run_name or f"hf_{safe_name(args.model_name or args.model_path)}_{args.languages}_{len(rows)}"
    out_dir = args.out_dir or (DEFAULT_OUT_BASE / run_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = out_dir / "predictions.jsonl"
    metrics_path = out_dir / "metrics.json"
    write_json(out_dir / "prompt_report.json", report)
    write_jsonl(
        out_dir / "prompt_preview.jsonl",
        [
            {
                "id": item["id"],
                "language": item["language"],
                "domain": item["domain"],
                "prompt_chars": len(item["prompt"]),
                "prompt_preview": item["prompt"][:1200],
            }
            for item in items[: args.preview_count]
        ],
    )
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report

    existing_predictions: list[dict[str, Any]] = []
    done_keys: set[tuple[str, str]] = set()
    if args.resume and predictions_path.is_file():
        existing_predictions = load_jsonl(predictions_path)
        done_keys = {(row["id"], row["language"]) for row in existing_predictions}
        print(f"[resume] loaded {len(existing_predictions)} existing predictions")
    elif predictions_path.exists():
        predictions_path.unlink()

    remaining_items = [item for item in items if (item["id"], item["language"]) not in done_keys]
    tokenizer, model = load_model(args)
    predictions = list(existing_predictions)
    started = time.time()
    for idx, item in enumerate(remaining_items, start=1):
        try:
            result = generate_one(tokenizer, model, item, args)
        except Exception as exc:  # noqa: BLE001
            result = {
                **{key: item[key] for key in ("id", "source_canonical_id", "language", "domain", "task_family")},
                "model": args.model_name or args.model_path,
                "provider": "hf",
                "gold_answer": item["gold_answer"],
                "gold_answer_label": item["gold_answer_label"],
                "pred_answer": "",
                "pred_answer_label": "",
                "correct": False,
                "reason": "",
                "raw_response": "",
                "error": repr(exc),
                "prompt_chars": len(item["prompt"]),
                "latency_sec": 0.0,
            }
        predictions.append(result)
        write_jsonl(predictions_path, sorted(predictions, key=lambda row: (row["id"], row["language"])))
        if args.progress_every > 0 and idx % args.progress_every == 0:
            print(f"[progress] {idx}/{len(remaining_items)} newly evaluated; total {len(predictions)}/{len(items)}")

    predictions.sort(key=lambda row: (row["id"], row["language"]))
    metrics = aggregate(predictions, report, time.time() - started)
    write_jsonl(predictions_path, predictions)
    write_json(metrics_path, metrics)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_view", type=Path, default=DEFAULT_LLM_VIEW)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--out_dir", type=Path, default=None)
    parser.add_argument("--run_name", default="")
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--model_name", default="")
    parser.add_argument("--languages", default="both", choices=["en", "zh", "both"])
    parser.add_argument("--max_items", type=int, default=0, help="0 means all rows")
    parser.add_argument("--per_domain", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260521)
    parser.add_argument("--max_new_tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top_p", type=float, default=0.9)
    parser.add_argument("--torch_dtype", default="bfloat16", choices=["auto", "float16", "bfloat16", "float32"])
    parser.add_argument("--device_map", default="auto")
    parser.add_argument("--max_input_tokens", type=int, default=32768)
    parser.add_argument("--truncate", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--preview_count", type=int, default=4)
    parser.add_argument("--progress_every", type=int, default=10)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
