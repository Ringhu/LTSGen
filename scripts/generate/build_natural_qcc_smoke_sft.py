#!/usr/bin/env python3
"""Build smoke SFT assets for the reviewed natural QCC probe dataset.

This keeps the current 43-row reviewer-positive set small on purpose. It is
not the final training dataset; it creates a concrete training/evaluation entry
point so the natural-QA construction can be plugged into the existing TS-RLM
caption training path before scaling to hundreds of rows per domain.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "natural_qcc_probe_positive.jsonl"
)
DEFAULT_OUT_DIR = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/"
    / "smoke_sft"
)


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
    return str(row.get("merge_source_name") or meta.get("merge_source_name") or row.get("multisim_source_domain") or row.get("domain") or "unknown")


def value_dim(row: dict[str, Any]) -> int:
    values = row.get("values") or []
    if not values:
        return 0
    first = values[0]
    return len(first) if isinstance(first, list) else 1


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    meta = dict(row.get("meta") or {})
    meta.update(
        {
            "natural_qcc_smoke_sft": True,
            "merge_source_name": source_name(row),
            "task_family": row.get("task_family", ""),
            "answer": row.get("answer", ""),
            "answer_label": row.get("answer_label", ""),
            "question_zh": row.get("question_zh", ""),
            "natural_evidence_zh": row.get("natural_evidence_zh", ""),
        }
    )
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row.get("target_caption", row.get("output", "")),
        "meta": meta,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_split: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        source_split[source_name(row)][str(row.get("split", ""))] += 1
    answer_counts = Counter(str(row.get("answer", "")) for row in rows)
    return {
        "n": len(rows),
        "by_split": dict(Counter(str(row.get("split", "")) for row in rows)),
        "by_source": dict(Counter(source_name(row) for row in rows)),
        "by_source_split": {source: dict(counts) for source, counts in sorted(source_split.items())},
        "by_value_dim": dict(Counter(str(value_dim(row)) for row in rows)),
        "by_task_family": dict(Counter(str(row.get("task_family", "")) for row in rows)),
        "answer_distribution": dict(answer_counts),
        "max_answer_share": round(max(answer_counts.values()) / len(rows), 4) if rows else 1.0,
        "missing_required_count": sum(
            1
            for row in rows
            if not all(key in row and row[key] not in ("", [], None) for key in ("id", "values", "prompt", "output", "target_caption"))
        ),
    }


def markdown(report: dict[str, Any]) -> str:
    train = report["train"]
    eval_ = report["eval"]
    lines = [
        "# Natural QCC Smoke SFT Assets（2026-05-19）",
        "",
        "本目录把 reviewer-positive natural QCC probe 样本转换成现有 TS-RLM/Qwen caption SFT 可直接读取的 smoke 训练资产。",
        "",
        "## Files",
        "",
        f"- train raw: `{report['files']['train_raw']}`",
        f"- train SFT: `{report['files']['train_sft']}`",
        f"- eval raw: `{report['files']['eval_raw']}`",
        f"- eval SFT: `{report['files']['eval_sft']}`",
        f"- schema report: `{report['files']['schema_report']}`",
        "",
        "## Split Summary",
        "",
        "| split role | n | by source | by value dim | max answer share |",
        "| --- | ---: | --- | --- | ---: |",
        f"| train/dev-as-train | {train['n']} | `{train['by_source']}` | `{train['by_value_dim']}` | {train['max_answer_share']:.4f} |",
        f"| eval/test-as-eval | {eval_['n']} | `{eval_['by_source']}` | `{eval_['by_value_dim']}` | {eval_['max_answer_share']:.4f} |",
        "",
        "## Smoke Training Command",
        "",
        "这不是正式训练命令，而是下一步在有 GPU 的机器上验证 natural evidence caption 训练链路的最小入口：",
        "",
        "```bash",
        "python3 tslm/scripts/train_multisim_v5_smoke.py \\",
        f"  --train_jsonl {report['files']['train_sft']} \\",
        f"  --eval_jsonl {report['files']['eval_sft']} \\",
        "  --llm_name_or_path /cluster/home/user1/fenghaoran/model/Qwen3-4B-Instruct-2507 \\",
        "  --output_dir .research/general-qcc-captioner-20260515/natural_qcc_probe_20260519/tsrlm_natural_qcc_probe_smoke_qwen3_4b_20260519 \\",
        "  --trust_remote_code \\",
        "  --bridge_type prefix \\",
        "  --ts_num_vars 4 \\",
        "  --target_num_vars 4 \\",
        "  --freeze_llm \\",
        "  --save_trainable_only \\",
        "  --bf16 \\",
        "  --num_train_epochs 1 \\",
        "  --per_device_train_batch_size 1 \\",
        "  --per_device_eval_batch_size 1 \\",
        "  --gradient_accumulation_steps 4 \\",
        "  --source_group_key merge_source_name",
        "```",
        "",
        "## Caveat",
        "",
        "当前只有 43 条 positive，其中 train 只有 19 条，且 AIOpsLab 没有 train 正例。因此该资产只能验证训练接口，不应用来报告方法收益。命令使用当前本地 TS-RLM 代码真实支持的 `prefix` bridge；若后续恢复 `qprefix/local_gated_qprefix` 实现，应另开架构对照。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--train_split", default="dev")
    parser.add_argument("--eval_split", default="test")
    args = parser.parse_args()

    rows = load_jsonl(args.input)
    train_rows = [row for row in rows if row.get("split") == args.train_split]
    eval_rows = [row for row in rows if row.get("split") == args.eval_split]
    if not train_rows:
        raise ValueError(f"No train rows for split={args.train_split!r}")
    if not eval_rows:
        raise ValueError(f"No eval rows for split={args.eval_split!r}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    train_raw = args.out_dir / "natural_qcc_probe_train_dev_raw.jsonl"
    eval_raw = args.out_dir / "natural_qcc_probe_eval_test_raw.jsonl"
    train_sft = args.out_dir / "natural_qcc_probe_train_dev_sft.jsonl"
    eval_sft = args.out_dir / "natural_qcc_probe_eval_test_sft.jsonl"
    write_jsonl(train_raw, train_rows)
    write_jsonl(eval_raw, eval_rows)
    write_jsonl(train_sft, [sft_row(row) for row in train_rows])
    write_jsonl(eval_sft, [sft_row(row) for row in eval_rows])

    report = {
        "input": str(args.input.relative_to(ROOT)),
        "train_split": args.train_split,
        "eval_split": args.eval_split,
        "files": {
            "train_raw": str(train_raw.relative_to(ROOT)),
            "train_sft": str(train_sft.relative_to(ROOT)),
            "eval_raw": str(eval_raw.relative_to(ROOT)),
            "eval_sft": str(eval_sft.relative_to(ROOT)),
            "schema_report": str((args.out_dir / "natural_qcc_probe_smoke_sft_schema.json").relative_to(ROOT)),
        },
        "train": summarize(train_rows),
        "eval": summarize(eval_rows),
    }
    report["schema_gate_pass"] = (
        report["train"]["n"] > 0
        and report["eval"]["n"] > 0
        and report["train"]["missing_required_count"] == 0
        and report["eval"]["missing_required_count"] == 0
        and set(report["train"]["by_value_dim"]).issubset({"3", "4"})
        and set(report["eval"]["by_value_dim"]).issubset({"3", "4"})
    )
    (args.out_dir / "natural_qcc_probe_smoke_sft_schema.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "NATURAL_QCC_SMOKE_SFT_ASSETS_20260519_ZH.md").write_text(
        markdown(report),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
