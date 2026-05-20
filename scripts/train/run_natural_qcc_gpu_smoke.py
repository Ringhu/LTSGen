#!/usr/bin/env python3
"""Run or dry-run the natural-QCC GPU smoke training pipeline.

Pipeline:
1. preflight
2. TS-RLM/Qwen smoke training
3. caption generation on eval raw rows
4. natural-QCC QA evaluation of generated captions

Use --dry_run on machines without the GPU/model environment to write the exact
commands that should be run on A100/3090.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519"
DEFAULT_TRAIN = BASE / "smoke_sft/natural_qcc_probe_train_dev_sft.jsonl"
DEFAULT_EVAL = BASE / "smoke_sft/natural_qcc_probe_eval_test_sft.jsonl"
DEFAULT_EVAL_RAW = BASE / "smoke_sft/natural_qcc_probe_eval_test_raw.jsonl"
DEFAULT_GOLD = BASE / "natural_qcc_probe_positive.jsonl"
DEFAULT_MODEL = Path("/cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507")
DEFAULT_RUN_DIR = BASE / "tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def run_command(cmd: list[str], *, cwd: Path, dry_run: bool) -> dict[str, Any]:
    item: dict[str, Any] = {
        "cmd": cmd,
        "cmd_string": " ".join(shlex.quote(part) for part in cmd),
        "cwd": str(cwd),
        "dry_run": dry_run,
    }
    if dry_run:
        item.update({"returncode": None, "stdout_tail": "", "stderr_tail": "", "skipped": True})
        return item
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)
    item.update(
        {
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
            "skipped": False,
        }
    )
    return item


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def maybe_load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_sft", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--eval_sft", type=Path, default=DEFAULT_EVAL)
    parser.add_argument("--eval_raw", type=Path, default=DEFAULT_EVAL_RAW)
    parser.add_argument("--gold_jsonl", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--model_path", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--run_dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--bridge_type", default="prefix")
    parser.add_argument("--target_num_vars", type=int, default=4)
    parser.add_argument("--ts_num_vars", type=int, default=4)
    parser.add_argument("--num_train_epochs", type=float, default=1.0)
    parser.add_argument("--train_batch_size", type=int, default=1)
    parser.add_argument("--eval_batch_size", type=int, default=1)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4)
    parser.add_argument("--max_new_tokens", type=int, default=48)
    parser.add_argument("--clean_max_sentences", type=int, default=2)
    parser.add_argument("--min_gpu_mem_gb", type=float, default=20.0)
    parser.add_argument(
        "--qa_evaluator",
        choices=["strict", "semantic"],
        default="strict",
        help="Use the strict answer-label bridge or deterministic semantic bridge for generated-caption QA.",
    )
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--skip_preflight", action="store_true")
    args = parser.parse_args()

    preflight_json = args.run_dir / "preflight.json"
    generate_dir = args.run_dir / "generate_eval_test_clean"
    ruleqa_dir = generate_dir / "rule_qa"
    pipeline_plan = args.run_dir / "natural_qcc_smoke_pipeline_plan.json"
    pipeline_summary = args.run_dir / "natural_qcc_smoke_pipeline_summary.json"

    commands: dict[str, list[str]] = {
        "preflight": [
            sys.executable,
            "scripts/eval/check_natural_qcc_gpu_smoke_preflight.py",
            "--train_sft",
            rel(args.train_sft),
            "--eval_sft",
            rel(args.eval_sft),
            "--eval_raw",
            rel(args.eval_raw),
            "--gold_jsonl",
            rel(args.gold_jsonl),
            "--model_path",
            str(args.model_path),
            "--bridge_type",
            args.bridge_type,
            "--min_gpu_mem_gb",
            str(args.min_gpu_mem_gb),
            "--out",
            rel(preflight_json),
        ],
        "train": [
            sys.executable,
            "tslm/scripts/train_multisim_v5_smoke.py",
            "--train_jsonl",
            rel(args.train_sft),
            "--eval_jsonl",
            rel(args.eval_sft),
            "--llm_name_or_path",
            str(args.model_path),
            "--output_dir",
            rel(args.run_dir),
            "--trust_remote_code",
            "--bridge_type",
            args.bridge_type,
            "--ts_num_vars",
            str(args.ts_num_vars),
            "--target_num_vars",
            str(args.target_num_vars),
            "--freeze_llm",
            "--save_trainable_only",
            "--bf16",
            "--num_train_epochs",
            str(args.num_train_epochs),
            "--per_device_train_batch_size",
            str(args.train_batch_size),
            "--per_device_eval_batch_size",
            str(args.eval_batch_size),
            "--gradient_accumulation_steps",
            str(args.gradient_accumulation_steps),
            "--source_group_key",
            "merge_source_name",
        ],
        "generate": [
            sys.executable,
            "tslm/scripts/generate_multisim_v5_smoke.py",
            "--raw_jsonl",
            rel(args.eval_raw),
            "--checkpoint_dir",
            rel(args.run_dir / "final_model"),
            "--out_dir",
            rel(generate_dir),
            "--batch_size",
            "1",
            "--max_new_tokens",
            str(args.max_new_tokens),
            "--clean_max_sentences",
            str(args.clean_max_sentences),
        ],
    }
    qa_script = (
        "scripts/eval/evaluate_natural_qcc_semantic_predictions.py"
        if args.qa_evaluator == "semantic"
        else "scripts/eval/evaluate_natural_qcc_predictions.py"
    )
    commands["qa"] = [
        sys.executable,
        qa_script,
        "--predictions_jsonl",
        rel(generate_dir / "predictions.jsonl"),
        "--gold_jsonl",
        rel(args.gold_jsonl),
        "--out_dir",
        rel(ruleqa_dir),
        "--caption_field",
        "pred_caption",
        "--splits",
        "test",
    ]

    plan = {
        "dry_run": args.dry_run,
        "run_dir": rel(args.run_dir),
        "qa_evaluator": args.qa_evaluator,
        "commands": {name: " ".join(shlex.quote(part) for part in cmd) for name, cmd in commands.items()},
    }
    write_json(pipeline_plan, plan)

    results: dict[str, Any] = {"dry_run": args.dry_run, "run_dir": rel(args.run_dir), "steps": {}}
    if not args.skip_preflight:
        results["steps"]["preflight"] = run_command(commands["preflight"], cwd=ROOT, dry_run=args.dry_run)
        preflight = maybe_load_json(preflight_json)
        results["preflight"] = preflight
        if not args.dry_run and (not preflight or not preflight.get("preflight_pass")):
            results["stopped_after"] = "preflight"
            write_json(pipeline_summary, results)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            raise SystemExit(1)

    for step in ("train", "generate", "qa"):
        result = run_command(commands[step], cwd=ROOT, dry_run=args.dry_run)
        results["steps"][step] = result
        if not args.dry_run and result["returncode"] != 0:
            results["stopped_after"] = step
            write_json(pipeline_summary, results)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            raise SystemExit(int(result["returncode"]))

    qa_metrics_name = "semantic_qa_metrics.json" if args.qa_evaluator == "semantic" else "qa_metrics.json"
    qa_metrics = maybe_load_json(ruleqa_dir / qa_metrics_name)
    if qa_metrics:
        results["qa_metrics"] = qa_metrics.get("metrics", qa_metrics)
    results["complete"] = not args.dry_run and all(
        results["steps"].get(step, {}).get("returncode") == 0 for step in ("preflight", "train", "generate", "qa") if step in results["steps"]
    )
    write_json(pipeline_summary, results)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
