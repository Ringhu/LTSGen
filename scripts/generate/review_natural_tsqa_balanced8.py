#!/usr/bin/env python3
"""Review the 48-row natural balanced8 QA set with an OpenAI-compatible GPT reviewer."""
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
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]
CASE_ROOT = ROOT / ".research/general-qcc-captioner-20260515/natural_qa_balanced8_20260519"
INPUT_JSONL = CASE_ROOT / "natural_multisim_v5_balanced8.jsonl"
OUT_JSON = CASE_ROOT / "natural_multisim_v5_balanced8_review.json"
OUT_MD = CASE_ROOT / "NATURAL_QA_BALANCED8_REVIEW_20260519_ZH.md"


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_cases() -> list[dict]:
    with INPUT_JSONL.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_existing_reviews() -> dict[str, dict]:
    if not OUT_JSON.exists():
        return {}
    data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    return {review["id"]: review for review in data.get("reviews", [])}


def extract_json(text: str) -> dict:
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


def chat(prompt: str, *, model: str = "gpt-5.5", timeout: int = 240) -> str:
    base_url = get_env("OPENAI_BASE_URL").rstrip("/")
    api_key = get_env("OPENAI_API_KEY")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    return body["choices"][0]["message"]["content"]


def build_prompt(case: dict) -> str:
    review_payload = {
        "id": case["id"],
        "source": case["source"],
        "task_family": case["task_family"],
        "scene_en": case["scene_en"],
        "scene_zh": case["scene_zh"],
        "variables_en": case["variables_en"],
        "variables_zh": case["variables_zh"],
        "question_en": case["question_en"],
        "question_zh": case["question_zh"],
        "options": case["options"],
        "gold_answer": case["gold_answer"],
        "gold_answer_label": case["gold_answer_label"],
        "gold_answer_zh": case["gold_answer_zh"],
        "evidence_en": case["evidence_en"],
        "evidence_zh": case["evidence_zh"],
        "support_slots": case["support_slots"],
        "original_question": case["original_question"],
        "lint_issues": case["lint_issues"],
    }
    return dedent(
        f"""
        You are reviewing natural-language time-series QA examples for a General QCC research dataset.

        Review goals:
        - Judge whether the QA reads like a normal domain question, not a verifier-slot prompt.
        - Judge whether the question is answerable from the scene, variable definitions, options, evidence, and deterministic support slots.
        - Do not decide or recalculate the gold answer. The gold answer comes from deterministic support slots.
        - Penalize hidden metadata, internal IDs, unexplained global/local time axes, unclear variable meanings, and degree labels that need unstated thresholds.
        - Treat lead-lag examples conservatively. If the evidence does not make the timing relationship clearly usable, mark medium/high risk or revise.
        - Prefer concise scene + natural decision question + human-readable options.

        Return JSON only with this schema:
        {{
          "id": string,
          "decision": "keep" | "revise" | "reject",
          "naturalness_score": integer 1-5,
          "answerability_score": integer 1-5,
          "accuracy_risk": "low" | "medium" | "high",
          "problem_tags": [string],
          "reason_zh": string,
          "suggested_scene_zh": string,
          "suggested_question_zh": string,
          "suggested_options_zh": [string, string, string, string],
          "large_scale_rule_zh": string
        }}

        Case:
        {json.dumps(review_payload, ensure_ascii=False, indent=2)}
        """
    ).strip()


def excluded_review(case: dict) -> dict:
    return {
        "id": case["id"],
        "source": case["source"],
        "task_family": case["task_family"],
        "review_scope": "excluded_by_rule",
        "decision": "reject",
        "naturalness_score": 2,
        "answerability_score": 2,
        "accuracy_risk": "high",
        "problem_tags": ["metadata_only_not_pure_ts"],
        "reason_zh": "该行依赖 AIOps 官方 metadata，而不是仅由时间序列窗口和可解释场景回答；不应进入纯 TS-QA 正例池。",
        "suggested_scene_zh": case["scene_zh"],
        "suggested_question_zh": "如需保留，应显式提供 metadata 表或改成遥测本身可支持的问题。",
        "suggested_options_zh": [opt["zh"] for opt in case["options"]],
        "large_scale_rule_zh": "metadata/provenance/app/service-role/fault-context 题必须单独建模，不能伪装成纯时间序列推理题。",
    }


def validate_review(case: dict, review: dict) -> dict:
    review.setdefault("id", case["id"])
    review["id"] = case["id"]
    review["source"] = case["source"]
    review["task_family"] = case["task_family"]
    review["review_scope"] = "gpt55_candidate"
    if review.get("decision") not in {"keep", "revise", "reject"}:
        review["decision"] = "revise"
        review["problem_tags"] = list(set(review.get("problem_tags", []) + ["invalid_decision_repaired"]))
    for key in ["naturalness_score", "answerability_score"]:
        try:
            score = int(review.get(key, 3))
        except (TypeError, ValueError):
            score = 3
        review[key] = max(1, min(5, score))
    if review.get("accuracy_risk") not in {"low", "medium", "high"}:
        review["accuracy_risk"] = "medium"
    if not isinstance(review.get("problem_tags"), list):
        review["problem_tags"] = []
    for key in ["reason_zh", "suggested_scene_zh", "suggested_question_zh", "large_scale_rule_zh"]:
        review[key] = str(review.get(key, "")).strip()
    if not isinstance(review.get("suggested_options_zh"), list) or len(review["suggested_options_zh"]) != 4:
        review["suggested_options_zh"] = [opt["zh"] for opt in case["options"]]
    return review


def is_positive(review: dict) -> bool:
    return (
        review["review_scope"] == "gpt55_candidate"
        and review["decision"] == "keep"
        and review["naturalness_score"] >= 4
        and review["answerability_score"] >= 4
        and review["accuracy_risk"] == "low"
    )


def build_markdown(cases: list[dict], reviews: list[dict]) -> str:
    by_id = {case["id"]: case for case in cases}
    by_scope = Counter(review["review_scope"] for review in reviews)
    by_decision = Counter(review["decision"] for review in reviews)
    by_source = Counter(review["source"] for review in reviews)
    by_risk = Counter(review["accuracy_risk"] for review in reviews)
    candidate_reviews = [r for r in reviews if r["review_scope"] == "gpt55_candidate"]
    positive = [r for r in candidate_reviews if is_positive(r)]
    issue_counter = Counter()
    tag_counter = Counter()
    source_positive = defaultdict(int)
    source_candidate = defaultdict(int)
    for review in candidate_reviews:
        source_candidate[review["source"]] += 1
        if is_positive(review):
            source_positive[review["source"]] += 1
        tag_counter.update(review.get("problem_tags") or [])
        case = by_id[review["id"]]
        issue_counter.update(issue["code"] for issue in case.get("lint_issues", []))

    lines = [
        "# Natural QA Balanced8 GPT-5.5 Review（2026-05-19）",
        "",
        "本报告审查 `natural_multisim_v5_balanced8.jsonl` 的自然语言 QA 草案。Reviewer 只评估自然性、可答性和准确性风险；gold answer 仍来自 deterministic support slots。",
        "",
        "## 总览",
        "",
        f"- rows: `{len(cases)}`",
        f"- review scope: `{dict(by_scope)}`",
        f"- decision: `{dict(by_decision)}`",
        f"- source: `{dict(by_source)}`",
        f"- risk: `{dict(by_risk)}`",
        f"- positive pool by reviewer gate: `{len(positive)}/{len(candidate_reviews)}`",
        f"- candidate lint issues: `{dict(issue_counter)}`",
        f"- reviewer problem tags: `{dict(tag_counter)}`",
        "",
        "## 正例准入规则",
        "",
        "正例池只接受：`review_scope == gpt55_candidate`、`decision == keep`、`naturalness_score >= 4`、`answerability_score >= 4`、`accuracy_risk == low`。",
        "",
        "| source | positive | candidate |",
        "| --- | ---: | ---: |",
    ]
    for source in sorted(source_candidate):
        lines.append(f"| `{source}` | {source_positive[source]} | {source_candidate[source]} |")

    lines.extend(
        [
            "",
            "## 需要处理的样本",
            "",
            "| source | task | decision | naturalness | answerability | risk | reason |",
            "| --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    attention = [
        r
        for r in candidate_reviews
        if r["decision"] != "keep" or r["naturalness_score"] < 4 or r["answerability_score"] < 4 or r["accuracy_risk"] != "low"
    ]
    if not attention:
        lines.append("| - | - | - | - | - | - | 全部 candidate 通过 reviewer gate |")
    else:
        for review in attention:
            lines.append(
                "| `{source}` | `{task_family}` | `{decision}` | {naturalness_score} | {answerability_score} | {accuracy_risk} | {reason_zh} |".format(
                    **review
                )
            )

    lines.extend(
        [
            "",
            "## 逐条审查",
            "",
            "| source | task | scope | decision | naturalness | answerability | risk | question_zh | reason |",
            "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for review in reviews:
        case = by_id[review["id"]]
        lines.append(
            "| `{source}` | `{task}` | `{scope}` | `{decision}` | {naturalness} | {answerability} | `{risk}` | {question} | {reason} |".format(
                source=review["source"],
                task=review["task_family"],
                scope=review["review_scope"],
                decision=review["decision"],
                naturalness=review["naturalness_score"],
                answerability=review["answerability_score"],
                risk=review["accuracy_risk"],
                question=case["question_zh"].replace("|", "／"),
                reason=review["reason_zh"].replace("|", "／"),
            )
        )

    lines.extend(
        [
            "",
            "## 结论",
            "",
            "- 这批样本已经从 slot prompt 改成面向领域用户的自然问题，但 reviewer gate 仍用于筛掉不自然、隐藏上下文或弱证据样本。",
            "- 5 条 AIOps metadata-only 行被规则排除，不进入纯时间序列 QA 正例池。",
            "- lead-lag 行保留人工复核标记；如果 reviewer 给出中高风险，应优先替换成分离更强或证据更清楚的样本。",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(cases: list[dict], reviews_by_id: dict[str, dict]) -> None:
    ordered = [reviews_by_id[case["id"]] for case in cases if case["id"] in reviews_by_id]
    payload = {
        "input": str(INPUT_JSONL.relative_to(ROOT)),
        "model": "gpt-5.5",
        "n_cases": len(cases),
        "n_reviews": len(ordered),
        "reviews": ordered,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(cases, ordered), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="rerun reviews even if an existing output is present")
    parser.add_argument("--max-calls", type=int, default=None, help="limit GPT calls for smoke/resume")
    parser.add_argument("--only-task", action="append", default=[], help="rerun only rows whose task_family matches this value")
    args = parser.parse_args()

    cases = load_cases()
    reviews_by_id = {} if args.force else load_existing_reviews()
    if args.only_task:
        selected_tasks = set(args.only_task)
        reviews_by_id = {
            case_id: review for case_id, review in reviews_by_id.items() if review.get("task_family") not in selected_tasks
        }
    else:
        selected_tasks = set()
    calls = 0
    for idx, case in enumerate(cases, start=1):
        if selected_tasks and case["task_family"] not in selected_tasks:
            if case["id"] not in reviews_by_id:
                raise RuntimeError(f"missing existing review for skipped row {case['id']}")
            continue
        if case["id"] in reviews_by_id:
            continue
        if case["natural_status"] != "candidate":
            reviews_by_id[case["id"]] = excluded_review(case)
            write_outputs(cases, reviews_by_id)
            continue
        if args.max_calls is not None and calls >= args.max_calls:
            break
        print(f"[{idx}/{len(cases)}] reviewing {case['source']} {case['task_family']}", file=sys.stderr)
        last_error = None
        for attempt in range(3):
            try:
                content = chat(build_prompt(case))
                review = validate_review(case, extract_json(content))
                reviews_by_id[case["id"]] = review
                calls += 1
                write_outputs(cases, reviews_by_id)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < 2:
                    time.sleep(2 + attempt * 5)
        else:
            raise RuntimeError(f"failed to review {case['id']}: {last_error}") from last_error

    write_outputs(cases, reviews_by_id)
    print(OUT_JSON)
    print(OUT_MD)


if __name__ == "__main__":
    main()
