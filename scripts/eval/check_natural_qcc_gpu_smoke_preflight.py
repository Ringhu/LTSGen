#!/usr/bin/env python3
"""Preflight checks for the natural QCC GPU smoke run.

Run this on the machine that will launch TS-RLM/Qwen training. It verifies the
small natural-QCC SFT assets, local model path, CUDA capacity, bridge support,
and the generated-caption QA evaluator before spending GPU time.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAIN = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "smoke_sft/natural_qcc_probe_train_dev_sft.jsonl"
)
DEFAULT_EVAL = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "smoke_sft/natural_qcc_probe_eval_test_sft.jsonl"
)
DEFAULT_RAW_EVAL = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "smoke_sft/natural_qcc_probe_eval_test_raw.jsonl"
)
DEFAULT_GOLD = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "natural_qcc_probe_positive.jsonl"
)
DEFAULT_MODEL = Path("/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507")
DEFAULT_OUT = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "gpu_smoke_preflight.json"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def value_dim(row: dict[str, Any]) -> int:
    values = row.get("values") or []
    if not values:
        return 0
    first = values[0]
    return len(first) if isinstance(first, list) else 1


def summarize_rows(path: Path) -> dict[str, Any]:
    rows = load_jsonl(path)
    required = ("id", "values", "prompt", "output")
    missing = [
        {"id": row.get("id", f"row{idx}"), "missing": [key for key in required if key not in row or row[key] in ("", [], None)]}
        for idx, row in enumerate(rows)
        if any(key not in row or row[key] in ("", [], None) for key in required)
    ]
    return {
        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "exists": path.exists(),
        "n": len(rows),
        "missing_required_count": len(missing),
        "missing_required_examples": missing[:5],
        "value_dim_counts": dict(Counter(str(value_dim(row)) for row in rows)),
        "split_counts": dict(Counter(str(row.get("split", "")) for row in rows)),
    }


def load_tokenizer(model_path: Path) -> Any | None:
    try:
        from transformers import AutoTokenizer
    except Exception:  # noqa: BLE001
        return None
    try:
        return AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)
    except Exception:  # noqa: BLE001
        return None


def supervised_preview(tokenizer: Any, output_ids: list[int], eos_id: int | None, *, limit: int = 120) -> str:
    ids = list(output_ids)
    if eos_id is not None:
        ids.append(int(eos_id))
    text = tokenizer.decode(ids, skip_special_tokens=True) if ids else ""
    return " ".join(text.split())[:limit]


def token_budget_row(
    row: dict[str, Any],
    *,
    tokenizer: Any,
    max_text_length: int,
    max_prompt_length: int,
    add_eos: bool,
) -> dict[str, Any]:
    prompt_full = tokenizer(str(row.get("prompt", "")), add_special_tokens=False)["input_ids"]
    output_full = tokenizer(str(row.get("output", "")), add_special_tokens=False)["input_ids"]
    prompt_kept = prompt_full[:max_prompt_length]
    reserve = 1 + len(prompt_kept) + (1 if add_eos else 0)
    output_budget = max(max_text_length - reserve, 0)
    output_kept = output_full[:output_budget]
    eos_id = int(tokenizer.eos_token_id) if add_eos and tokenizer.eos_token_id is not None else None
    return {
        "id": row.get("id", ""),
        "prompt_full_tokens": len(prompt_full),
        "prompt_kept_tokens": len(prompt_kept),
        "prompt_truncated": len(prompt_full) > len(prompt_kept),
        "output_full_tokens": len(output_full),
        "output_kept_tokens": len(output_kept),
        "output_truncated": len(output_kept) < len(output_full),
        "labels_non_ignored": len(output_kept) + (1 if add_eos else 0),
        "reserve_tokens": reserve,
        "needed_tokens": 1 + len(prompt_full) + len(output_full) + (1 if add_eos else 0),
        "supervised_text_preview": supervised_preview(tokenizer, output_kept, eos_id),
    }


def summarize_token_budget(
    path: Path,
    *,
    tokenizer: Any | None,
    max_text_length: int,
    max_prompt_length: int,
    add_eos: bool,
    preview_rows: int = 5,
) -> dict[str, Any]:
    if tokenizer is None:
        return {
            "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
            "checked": False,
            "reason": "tokenizer_unavailable",
        }
    rows = load_jsonl(path)
    items = [
        token_budget_row(
            row,
            tokenizer=tokenizer,
            max_text_length=max_text_length,
            max_prompt_length=max_prompt_length,
            add_eos=add_eos,
        )
        for row in rows
    ]
    if not items:
        return {
            "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
            "checked": True,
            "n": 0,
        }
    zero_output = [item for item in items if item["output_kept_tokens"] == 0]
    output_truncated = [item for item in items if item["output_truncated"]]
    prompt_truncated = [item for item in items if item["prompt_truncated"]]
    eos_only = [item for item in items if item["supervised_text_preview"] == ""]
    return {
        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "checked": True,
        "n": len(items),
        "max_text_length": max_text_length,
        "max_prompt_length": max_prompt_length,
        "add_eos": add_eos,
        "zero_output_kept": len(zero_output),
        "zero_output_kept_rate": round(len(zero_output) / len(items), 4),
        "output_truncated": len(output_truncated),
        "output_truncated_rate": round(len(output_truncated) / len(items), 4),
        "prompt_truncated": len(prompt_truncated),
        "prompt_truncated_rate": round(len(prompt_truncated) / len(items), 4),
        "eos_only_supervision": len(eos_only),
        "mean_prompt_full_tokens": round(sum(item["prompt_full_tokens"] for item in items) / len(items), 2),
        "mean_prompt_kept_tokens": round(sum(item["prompt_kept_tokens"] for item in items) / len(items), 2),
        "mean_output_full_tokens": round(sum(item["output_full_tokens"] for item in items) / len(items), 2),
        "mean_output_kept_tokens": round(sum(item["output_kept_tokens"] for item in items) / len(items), 2),
        "min_output_kept_tokens": min(item["output_kept_tokens"] for item in items),
        "max_output_kept_tokens": max(item["output_kept_tokens"] for item in items),
        "max_needed_tokens": max(item["needed_tokens"] for item in items),
        "examples": items[:preview_rows],
        "zero_output_examples": zero_output[:preview_rows],
        "output_truncated_examples": output_truncated[:preview_rows],
        "prompt_truncated_examples": prompt_truncated[:preview_rows],
    }


def command_output(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, check=False, text=True, capture_output=True, timeout=20)
    except Exception as exc:  # noqa: BLE001
        return 127, repr(exc)
    text = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode, text[-4000:]


def cuda_report() -> dict[str, Any]:
    report: dict[str, Any] = {"torch_import": False, "cuda_available": False, "devices": []}
    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        report["error"] = repr(exc)
        return report
    report["torch_import"] = True
    report["cuda_available"] = bool(torch.cuda.is_available())
    if torch.cuda.is_available():
        for idx in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(idx)
            report["devices"].append(
                {
                    "index": idx,
                    "name": props.name,
                    "total_memory_gb": round(props.total_memory / (1024**3), 2),
                }
            )
    code, text = command_output(["nvidia-smi"])
    report["nvidia_smi_returncode"] = code
    report["nvidia_smi_tail"] = text
    return report


def module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def looks_like_hf_model_id(path: Path) -> bool:
    text = str(path)
    return not path.is_absolute() and "/" in text and not text.startswith(".")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_sft", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--eval_sft", type=Path, default=DEFAULT_EVAL)
    parser.add_argument("--eval_raw", type=Path, default=DEFAULT_RAW_EVAL)
    parser.add_argument("--gold_jsonl", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--model_path", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--bridge_type", default="prefix")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--min_gpu_mem_gb", type=float, default=20.0)
    parser.add_argument("--max_text_length", type=int, default=224)
    parser.add_argument("--max_prompt_length", type=int, default=320)
    parser.add_argument("--allow_output_truncation", action="store_true")
    parser.add_argument("--allow_prompt_truncation", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "tslm"))
    from tsrlm.config import TSRLMConfig  # noqa: WPS433

    data_paths = [args.train_sft, args.eval_sft, args.eval_raw, args.gold_jsonl]
    path_checks = {str(path): path.exists() for path in data_paths}
    train_summary = summarize_rows(args.train_sft) if args.train_sft.exists() else {"exists": False}
    eval_summary = summarize_rows(args.eval_sft) if args.eval_sft.exists() else {"exists": False}
    raw_eval_summary = summarize_rows(args.eval_raw) if args.eval_raw.exists() else {"exists": False}
    tokenizer = load_tokenizer(args.model_path) if args.model_path.exists() or looks_like_hf_model_id(args.model_path) else None
    train_token_budget = (
        summarize_token_budget(
            args.train_sft,
            tokenizer=tokenizer,
            max_text_length=args.max_text_length,
            max_prompt_length=args.max_prompt_length,
            add_eos=True,
        )
        if args.train_sft.exists()
        else {"checked": False, "reason": "train_sft_missing"}
    )
    eval_token_budget = (
        summarize_token_budget(
            args.eval_sft,
            tokenizer=tokenizer,
            max_text_length=args.max_text_length,
            max_prompt_length=args.max_prompt_length,
            add_eos=True,
        )
        if args.eval_sft.exists()
        else {"checked": False, "reason": "eval_sft_missing"}
    )
    token_budget_pass = bool(
        train_token_budget.get("checked")
        and eval_token_budget.get("checked")
        and train_token_budget.get("zero_output_kept", 1) == 0
        and eval_token_budget.get("zero_output_kept", 1) == 0
        and (args.allow_output_truncation or train_token_budget.get("output_truncated", 1) == 0)
        and (args.allow_output_truncation or eval_token_budget.get("output_truncated", 1) == 0)
        and (args.allow_prompt_truncation or train_token_budget.get("prompt_truncated", 1) == 0)
        and (args.allow_prompt_truncation or eval_token_budget.get("prompt_truncated", 1) == 0)
    )
    cuda = cuda_report()
    max_gpu_mem = max((item["total_memory_gb"] for item in cuda.get("devices", [])), default=0.0)

    supported_bridge = args.bridge_type in {"prefix", "xattn"}
    cfg_constructible = False
    cfg_error = ""
    try:
        TSRLMConfig(llm_name_or_path=str(args.model_path), bridge_type=args.bridge_type, ts_num_vars=4)
        cfg_constructible = True
    except Exception as exc:  # noqa: BLE001
        cfg_error = repr(exc)

    evaluator_path = ROOT / "scripts/eval/evaluate_natural_qcc_predictions.py"
    model_path_exists = args.model_path.exists()
    model_is_hf_id = looks_like_hf_model_id(args.model_path)
    model_reference_ok = model_path_exists or model_is_hf_id
    report = {
        "train_sft": str(args.train_sft),
        "eval_sft": str(args.eval_sft),
        "eval_raw": str(args.eval_raw),
        "gold_jsonl": str(args.gold_jsonl),
        "model_path": str(args.model_path),
        "model_path_exists": model_path_exists,
        "model_is_hf_id": model_is_hf_id,
        "model_reference_ok": model_reference_ok,
        "path_checks": path_checks,
        "train_summary": train_summary,
        "eval_summary": eval_summary,
        "raw_eval_summary": raw_eval_summary,
        "token_budget": {
            "max_text_length": args.max_text_length,
            "max_prompt_length": args.max_prompt_length,
            "allow_output_truncation": args.allow_output_truncation,
            "allow_prompt_truncation": args.allow_prompt_truncation,
            "tokenizer_loaded": tokenizer is not None,
            "train": train_token_budget,
            "eval": eval_token_budget,
            "token_budget_pass": token_budget_pass,
        },
        "cuda": cuda,
        "min_gpu_mem_gb": args.min_gpu_mem_gb,
        "max_gpu_mem_gb": max_gpu_mem,
        "has_required_gpu_memory": max_gpu_mem >= args.min_gpu_mem_gb,
        "bridge_type": args.bridge_type,
        "bridge_supported_by_current_tsrlm": supported_bridge,
        "tsrlm_config_constructible": cfg_constructible,
        "tsrlm_config_error": cfg_error,
        "python_modules": {
            "torch": module_exists("torch"),
            "transformers": module_exists("transformers"),
            "peft": module_exists("peft"),
        },
        "evaluator_exists": evaluator_path.exists(),
    }
    report["preflight_pass"] = (
        all(path_checks.values())
        and report["model_reference_ok"]
        and train_summary.get("n", 0) > 0
        and eval_summary.get("n", 0) > 0
        and train_summary.get("missing_required_count", 1) == 0
        and eval_summary.get("missing_required_count", 1) == 0
        and raw_eval_summary.get("n", 0) > 0
        and token_budget_pass
        and report["has_required_gpu_memory"]
        and supported_bridge
        and cfg_constructible
        and report["python_modules"]["torch"]
        and report["python_modules"]["transformers"]
        and report["evaluator_exists"]
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["preflight_pass"] else 1)


if __name__ == "__main__":
    main()
