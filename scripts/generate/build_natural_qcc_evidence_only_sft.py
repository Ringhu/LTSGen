#!/usr/bin/env python3
"""Build evidence-only Natural-QCC SFT variants.

The original Natural-QCC smoke target appended ``Answer label: ...`` to every
caption so the strict QA bridge could recover an answer. That is useful for a
closeout evaluator, but it also gives the captioner a cheap label-emission
shortcut. This builder preserves the reviewer-positive rows and gold labels,
while training the captioner only on natural evidence text.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_crossdomain_dataset_20260520"
DEFAULT_POSITIVE = BASE / "natural_qcc_crossdomain_positive.jsonl"
DEFAULT_OUT_DIR = BASE / "sft_evidence_only"

ANSWER_LABEL_RE = re.compile(r"\s*Answer label:\s*[^.;\n]+[.;]?\s*$", flags=re.IGNORECASE)
OPTION_LETTER_RE = re.compile(r"\b(?:answer|option|choice)\s*[:=]?\s*[ABCD]\b|\b[ABCD][.)]\s", flags=re.IGNORECASE)


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


def source_name(row: dict[str, Any]) -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return str(
        row.get("merge_source_name")
        or meta.get("merge_source_name")
        or row.get("multisim_source_domain")
        or row.get("domain")
        or "unknown"
    )


def value_dim(row: dict[str, Any]) -> int:
    values = row.get("values") or []
    if not values:
        return 0
    first = values[0]
    return len(first) if isinstance(first, list) else 1


def evidence_text(row: dict[str, Any]) -> str:
    text = str(row.get("natural_evidence_caption") or row.get("natural_evidence_en") or row.get("target_caption") or "")
    text = ANSWER_LABEL_RE.sub("", text).strip()
    return re.sub(r"\s+", " ", text)


def options_text(row: dict[str, Any]) -> str:
    options = row.get("options") or []
    return "; ".join(str(item).strip() for item in options if str(item).strip())


def build_prompt(row: dict[str, Any], *, include_options: bool = False) -> str:
    scene = str(row.get("scene_en", "")).strip()
    variables = row.get("variables_en") or []
    if isinstance(variables, list):
        variables_text = "; ".join(str(item) for item in variables)
    else:
        variables_text = str(variables)
    question = str(row.get("question", "")).strip()
    prompt = (
        "You are a question-conditioned time-series evidence captioner. "
        "Given the time series, scene, variables, and question, write one or two "
        "concise natural-language evidence sentences. Include the numeric facts "
        "and rule thresholds needed for the decision. Do not output an answer "
        "letter or JSON.\n\n"
        f"Scene: {scene}\n"
        f"Variables: {variables_text}\n"
        f"Question: {question}"
    )
    opts = options_text(row)
    if include_options and opts:
        prompt += f"\nOptions: {opts}"
    return prompt


def build_no_question_prompt(row: dict[str, Any]) -> str:
    scene = str(row.get("scene_en", "")).strip()
    variables = row.get("variables_en") or []
    if isinstance(variables, list):
        variables_text = "; ".join(str(item) for item in variables)
    else:
        variables_text = str(variables)
    return (
        "You are a time-series evidence captioner. Given the time series, scene, "
        "and variables, write one or two concise natural-language evidence "
        "sentences. Include numeric facts from the window. Do not output an "
        "answer letter or JSON.\n\n"
        f"Scene: {scene}\n"
        f"Variables: {variables_text}"
    )


def transform_row(row: dict[str, Any], *, prompt_control: str, include_options_in_prompt: bool = False) -> dict[str, Any]:
    evidence = evidence_text(row)
    out = dict(row)
    out["prompt"] = (
        build_no_question_prompt(row)
        if prompt_control == "no_question"
        else build_prompt(row, include_options=include_options_in_prompt)
    )
    out["output"] = evidence
    out["target_caption"] = evidence
    out["evidence_only_target_caption"] = evidence
    meta = dict(out.get("meta") or {})
    meta.update(
        {
            "natural_qcc_evidence_only_sft": True,
            "prompt_control": prompt_control,
            "question_conditioned": prompt_control == "qcond",
            "include_options_in_prompt": include_options_in_prompt if prompt_control == "qcond" else False,
            "merge_source_name": source_name(row),
            "task_family": row.get("task_family", ""),
            "answer": row.get("answer", ""),
            "answer_label": row.get("answer_label", ""),
            "natural_evidence_zh": row.get("natural_evidence_zh", ""),
        }
    )
    out["meta"] = meta
    return out


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row["target_caption"],
        "meta": row.get("meta", {}),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_split: dict[str, Counter[str]] = defaultdict(Counter)
    answer_counts = Counter(str(row.get("answer", "")) for row in rows)
    output_lengths = [len(str(row.get("output", ""))) for row in rows]
    for row in rows:
        source_split[source_name(row)][str(row.get("split", ""))] += 1
    return {
        "n": len(rows),
        "by_source": dict(Counter(source_name(row) for row in rows)),
        "by_split": dict(Counter(str(row.get("split", "")) for row in rows)),
        "by_source_split": {source: dict(counts) for source, counts in sorted(source_split.items())},
        "by_task_family": dict(Counter(str(row.get("task_family", "")) for row in rows)),
        "by_value_dim": dict(Counter(str(value_dim(row)) for row in rows)),
        "answer_distribution": dict(answer_counts),
        "max_answer_share": round(max(answer_counts.values()) / len(rows), 4) if rows else 1.0,
        "mean_output_chars": round(sum(output_lengths) / len(output_lengths), 1) if output_lengths else 0.0,
        "answer_label_suffix_count": sum(1 for row in rows if "answer label:" in str(row.get("output", "")).lower()),
        "option_letter_leak_count": sum(1 for row in rows if OPTION_LETTER_RE.search(str(row.get("output", "")))),
        "missing_required_count": sum(
            1
            for row in rows
            if not all(key in row and row[key] not in ("", [], None) for key in ("id", "values", "prompt", "output", "target_caption"))
        ),
    }


def split_rows(rows: list[dict[str, Any]], *, train_splits: set[str], eval_split: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    train_rows = [row for row in rows if str(row.get("split", "")) in train_splits]
    eval_rows = [row for row in rows if str(row.get("split", "")) == eval_split]
    original = {
        split: [row for row in rows if str(row.get("split", "")) == split]
        for split in sorted({str(row.get("split", "")) for row in rows if row.get("split")})
    }
    return train_rows, eval_rows, original


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Natural QCC Evidence-Only SFT Assets（2026-05-20）",
        "",
        "本目录不改变 reviewer-positive 数据，只把 SFT 训练目标从带 `Answer label` 的 oracle caption 改为 evidence-only caption，减少模型只学答案标签的捷径。",
        "",
        f"- input positive JSONL: `{report['input_positive_jsonl']}`",
        f"- output dir: `{report['out_dir']}`",
        f"- include options in qcond prompt: `{report['include_options_in_prompt']}`",
        f"- train splits: `{report['train_splits']}`",
        f"- eval split: `{report['eval_split']}`",
        f"- schema gate pass: `{report['schema_gate_pass']}`",
        "",
        "## Files",
        "",
        "| prompt control | train rows | eval rows | train sft | eval sft |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for control, item in sorted(report["variants"].items()):
        lines.append(
            f"| `{control}` | {item['train']['n']} | {item['eval']['n']} | "
            f"`{item['files']['train_sft']}` | `{item['files']['eval_sft']}` |"
        )
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "该变体只能用 deterministic semantic bridge 评估 evidence 是否支持答案；strict label bridge 预期会低估 evidence-only caption。",
            "如果生成 caption 仍出现答案标签、选项字母或过短碎片，应报告为训练/解码失败。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--positive_jsonl", type=Path, default=DEFAULT_POSITIVE)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run_name", default="natural_qcc_crossdomain_evidence_only")
    parser.add_argument("--train_splits", nargs="+", default=["train", "dev"])
    parser.add_argument("--eval_split", default="test")
    parser.add_argument(
        "--include_options_in_prompt",
        action="store_true",
        help="Append the multiple-choice options to the q-conditioned prompt while keeping targets evidence-only.",
    )
    args = parser.parse_args()

    positive_rows = load_jsonl(args.positive_jsonl)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "input_positive_jsonl": rel(args.positive_jsonl),
        "out_dir": rel(args.out_dir),
        "run_name": args.run_name,
        "include_options_in_prompt": args.include_options_in_prompt,
        "train_splits": args.train_splits,
        "eval_split": args.eval_split,
        "original_positive": summarize(positive_rows),
        "variants": {},
    }

    for control in ("qcond", "no_question"):
        variant_rows = [
            transform_row(row, prompt_control=control, include_options_in_prompt=args.include_options_in_prompt)
            for row in positive_rows
        ]
        train_rows, eval_rows, split_map = split_rows(variant_rows, train_splits=set(args.train_splits), eval_split=args.eval_split)
        prefix = args.run_name if control == "qcond" else f"{args.run_name}_no_question"
        train_raw = args.out_dir / f"{prefix}_train_raw.jsonl"
        train_sft = args.out_dir / f"{prefix}_train_sft.jsonl"
        eval_raw = args.out_dir / f"{prefix}_{args.eval_split}_raw.jsonl"
        eval_sft = args.out_dir / f"{prefix}_{args.eval_split}_sft.jsonl"
        write_jsonl(train_raw, train_rows)
        write_jsonl(train_sft, [sft_row(row) for row in train_rows])
        write_jsonl(eval_raw, eval_rows)
        write_jsonl(eval_sft, [sft_row(row) for row in eval_rows])
        for split, rows in split_map.items():
            split_prefix = f"{prefix}_original_{split}"
            write_jsonl(args.out_dir / f"{split_prefix}_raw.jsonl", rows)
            write_jsonl(args.out_dir / f"{split_prefix}_sft.jsonl", [sft_row(row) for row in rows])
        report["variants"][control] = {
            "files": {
                "train_raw": rel(train_raw),
                "train_sft": rel(train_sft),
                "eval_raw": rel(eval_raw),
                "eval_sft": rel(eval_sft),
            },
            "train": summarize(train_rows),
            "eval": summarize(eval_rows),
            "all": summarize(variant_rows),
        }

    report["schema_gate_pass"] = all(
        item["train"]["n"] > 0
        and item["eval"]["n"] > 0
        and item["all"]["missing_required_count"] == 0
        and item["all"]["answer_label_suffix_count"] == 0
        and item["all"]["option_letter_leak_count"] == 0
        for item in report["variants"].values()
    )
    summary_path = args.out_dir / "natural_qcc_crossdomain_evidence_only_summary.json"
    report_path = args.out_dir / "NATURAL_QCC_EVIDENCE_ONLY_SFT_20260520_ZH.md"
    summary_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["schema_gate_pass"] else 1)


if __name__ == "__main__":
    main()
