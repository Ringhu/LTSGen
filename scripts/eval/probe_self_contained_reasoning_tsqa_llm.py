#!/usr/bin/env python3
"""Probe self-contained reasoning TS-QA with data-only LLM prompts.

The prompt intentionally excludes evidence captions and support slots. The
model receives only scene, decision rule, variables, question, options, and
physical-unit time-series values.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_20260521/"
    / "self_contained_reasoning_tsqa.jsonl"
)
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_20260521"
DEFAULT_GPTAPI_DIR = Path("/home/cris/Research/gptapi")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


def normalize_label(text: Any) -> str:
    normalized = str(text or "").strip().lower()
    normalized = re.sub(r"^[a-d]\s*[\).:]\s*", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" .;")


def option_labels(row: dict[str, Any]) -> dict[str, str]:
    labels = row.get("option_label_by_letter")
    if isinstance(labels, dict) and labels:
        return {str(k).strip().upper()[:1]: str(v).strip() for k, v in labels.items()}
    parsed: dict[str, str] = {}
    for option in row.get("options", []):
        match = re.match(r"^\s*([A-D])\s*[\).]\s*(.+?)\s*$", str(option))
        if match:
            parsed[match.group(1)] = match.group(2)
    return parsed


def chat_via_gptapi(prompt: str, *, model: str, gptapi_dir: Path) -> str | None:
    if not gptapi_dir.exists():
        return None
    sys.path.insert(0, str(gptapi_dir))
    try:
        from llm_client import chat as gptapi_chat  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    return gptapi_chat(
        prompt,
        model=model,
        temperature=0.0,
        response_format={"type": "json_object"},
    )


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def chat_via_urllib(prompt: str, *, model: str, timeout: int = 240) -> str:
    base_url = get_env("OPENAI_BASE_URL").rstrip("/")
    api_key = get_env("OPENAI_API_KEY")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    return body["choices"][0]["message"]["content"]


def chat(prompt: str, *, model: str, gptapi_dir: Path) -> str:
    content = chat_via_gptapi(prompt, model=model, gptapi_dir=gptapi_dir)
    if content is not None:
        return content
    return chat_via_urllib(prompt, model=model)


def choose_rows(rows: list[dict[str, Any]], *, per_domain: int | None, limit: int | None) -> list[dict[str, Any]]:
    if per_domain is not None:
        selected = []
        counts: Counter[str] = Counter()
        for row in rows:
            domain = row["merge_source_name"]
            if counts[domain] < per_domain:
                selected.append(row)
                counts[domain] += 1
        return selected
    return rows[:limit] if limit is not None else rows


def sample_indices(n: int, budget: int) -> list[int]:
    if n <= budget:
        return list(range(n))
    anchors = {0, n - 1, n // 2, n // 3, (2 * n) // 3}
    remaining = [round(i * (n - 1) / (budget - 1)) for i in range(budget)]
    return sorted(set(i for i in anchors.union(remaining) if 0 <= i < n))


def format_values(values: list[list[float]], *, max_rows: int) -> str:
    idxs = sample_indices(len(values), max_rows)
    lines = ["index," + ",".join(f"x{i}" for i in range(len(values[0])))]
    for idx in idxs:
        row = values[idx]
        lines.append(f"{idx}," + ",".join(f"{float(x):.6g}" for x in row))
    return "\n".join(lines)


def build_prompt(row: dict[str, Any], *, max_rows: int) -> str:
    payload = {
        "id": row["id"],
        "scene": row["scene_en"],
        "decision_rule": row["decision_rule_en"],
        "variables": row["variables_en"],
        "question": row["question"],
        "options": row["options"],
        "time_series_table": format_values(row["values"], max_rows=max_rows),
    }
    return (
        "You are answering a self-contained time-series multiple-choice question.\n"
        "Use only the scene, decision rule, variables, options, and the time-series table below.\n"
        "Do not use hidden support slots, evidence captions, simulator background, or outside domain knowledge.\n"
        "Compute the needed summary statistics from the table. If the sampled table is insufficient, say so in reason.\n\n"
        "Before returning, check that answer_label is the option text for answer, and that both match your own reason.\n\n"
        "Return JSON only with this schema:\n"
        "{\"answer\": \"A|B|C|D\", \"answer_label\": \"exact option text without the leading letter\", "
        "\"confidence\": 0.0, \"reason\": \"brief\", "
        "\"computed_summary\": {\"key\": \"value\"}, \"needs_full_series\": false}\n\n"
        f"Case:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def validate_prediction(row: dict[str, Any], pred: dict[str, Any], latency: float, raw_text: str) -> dict[str, Any]:
    answer = str(pred.get("answer", "")).strip().upper()[:1]
    if answer not in {"A", "B", "C", "D"}:
        answer = ""
    labels = option_labels(row)
    pred_answer_label = str(pred.get("answer_label", "")).strip()
    if not pred_answer_label and answer:
        pred_answer_label = labels.get(answer, "")
    gold_label = str(row["answer_label"])
    pred_letter_label = labels.get(answer, "")
    letter_correct = answer == row["answer"]
    semantic_correct = normalize_label(pred_answer_label) == normalize_label(gold_label)
    if normalize_label(pred_letter_label) == normalize_label(gold_label):
        semantic_correct = True
    label_letter_mismatch = bool(
        answer
        and pred_answer_label
        and pred_letter_label
        and normalize_label(pred_answer_label) != normalize_label(pred_letter_label)
    )
    try:
        confidence = float(pred.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "id": row["id"],
        "source_row_id": row.get("source_row_id"),
        "source": row["merge_source_name"],
        "task_family": row["task_family"],
        "gold_answer": row["answer"],
        "gold_answer_label": row["answer_label"],
        "pred_answer": answer,
        "pred_answer_label": pred_answer_label,
        "pred_letter_label": pred_letter_label,
        "correct": letter_correct,
        "letter_correct": letter_correct,
        "semantic_correct": semantic_correct,
        "label_letter_mismatch": label_letter_mismatch,
        "confidence": max(0.0, min(1.0, confidence)),
        "reason": str(pred.get("reason", ""))[:1000],
        "computed_summary": pred.get("computed_summary", {}),
        "needs_full_series": bool(pred.get("needs_full_series", False)),
        "latency_sec": latency,
        "raw_response": raw_text,
    }


def summarize(rows: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    by_source_total = Counter(row["merge_source_name"] for row in rows)
    by_source_letter_correct: Counter[str] = Counter()
    by_source_semantic_correct: Counter[str] = Counter()
    by_task_total = Counter(row["task_family"] for row in rows)
    by_task_letter_correct: Counter[str] = Counter()
    by_task_semantic_correct: Counter[str] = Counter()
    for pred in predictions:
        if pred["letter_correct"]:
            by_source_letter_correct[pred["source"]] += 1
            by_task_letter_correct[pred["task_family"]] += 1
        if pred["semantic_correct"]:
            by_source_semantic_correct[pred["source"]] += 1
            by_task_semantic_correct[pred["task_family"]] += 1
    letter_accuracy = round(sum(p["letter_correct"] for p in predictions) / len(predictions), 4) if predictions else 0.0
    semantic_accuracy = round(sum(p["semantic_correct"] for p in predictions) / len(predictions), 4) if predictions else 0.0
    return {
        "n": len(rows),
        "n_predictions": len(predictions),
        "accuracy": letter_accuracy,
        "letter_accuracy": letter_accuracy,
        "semantic_accuracy": semantic_accuracy,
        "by_source": {
            source: {
                "n": by_source_total[source],
                "correct": by_source_letter_correct[source],
                "letter_correct": by_source_letter_correct[source],
                "semantic_correct": by_source_semantic_correct[source],
                "accuracy": round(by_source_letter_correct[source] / by_source_total[source], 4),
                "letter_accuracy": round(by_source_letter_correct[source] / by_source_total[source], 4),
                "semantic_accuracy": round(by_source_semantic_correct[source] / by_source_total[source], 4),
            }
            for source in sorted(by_source_total)
        },
        "by_task_family": {
            task: {
                "n": by_task_total[task],
                "correct": by_task_letter_correct[task],
                "letter_correct": by_task_letter_correct[task],
                "semantic_correct": by_task_semantic_correct[task],
                "accuracy": round(by_task_letter_correct[task] / by_task_total[task], 4),
                "letter_accuracy": round(by_task_letter_correct[task] / by_task_total[task], 4),
                "semantic_accuracy": round(by_task_semantic_correct[task] / by_task_total[task], 4),
            }
            for task in sorted(by_task_total)
        },
        "mean_latency_sec": round(sum(p["latency_sec"] for p in predictions) / len(predictions), 3) if predictions else 0.0,
        "needs_full_series_count": sum(1 for p in predictions if p["needs_full_series"]),
        "wrong": [p for p in predictions if not p["letter_correct"]],
        "semantic_wrong": [p for p in predictions if not p["semantic_correct"]],
        "letter_label_mismatch": [p for p in predictions if p.get("label_letter_mismatch")],
    }


def render_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# Self-contained Reasoning TSQA Data-only GPT Probe（2026-05-21）",
        "",
        "本 probe 只给 LLM 自足背景、变量、决策规则、四选项和物理量时序表，不给 evidence caption 或 support slots。",
        "",
        "## 总览",
        "",
        f"- model: `{report['model']}`",
        f"- rows: `{summary['n_predictions']}/{summary['n']}`",
        f"- strict letter accuracy: `{summary['letter_accuracy']}`",
        f"- semantic answer accuracy: `{summary['semantic_accuracy']}`",
        f"- mean latency: `{summary['mean_latency_sec']}s`",
        f"- needs full series: `{summary['needs_full_series_count']}`",
        "",
        "## By Source",
        "",
        "| source | n | letter correct | letter acc | semantic correct | semantic acc |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for source, item in summary["by_source"].items():
        lines.append(
            f"| `{source}` | {item['n']} | {item['letter_correct']} | {item['letter_accuracy']} | "
            f"{item['semantic_correct']} | {item['semantic_accuracy']} |"
        )
    lines.extend(
        [
            "",
            "## Semantic Wrong / Risk Cases",
            "",
            "| source | task | gold | pred | reason |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if not summary["semantic_wrong"]:
        lines.append("| - | - | - | - | 全部正确 |")
    else:
        for pred in summary["semantic_wrong"]:
            reason = str(pred["reason"]).replace("|", "／")
            lines.append(
                f"| `{pred['source']}` | `{pred['task_family']}` | "
                f"{pred['gold_answer']} / {pred['gold_answer_label']} | "
                f"{pred['pred_answer']} / {pred.get('pred_answer_label', '')} | {reason} |"
            )
    lines.extend(
        [
            "",
            "## Letter / Label Mismatches",
            "",
            "| source | task | gold | returned letter | returned label | letter label |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    if not summary["letter_label_mismatch"]:
        lines.append("| - | - | - | - | - | 无 |")
    else:
        for pred in summary["letter_label_mismatch"]:
            lines.append(
                f"| `{pred['source']}` | `{pred['task_family']}` | "
                f"{pred['gold_answer']} / {pred['gold_answer_label']} | "
                f"{pred['pred_answer']} | {str(pred.get('pred_answer_label', '')).replace('|', '／')} | "
                f"{str(pred.get('pred_letter_label', '')).replace('|', '／')} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_jsonl", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--gptapi_dir", type=Path, default=DEFAULT_GPTAPI_DIR)
    parser.add_argument("--per-domain", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-table-rows", type=int, default=64)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    all_rows = load_jsonl(args.input_jsonl)
    rows = choose_rows(all_rows, per_domain=args.per_domain, limit=args.limit)
    if args.dry_run:
        print(build_prompt(rows[0], max_rows=args.max_table_rows)[:8000])
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "self_contained_reasoning_tsqa_gpt_data_only_probe.json"
    out_md = args.out_dir / "SELF_CONTAINED_REASONING_TSQA_GPT_DATA_ONLY_PROBE_20260521_ZH.md"
    existing: dict[str, dict[str, Any]] = {}
    if out_json.exists() and not args.force:
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        existing = {item["id"]: item for item in payload.get("predictions", [])}

    predictions: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        if row["id"] in existing:
            predictions.append(existing[row["id"]])
            continue
        print(f"[{idx}/{len(rows)}] probing {row['merge_source_name']} {row['task_family']}", file=sys.stderr)
        prompt = build_prompt(row, max_rows=args.max_table_rows)
        last_error: Exception | None = None
        for attempt in range(3):
            start = time.time()
            try:
                raw_text = chat(prompt, model=args.model, gptapi_dir=args.gptapi_dir)
                pred = validate_prediction(row, extract_json(raw_text), time.time() - start, raw_text)
                predictions.append(pred)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < 2:
                    time.sleep(2 + attempt * 4)
        else:
            raise RuntimeError(f"failed to probe {row['id']}: {last_error}") from last_error

        report = {
            "input": rel(args.input_jsonl),
            "model": args.model,
            "max_table_rows": args.max_table_rows,
            "summary": summarize(rows, predictions),
            "predictions": predictions,
        }
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        render_markdown(out_md, report)

    report = {
        "input": rel(args.input_jsonl),
        "model": args.model,
        "max_table_rows": args.max_table_rows,
        "summary": summarize(rows, predictions),
        "predictions": predictions,
    }
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_markdown(out_md, report)
    print(json.dumps({"out_json": rel(out_json), "out_md": rel(out_md), "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
