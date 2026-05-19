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
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "tslm"))
    from tsrlm.config import TSRLMConfig  # noqa: WPS433

    data_paths = [args.train_sft, args.eval_sft, args.eval_raw, args.gold_jsonl]
    path_checks = {str(path): path.exists() for path in data_paths}
    train_summary = summarize_rows(args.train_sft) if args.train_sft.exists() else {"exists": False}
    eval_summary = summarize_rows(args.eval_sft) if args.eval_sft.exists() else {"exists": False}
    raw_eval_summary = summarize_rows(args.eval_raw) if args.eval_raw.exists() else {"exists": False}
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
    report = {
        "train_sft": str(args.train_sft),
        "eval_sft": str(args.eval_sft),
        "eval_raw": str(args.eval_raw),
        "gold_jsonl": str(args.gold_jsonl),
        "model_path": str(args.model_path),
        "model_path_exists": args.model_path.exists(),
        "path_checks": path_checks,
        "train_summary": train_summary,
        "eval_summary": eval_summary,
        "raw_eval_summary": raw_eval_summary,
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
        and report["model_path_exists"]
        and train_summary.get("n", 0) > 0
        and eval_summary.get("n", 0) > 0
        and train_summary.get("missing_required_count", 1) == 0
        and eval_summary.get("missing_required_count", 1) == 0
        and raw_eval_summary.get("n", 0) > 0
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
