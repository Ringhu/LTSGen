#!/usr/bin/env python3
"""Build no-question prompt-control SFT assets for natural QCC.

The control keeps the same time-series values and target captions but removes
the downstream question from the model prompt. This lets a GPU smoke run compare
question-conditioned caption training against a no-question captioner under the
same train/test split and evaluator.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_SFT_DIR = BASE / "sft"
DEFAULT_OUT_DIR = BASE / "sft_no_question"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract_prompt_field(prompt: str, field: str) -> str:
    pattern = re.compile(rf"^{re.escape(field)}:\s*(.+?)\s*$", flags=re.MULTILINE)
    match = pattern.search(prompt or "")
    return match.group(1).strip() if match else ""


def build_no_question_prompt(prompt: str) -> tuple[str, dict[str, str]]:
    scene = extract_prompt_field(prompt, "Scene")
    variables = extract_prompt_field(prompt, "Variables")
    question = extract_prompt_field(prompt, "Question")
    lines = [
        "You are a time-series evidence captioner. Given the time series, scene, "
        "and variables, write one or two concise natural-language sentences "
        "describing the most salient evidence in the window. Do not choose an "
        "option letter and do not output JSON.",
        "",
    ]
    if scene:
        lines.append(f"Scene: {scene}")
    if variables:
        lines.append(f"Variables: {variables}")
    if not scene and not variables:
        stripped = re.sub(r"^Question:\s*.+$", "", prompt or "", flags=re.MULTILINE).strip()
        if stripped:
            lines.append(stripped)
    no_question_prompt = "\n".join(lines).strip()
    return no_question_prompt, {"removed_question": question, "scene": scene, "variables": variables}


def transform_row(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    out = dict(row)
    prompt, info = build_no_question_prompt(str(row.get("prompt", "")))
    out["prompt"] = prompt
    meta = dict(out.get("meta") or {})
    meta.update(
        {
            "prompt_control": "no_question",
            "question_conditioned": False,
            "removed_question_en": info["removed_question"],
        }
    )
    out["meta"] = meta
    return out, info


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(
        row.get("merge_source_name")
        or meta.get("merge_source_name")
        or row.get("multisim_source_domain")
        or row.get("domain")
        or "unknown"
    )


def validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    question_markers = [row.get("id", "") for row in rows if "Question:" in str(row.get("prompt", ""))]
    missing_prompt = [row.get("id", "") for row in rows if not str(row.get("prompt", "")).strip()]
    return {
        "n": len(rows),
        "question_marker_count": len(question_markers),
        "question_marker_examples": question_markers[:5],
        "missing_prompt_count": len(missing_prompt),
        "missing_prompt_examples": missing_prompt[:5],
        "by_source": dict(Counter(source_name(row) for row in rows)),
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Natural QCC No-Question Control Assets（2026-05-20）",
        "",
        "本目录保留相同 values、gold target caption 和 train/dev/test split，只把模型输入 prompt 中的 downstream question 移除。",
        "用途是训练 no-question captioner，对照 question-conditioned QCC captioner 是否真正利用问题条件。",
        "",
        "## Inputs",
        "",
        f"- source SFT dir: `{report['inputs']['sft_dir']}`",
        f"- source run name: `{report['inputs']['run_name']}`",
        "",
        "## Outputs",
        "",
        f"- output dir: `{report['outputs']['out_dir']}`",
        f"- output run name: `{report['outputs']['out_run_name']}`",
        "",
        "## Split Summary",
        "",
        "| split | raw rows | sft rows | raw question markers | sft question markers |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for split, item in sorted(report["splits"].items()):
        raw = item["raw_summary"]
        sft = item["sft_summary"]
        lines.append(
            f"| `{split}` | {raw['n']} | {sft['n']} | "
            f"{raw['question_marker_count']} | {sft['question_marker_count']} |"
        )
    lines.extend(
        [
            "",
            "## GPU Usage",
            "",
            "Run the no-question control with:",
            "",
            "```bash",
            "MODE=no_question PROFILE=a100 scripts/remote/run_natural_qcc_crossdomain_smoke_a100.sh",
            "```",
            "",
            "Then compare against the question-conditioned run with:",
            "",
            "```bash",
            "python3 scripts/eval/audit_natural_qcc_gpu_qcond_vs_noquestion.py",
            "```",
            "",
            "若 no-question 与 q-conditioned 结果相同或更强，应报告为 Q-conditioning gap 不成立，而不是 QCC 成功。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sft_dir", type=Path, default=DEFAULT_SFT_DIR)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run_name", default="natural_qcc_crossdomain")
    parser.add_argument("--out_run_name", default="natural_qcc_crossdomain_no_question")
    parser.add_argument("--splits", nargs="+", default=["train", "dev", "test"])
    args = parser.parse_args()

    report: dict[str, Any] = {
        "inputs": {"sft_dir": rel(args.sft_dir), "run_name": args.run_name},
        "outputs": {"out_dir": rel(args.out_dir), "out_run_name": args.out_run_name},
        "splits": {},
    }
    for split in args.splits:
        raw_in = args.sft_dir / f"{args.run_name}_{split}_raw.jsonl"
        sft_in = args.sft_dir / f"{args.run_name}_{split}_sft.jsonl"
        raw_out = args.out_dir / f"{args.out_run_name}_{split}_raw.jsonl"
        sft_out = args.out_dir / f"{args.out_run_name}_{split}_sft.jsonl"
        raw_rows = [transform_row(row)[0] for row in load_jsonl(raw_in)]
        sft_rows = [transform_row(row)[0] for row in load_jsonl(sft_in)]
        write_jsonl(raw_out, raw_rows)
        write_jsonl(sft_out, sft_rows)
        report["splits"][split] = {
            "raw_in": rel(raw_in),
            "sft_in": rel(sft_in),
            "raw_out": rel(raw_out),
            "sft_out": rel(sft_out),
            "raw_summary": validate_rows(raw_rows),
            "sft_summary": validate_rows(sft_rows),
        }

    report["gate_pass"] = all(
        item["raw_summary"]["n"] > 0
        and item["sft_summary"]["n"] > 0
        and item["raw_summary"]["question_marker_count"] == 0
        and item["sft_summary"]["question_marker_count"] == 0
        and item["raw_summary"]["missing_prompt_count"] == 0
        and item["sft_summary"]["missing_prompt_count"] == 0
        for item in report["splits"].values()
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.out_dir / "natural_qcc_crossdomain_no_question_summary.json"
    report_path = args.out_dir / "NATURAL_QCC_NO_QUESTION_CONTROL_20260520_ZH.md"
    summary_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["gate_pass"] else 1)


if __name__ == "__main__":
    main()
