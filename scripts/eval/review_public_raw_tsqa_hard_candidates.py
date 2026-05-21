#!/usr/bin/env python3
"""Review Public Raw TSQA hard-case candidates with an LLM quality critic.

Reviewer output is a quality gate only. It must not change gold answers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from textwrap import dedent
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521"
DEFAULT_AUDIT_JSONL = DEFAULT_DATA_DIR / "hard_case_audit_20260521.jsonl"
DEFAULT_OUT_JSONL = DEFAULT_DATA_DIR / "hard_candidate_reviewer_20260521.jsonl"
DEFAULT_OUT_MD = DEFAULT_DATA_DIR / "PUBLIC_RAW_TSQA_V4_HARD_CANDIDATE_REVIEW_20260521_ZH.md"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_key_env(root: Path) -> None:
    path = root / "key.env"
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and value:
            os.environ.setdefault(key, value)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract_json(text: str) -> dict[str, Any]:
    stripped = (text or "").strip()
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
    return {}


def response_text(body: dict[str, Any]) -> str:
    try:
        msg = body["choices"][0]["message"]
    except Exception:
        return ""
    for key in ("content", "reasoning_content", "reasoning"):
        value = msg.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def build_prompt(row: dict[str, Any]) -> str:
    payload = {
        "id": row["id"],
        "language": row["language"],
        "domain": row["domain"],
        "task_family": row["task_family"],
        "gold_answer": row["gold_answer"],
        "answer_label": row.get("answer_label", ""),
        "answer_label_zh": row.get("answer_label_zh", ""),
        "natural_task_en": row.get("natural_task_en", ""),
        "natural_task_zh": row.get("natural_task_zh", ""),
        "deterministic_rule_id": row.get("deterministic_rule_id", ""),
        "support_summary": row.get("support_summary", ""),
        "oracle_evidence_en": row.get("oracle_evidence_en", ""),
        "oracle_evidence_zh": row.get("oracle_evidence_zh", ""),
        "top_model": row.get("top_model", ""),
        "top_model_pred_answer": row.get("top_model_pred_answer", ""),
        "top_model_reason": row.get("top_model_reason", ""),
        "wrong_runs": row.get("wrong_runs", []),
        "manual_pre_review_note_zh": row.get("manual_review_note_zh", ""),
    }
    return dedent(
        f"""
        You are a reviewer for a bilingual time-series QA benchmark.

        Goal:
        Decide whether this model failure is a fair hard benchmark case.
        Do not change or recalculate the gold answer. The answer comes from deterministic support slots.

        A case is fair hard only if:
        - the public natural task is self-contained;
        - all thresholds/window boundaries needed by a careful model are clear;
        - the public time-series variables mentioned by the task are enough;
        - the wrong answer is plausibly due to real time-series reasoning difficulty, not wording, hidden metadata, unclear segment boundaries, ambiguous thresholds, or option-label traps.

        Return JSON only:
        {{
          "id": string,
          "language": "en" | "zh",
          "decision": "keep" | "revise" | "reject",
          "fair_hard_score": integer 1-5,
          "naturalness_score": integer 1-5,
          "answerability_score": integer 1-5,
          "threshold_clarity_score": integer 1-5,
          "window_boundary_clarity_score": integer 1-5,
          "accuracy_risk": "low" | "medium" | "high",
          "problem_tags": [string],
          "reason_zh": string,
          "revision_priority_zh": string,
          "hard_subset_eligible": true | false
        }}

        Case:
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
    ).strip()


def chat(prompt: str, args: argparse.Namespace) -> tuple[str, float]:
    url = f"{args.base_url.rstrip('/')}/chat/completions"
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": args.max_tokens,
    }
    if not args.no_response_format:
        payload["response_format"] = {"type": "json_object"}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {args.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.time()
    with urllib.request.urlopen(request, timeout=args.timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return response_text(body), time.time() - started


def validate_review(row: dict[str, Any], data: dict[str, Any], raw: str, latency: float) -> dict[str, Any]:
    out = {
        "id": row["id"],
        "language": row["language"],
        "domain": row["domain"],
        "task_family": row["task_family"],
        "source_decision": row["decision"],
        "top_model": row["top_model"],
        "top_model_pred_answer": row.get("top_model_pred_answer", ""),
        "gold_answer": row["gold_answer"],
        "raw_response": raw[:2000],
        "latency_sec": round(latency, 3),
    }
    out["decision"] = data.get("decision") if data.get("decision") in {"keep", "revise", "reject"} else "revise"
    for key in [
        "fair_hard_score",
        "naturalness_score",
        "answerability_score",
        "threshold_clarity_score",
        "window_boundary_clarity_score",
    ]:
        try:
            value = int(data.get(key, 3))
        except (TypeError, ValueError):
            value = 3
        out[key] = max(1, min(5, value))
    out["accuracy_risk"] = data.get("accuracy_risk") if data.get("accuracy_risk") in {"low", "medium", "high"} else "medium"
    out["problem_tags"] = data.get("problem_tags") if isinstance(data.get("problem_tags"), list) else []
    out["reason_zh"] = str(data.get("reason_zh", "")).strip()
    out["revision_priority_zh"] = str(data.get("revision_priority_zh", "")).strip()
    out["hard_subset_eligible"] = bool(
        data.get("hard_subset_eligible") is True
        and out["decision"] == "keep"
        and out["fair_hard_score"] >= 4
        and out["answerability_score"] >= 4
        and out["threshold_clarity_score"] >= 4
        and out["window_boundary_clarity_score"] >= 4
        and out["accuracy_risk"] == "low"
    )
    return out


def write_markdown(path: Path, reviews: list[dict[str, Any]], args: argparse.Namespace) -> None:
    by_decision = Counter(row["decision"] for row in reviews)
    by_eligible = Counter(str(row["hard_subset_eligible"]).lower() for row in reviews)
    tags = Counter(tag for row in reviews for tag in row.get("problem_tags", []))
    lines = [
        "# Public Raw TSQA v4 Hard Candidate Reviewer 2026-05-21",
        "",
        "本报告只复审 GPT-5.5 失败的候选 hard case。Reviewer 只判断题目质量和 hard-case 公平性，不改 gold answer。",
        "",
        "## Summary",
        "",
        f"- reviewer model: `{args.model}`",
        f"- candidates reviewed: `{len(reviews)}`",
        f"- decision: `{dict(by_decision)}`",
        f"- hard subset eligible: `{dict(by_eligible)}`",
        f"- problem tags: `{dict(tags)}`",
        "",
        "## Reviewed Candidates",
        "",
        "| ID | Lang | Decision | Eligible | Scores | Risk | Tags | Reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in reviews:
        scores = (
            f"hard={row['fair_hard_score']}, ans={row['answerability_score']}, "
            f"thr={row['threshold_clarity_score']}, win={row['window_boundary_clarity_score']}"
        )
        lines.append(
            f"| `{row['id']}` | `{row['language']}` | `{row['decision']}` | "
            f"`{str(row['hard_subset_eligible']).lower()}` | {scores} | "
            f"`{row['accuracy_risk']}` | `{','.join(row.get('problem_tags', []))}` | {row['reason_zh']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit_jsonl", type=Path, default=DEFAULT_AUDIT_JSONL)
    parser.add_argument("--out_jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    parser.add_argument("--out_md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--api_key", default="")
    parser.add_argument("--base_url", default="")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--max_tokens", type=int, default=240)
    parser.add_argument("--max_retries", type=int, default=1)
    parser.add_argument("--no_response_format", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    args = parser.parse_args()

    load_key_env(ROOT)
    args.api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    args.base_url = args.base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not args.api_key and not args.dry_run:
        raise SystemExit("Missing OPENAI_API_KEY or --api_key")

    rows = [
        row
        for row in load_jsonl(args.audit_jsonl)
        if row.get("decision") in {"candidate_hard_needs_review", "revise_before_hard"}
    ]
    existing = {f"{row['id']}::{row['language']}": row for row in load_jsonl(args.out_jsonl)} if args.resume else {}
    reviews = list(existing.values())

    for row in rows:
        key = f"{row['id']}::{row['language']}"
        if key in existing:
            continue
        prompt = build_prompt(row)
        if args.dry_run:
            print(prompt[:3000])
            continue
        last_error = ""
        raw = ""
        latency = 0.0
        for attempt in range(args.max_retries + 1):
            try:
                raw, latency = chat(prompt, args)
                break
            except urllib.error.HTTPError as exc:
                last_error = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception as exc:  # noqa: BLE001
                last_error = repr(exc)
            if attempt < args.max_retries:
                time.sleep(min(30, 2**attempt))
        data = extract_json(raw)
        review = validate_review(row, data, raw or last_error, latency)
        if last_error and not raw:
            review["error"] = last_error
        reviews.append(review)
        write_jsonl(args.out_jsonl, reviews)
        write_markdown(args.out_md, reviews, args)
        print(json.dumps({"reviewed": key, "decision": review["decision"], "eligible": review["hard_subset_eligible"]}, ensure_ascii=False))

    if not args.dry_run:
        reviews.sort(key=lambda item: (item["id"], item["language"]))
        write_jsonl(args.out_jsonl, reviews)
        write_markdown(args.out_md, reviews, args)
        print(json.dumps({"reviews": len(reviews), "out_jsonl": rel(args.out_jsonl), "out_md": rel(args.out_md)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
