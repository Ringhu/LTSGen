#!/usr/bin/env python3
"""Review natural TS-QA pilot cases with an OpenAI-compatible GPT reviewer."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]
CASE_ROOT = ROOT / ".research/general-qcc-captioner-20260515/natural_qa_pilot_20260519"
PILOT_JSON = CASE_ROOT / "natural_tsqa_case_pilot.json"
OUT_JSON = CASE_ROOT / "natural_tsqa_case_pilot_gpt55_review.json"
OUT_MD = CASE_ROOT / "NATURAL_TSQA_CASE_PILOT_GPT55_REVIEW_20260519_ZH.md"


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


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


def chat(prompt: str, *, model: str = "gpt-5.5") -> str:
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
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    return body["choices"][0]["message"]["content"]


def build_prompt(case: dict) -> str:
    review_payload = {
        "case_key": case["case_key"],
        "source": case["source"],
        "scene_en": case["scene_en"],
        "scene_zh": case["scene_zh"],
        "question_en": case["question_en"],
        "question_zh": case["question_zh"],
        "options": case["options"],
        "gold_answer": case["gold_answer"],
        "gold_answer_zh": case["gold_answer_zh"],
        "evidence_en": case["evidence_en"],
        "evidence_zh": case["evidence_zh"],
        "support_slots": case["support_slots"],
        "original_question": case["original_question"],
    }
    return dedent(
        f"""
        You are reviewing natural-language time-series QA case studies for a research paper.

        Requirements:
        - Judge whether the QA reads like a normal domain question, not a verifier-slot prompt.
        - Judge whether the question is answerable from the provided scene, plot variables, options, and evidence.
        - Do not change the gold answer unless the supplied evidence contradicts it.
        - Penalize hidden context, internal IDs, unexplained global/local time axes, and options that require unstated thresholds.
        - Prefer concise scene + natural decision question + human-readable options.

        Return JSON only with this schema:
        {{
          "case_key": string,
          "decision": "keep" | "revise" | "reject",
          "naturalness_score": integer 1-5,
          "answerability_score": integer 1-5,
          "accuracy_risk": "low" | "medium" | "high",
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


def build_markdown(reviews: list[dict]) -> str:
    lines = [
        "# GPT-5.5 Reviewer: Natural TS-QA Case Pilot（2026-05-19）",
        "",
        "Reviewer 只评估自然性、可答性和潜在准确性风险；gold answer 仍来自 deterministic support slots。",
        "",
        "| case | decision | naturalness | answerability | risk | reason |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for review in reviews:
        lines.append(
            "| {case_key} | {decision} | {naturalness_score} | {answerability_score} | {accuracy_risk} | {reason_zh} |".format(
                **review
            )
        )
    lines.append("")
    for review in reviews:
        lines.extend(
            [
                f"## {review['case_key']}",
                "",
                f"**Decision:** `{review['decision']}`  ",
                f"**Naturalness:** `{review['naturalness_score']}`  ",
                f"**Answerability:** `{review['answerability_score']}`  ",
                f"**Accuracy risk:** `{review['accuracy_risk']}`",
                "",
                f"**理由:** {review['reason_zh']}",
                "",
                f"**建议场景:** {review['suggested_scene_zh']}",
                "",
                f"**建议问题:** {review['suggested_question_zh']}",
                "",
                "**建议选项:**",
                "",
                *[f"- {opt}" for opt in review["suggested_options_zh"]],
                "",
                f"**可沉淀规则:** {review['large_scale_rule_zh']}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    cases = json.loads(PILOT_JSON.read_text(encoding="utf-8"))["cases"]
    reviews = []
    for case in cases:
        print(f"reviewing {case['case_key']}", file=sys.stderr)
        content = chat(build_prompt(case))
        review = extract_json(content)
        reviews.append(review)
    OUT_JSON.write_text(json.dumps({"reviews": reviews}, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(reviews), encoding="utf-8")
    print(OUT_JSON)
    print(OUT_MD)


if __name__ == "__main__":
    main()
