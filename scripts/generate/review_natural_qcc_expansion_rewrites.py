#!/usr/bin/env python3
"""Review Natural-QCC expansion rewrites with a GPT-5.5 quality gate."""
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
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASE_ROOT = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_expansion_rewrites_20260519"
DEFAULT_INPUT = DEFAULT_CASE_ROOT / "natural_qcc_expansion_rewrites.jsonl"
DEFAULT_REVIEW_JSON = DEFAULT_CASE_ROOT / "natural_qcc_expansion_rewrites_review.json"
DEFAULT_REVIEW_MD = DEFAULT_CASE_ROOT / "NATURAL_QCC_EXPANSION_REVIEW_20260519_ZH.md"
DEFAULT_GPTAPI_DIR = Path("/home/cris/Research/gptapi")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_existing_reviews(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {review["id"]: review for review in payload.get("reviews", [])}


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


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


def chat(prompt: str, *, model: str, gptapi_dir: Path) -> str:
    content = chat_via_gptapi(prompt, model=model, gptapi_dir=gptapi_dir)
    if content is not None:
        return content
    return chat_via_urllib(prompt, model=model)


def build_prompt(case: dict[str, Any]) -> str:
    review_payload = {
        "id": case["id"],
        "source": case["source"],
        "split": case.get("split"),
        "task_family": case["task_family"],
        "abstract_primitive": case.get("candidate_abstract_primitive"),
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
        "lint_issues": case.get("lint_issues", []),
    }
    return dedent(
        f"""
        You are reviewing natural-language time-series QA examples for a General QCC research dataset.

        Review goals:
        - Judge whether the QA reads like a normal domain question, not a verifier-slot prompt.
        - Judge whether the question is answerable from the scene, variable definitions, options, evidence, and deterministic support slots.
        - Do not decide or recalculate the gold answer. The gold answer comes from deterministic support slots.
        - Penalize hidden metadata, internal IDs, unexplained global/local time axes, unclear variable meanings, and degree labels that need unstated thresholds.
        - Reject examples that require metadata not present in the scene/evidence, even if the original dataset stores that metadata.
        - Treat lead-lag and counterfactual examples conservatively. If the evidence does not make the relationship clearly usable, mark medium/high risk or revise.
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


def excluded_review(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"],
        "source": case["source"],
        "task_family": case["task_family"],
        "review_scope": "excluded_by_rule",
        "decision": "reject",
        "naturalness_score": 2,
        "answerability_score": 2,
        "accuracy_risk": "high",
        "problem_tags": ["not_candidate"],
        "reason_zh": case.get("exclude_reason") or "该行已被规则标记为非主训练候选。",
        "suggested_scene_zh": case["scene_zh"],
        "suggested_question_zh": "不进入主 natural QCC 训练池。",
        "suggested_options_zh": [opt["zh"] for opt in case["options"]],
        "large_scale_rule_zh": "非 candidate 行不能进入 reviewer-positive 主训练池。",
    }


def validate_review(case: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    review.setdefault("id", case["id"])
    review["id"] = case["id"]
    review["source"] = case["source"]
    review["task_family"] = case["task_family"]
    review["split"] = case.get("split")
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


def is_positive(review: dict[str, Any]) -> bool:
    return (
        review.get("review_scope") == "gpt55_candidate"
        and review.get("decision") == "keep"
        and int(review.get("naturalness_score", 0)) >= 4
        and int(review.get("answerability_score", 0)) >= 4
        and review.get("accuracy_risk") == "low"
    )


def build_markdown(cases: list[dict[str, Any]], reviews: list[dict[str, Any]], *, model: str) -> str:
    by_id = {case["id"]: case for case in cases}
    by_scope = Counter(review["review_scope"] for review in reviews)
    by_decision = Counter(review["decision"] for review in reviews)
    by_source = Counter(review["source"] for review in reviews)
    by_risk = Counter(review["accuracy_risk"] for review in reviews)
    candidate_reviews = [r for r in reviews if r["review_scope"] == "gpt55_candidate"]
    positive = [r for r in candidate_reviews if is_positive(r)]
    source_positive: dict[str, int] = defaultdict(int)
    source_candidate: dict[str, int] = defaultdict(int)
    tag_counter = Counter()
    for review in candidate_reviews:
        source_candidate[review["source"]] += 1
        tag_counter.update(review.get("problem_tags") or [])
        if is_positive(review):
            source_positive[review["source"]] += 1

    lines = [
        "# Natural QCC Expansion GPT-5.5 Review（2026-05-19）",
        "",
        "本报告审查扩展候选池的自然语言 QA 草案。Reviewer 只评估自然性、可答性和准确性风险；gold answer 仍来自 deterministic support slots。",
        "",
        "## 总览",
        "",
        f"- input rows: `{len(cases)}`",
        f"- reviewed rows: `{len(reviews)}`",
        f"- model: `{model}`",
        f"- review scope: `{dict(by_scope)}`",
        f"- decision: `{dict(by_decision)}`",
        f"- source: `{dict(by_source)}`",
        f"- risk: `{dict(by_risk)}`",
        f"- positive pool by reviewer gate: `{len(positive)}/{len(candidate_reviews)}`",
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
        if r["decision"] != "keep"
        or r["naturalness_score"] < 4
        or r["answerability_score"] < 4
        or r["accuracy_risk"] != "low"
    ]
    if not attention:
        lines.append("| - | - | - | - | - | - | 全部 candidate 通过 reviewer gate |")
    else:
        for review in attention:
            lines.append(
                "| `{source}` | `{task_family}` | `{decision}` | {naturalness_score} | {answerability_score} | `{accuracy_risk}` | {reason_zh} |".format(
                    **review
                )
            )

    lines.extend(
        [
            "",
            "## 逐条审查",
            "",
            "| source | split | task | scope | decision | naturalness | answerability | risk | question_zh | reason |",
            "| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for review in reviews:
        case = by_id[review["id"]]
        lines.append(
            "| `{source}` | `{split}` | `{task}` | `{scope}` | `{decision}` | {naturalness} | {answerability} | `{risk}` | {question} | {reason} |".format(
                source=review["source"],
                split=case.get("split") or "",
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
            "- reviewer gate 是进入正式 natural QCC train/dev/test 之前的准入条件，不替代 deterministic support slots。",
            "- 当前本地输出只覆盖 AIOpsLab 数值时序候选；完整每域结果需要在数据机器上重跑 selector、natural rewrite 和本 reviewer。",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    cases: list[dict[str, Any]],
    reviews_by_id: dict[str, dict[str, Any]],
    *,
    input_jsonl: Path,
    review_json: Path,
    review_md: Path,
    model: str,
) -> None:
    ordered = [reviews_by_id[case["id"]] for case in cases if case["id"] in reviews_by_id]
    payload = {
        "input": rel(input_jsonl),
        "model": model,
        "n_cases": len(cases),
        "n_reviews": len(ordered),
        "reviews": ordered,
    }
    review_json.parent.mkdir(parents=True, exist_ok=True)
    review_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    review_md.write_text(build_markdown(cases, ordered, model=model), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_jsonl", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--review_json", type=Path, default=DEFAULT_REVIEW_JSON)
    parser.add_argument("--review_md", type=Path, default=DEFAULT_REVIEW_MD)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--gptapi_dir", type=Path, default=DEFAULT_GPTAPI_DIR)
    parser.add_argument("--force", action="store_true", help="rerun reviews even if an existing output is present")
    parser.add_argument("--max-calls", type=int, default=None, help="limit GPT calls for smoke/resume")
    parser.add_argument("--only-task", action="append", default=[], help="rerun only rows whose task_family matches this value")
    parser.add_argument("--dry-run", action="store_true", help="validate inputs and print the first prompt without calling GPT")
    args = parser.parse_args()

    cases = load_jsonl(args.input_jsonl)
    if args.dry_run:
        print(f"cases={len(cases)}")
        if cases:
            print(build_prompt(cases[0])[:4000])
        return

    reviews_by_id = {} if args.force else load_existing_reviews(args.review_json)
    if args.only_task:
        selected_tasks = set(args.only_task)
        reviews_by_id = {
            case_id: review
            for case_id, review in reviews_by_id.items()
            if review.get("task_family") not in selected_tasks
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
            write_outputs(
                cases,
                reviews_by_id,
                input_jsonl=args.input_jsonl,
                review_json=args.review_json,
                review_md=args.review_md,
                model=args.model,
            )
            continue
        if args.max_calls is not None and calls >= args.max_calls:
            break
        print(f"[{idx}/{len(cases)}] reviewing {case['source']} {case['task_family']}", file=sys.stderr)
        last_error = None
        for attempt in range(3):
            try:
                content = chat(build_prompt(case), model=args.model, gptapi_dir=args.gptapi_dir)
                review = validate_review(case, extract_json(content))
                reviews_by_id[case["id"]] = review
                calls += 1
                write_outputs(
                    cases,
                    reviews_by_id,
                    input_jsonl=args.input_jsonl,
                    review_json=args.review_json,
                    review_md=args.review_md,
                    model=args.model,
                )
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < 2:
                    time.sleep(2 + attempt * 5)
        else:
            raise RuntimeError(f"failed to review {case['id']}: {last_error}") from last_error

    write_outputs(
        cases,
        reviews_by_id,
        input_jsonl=args.input_jsonl,
        review_json=args.review_json,
        review_md=args.review_md,
        model=args.model,
    )
    print(args.review_json)
    print(args.review_md)


if __name__ == "__main__":
    main()
