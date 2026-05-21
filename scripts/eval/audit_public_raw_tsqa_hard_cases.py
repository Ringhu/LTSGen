#!/usr/bin/env python3
"""Audit hard-but-fair candidates for Public Raw TSQA v4.

The script is intentionally deterministic. It does not declare GPT-5.5 failures
as final hard cases; it only builds the evidence table that a reviewer should
use before promoting a row into a hard benchmark subset.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / ".research/general-qcc-captioner-20260515/public_raw_tsqa_v4_20260521"
DEFAULT_EVAL_DIR = DEFAULT_DATA_DIR / "model_eval_20260521"
DEFAULT_OUT_JSONL = DEFAULT_DATA_DIR / "hard_case_audit_20260521.jsonl"
DEFAULT_OUT_MD = DEFAULT_DATA_DIR / "PUBLIC_RAW_TSQA_V4_HARD_CASE_AUDIT_20260521_ZH.md"
DEFAULT_MODEL_ASSET_JSON = DEFAULT_DATA_DIR / "qwen_model_asset_audit_20260521.json"
DEFAULT_REVIEWER_JSONL = DEFAULT_DATA_DIR / "hard_candidate_reviewer_20260521.jsonl"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_keyed_jsonl(path: Path, key: str = "id") -> dict[str, dict[str, Any]]:
    return {row[key]: row for row in load_jsonl(path)}


def fmt_acc(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value):.4f}"


def short(text: str, n: int = 90) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "..."


def support_summary(slots: dict[str, Any]) -> str:
    items = []
    for key, value in slots.items():
        if key == "verifier_answer_label":
            continue
        if isinstance(value, float):
            items.append(f"{key}={value:.4g}")
        else:
            items.append(f"{key}={value}")
    return "; ".join(items[:5])


def is_full_run(metrics: dict[str, Any]) -> bool:
    run = metrics.get("run", {})
    overall = metrics.get("overall", {})
    return int(run.get("n_rows") or 0) == 39 and int(overall.get("n") or 0) == 78


def load_runs(eval_dir: Path) -> list[dict[str, Any]]:
    runs = []
    for metrics_path in sorted(eval_dir.glob("*/metrics.json")):
        metrics = load_json(metrics_path)
        if not is_full_run(metrics):
            continue
        pred_path = metrics_path.parent / "predictions.jsonl"
        if not pred_path.is_file():
            continue
        run = metrics.get("run", {})
        overall = metrics.get("overall", {})
        by_language = metrics.get("by_language", {})
        by_domain = metrics.get("by_domain", {})
        runs.append(
            {
                "run_name": metrics_path.parent.name,
                "provider": run.get("provider", ""),
                "model": run.get("model", ""),
                "accuracy": overall.get("accuracy"),
                "en_accuracy": by_language.get("en", {}).get("accuracy"),
                "zh_accuracy": by_language.get("zh", {}).get("accuracy"),
                "water_service_accuracy": by_domain.get("water_service", {}).get("accuracy"),
                "predictions_path": pred_path,
                "metrics_path": metrics_path,
            }
        )
    runs.sort(key=lambda row: (-float(row.get("accuracy") or 0.0), row["run_name"]))
    return runs


def select_top_run(runs: list[dict[str, Any]], preferred_model: str) -> dict[str, Any]:
    for run in runs:
        if run["model"] == preferred_model or run["run_name"] == preferred_model:
            return run
    for run in runs:
        if "gpt-5.5" in run["model"] or "gpt55" in run["run_name"]:
            return run
    if not runs:
        raise SystemExit("No complete full bilingual runs found.")
    return runs[0]


def build_prediction_index(runs: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    out: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for run in runs:
        for row in load_jsonl(run["predictions_path"]):
            out[(row["id"], row["language"])][run["run_name"]] = row
    return out


def verifier_supported(audit: dict[str, Any]) -> bool:
    gate = audit.get("reviewer_gate") or {}
    return bool(
        audit.get("raw_gold_matches_v3") is True
        and gate.get("v3_positive_seed_ready") is True
        and gate.get("v3_probe_status") == "pass"
    )


def manual_review_note(case_id: str) -> tuple[str, str]:
    """Known manual notes from deterministic audit of the current pilot."""
    if case_id == "public_raw_tsqa_v4_00019":
        return (
            "revise",
            "GPT-5.5 错在 water_service，但 public prompt 只说 before-during-after，没有给出事件分段边界；该错题更像窗口分段歧义，不应直接作为 hard。",
        )
    if case_id == "public_raw_tsqa_v4_00021":
        return (
            "revise",
            "GPT-5.5 错在 persistent leak/recovery 边界；support slots 支持 A，但 public prompt 对“remains depressed / close to pre-event”的阈值不够硬，需要重写阈值表达。",
        )
    return ("pending", "需要 reviewer 判断是否是真实时序推理困难，而非题面歧义。")


def classify_prompt(
    key: tuple[str, str],
    preds: dict[str, dict[str, Any]],
    runs: list[dict[str, Any]],
    top_run: dict[str, Any],
    audit_by_id: dict[str, dict[str, Any]],
    canonical_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    case_id, language = key
    canonical = canonical_by_id.get(case_id, {})
    audit = audit_by_id.get(case_id, {})
    top_pred = preds.get(top_run["run_name"], {})
    model_results = []
    wrong_runs = []
    correct_runs = []
    for run in runs:
        pred = preds.get(run["run_name"], {})
        correct = bool(pred.get("correct")) if pred else False
        record = {
            "run_name": run["run_name"],
            "model": run["model"],
            "provider": run["provider"],
            "correct": correct,
            "pred_answer": pred.get("pred_answer", ""),
            "reason": pred.get("reason", ""),
        }
        model_results.append(record)
        (correct_runs if correct else wrong_runs).append(run["run_name"])

    top_wrong = bool(top_pred) and not bool(top_pred.get("correct"))
    support_ok = verifier_supported(audit)
    wrong_count = len(wrong_runs)
    tags = []
    if support_ok:
        tags.append("verifier_supported")
    else:
        tags.append("verifier_or_seed_gate_missing")
    if top_wrong:
        tags.append("top_closed_model_wrong")
    if wrong_count == len(runs):
        tags.append("all_current_models_wrong")
    if wrong_count >= max(3, len(runs) - 1):
        tags.append("multi_model_failure")
    if not top_wrong and wrong_count >= 3:
        tags.append("scaling_sensitive")
    if canonical.get("domain") == "water_service":
        tags.append("water_boundary_review")

    if top_wrong and support_ok:
        decision = "candidate_hard_needs_review"
    elif not top_wrong and wrong_count >= 3 and support_ok:
        decision = "scaling_sensitive_medium"
    elif support_ok:
        decision = "verified_easy_or_medium"
    else:
        decision = "reject_or_repair"

    review_decision, review_note = manual_review_note(case_id) if top_wrong else ("not_required", "")
    if top_wrong and review_decision == "revise":
        decision = "revise_before_hard"
        tags.append("not_certified_hard")

    return {
        "id": case_id,
        "language": language,
        "domain": canonical.get("domain", top_pred.get("domain", "")),
        "task_family": canonical.get("task_family", top_pred.get("task_family", "")),
        "gold_answer": canonical.get("answer", top_pred.get("gold_answer", "")),
        "answer_label": canonical.get("answer_label", top_pred.get("gold_answer_label", "")),
        "answer_label_zh": canonical.get("answer_label_zh", ""),
        "top_model": top_run["model"],
        "top_model_run": top_run["run_name"],
        "top_model_correct": not top_wrong,
        "top_model_pred_answer": top_pred.get("pred_answer", ""),
        "top_model_reason": top_pred.get("reason", ""),
        "wrong_model_count": wrong_count,
        "correct_model_count": len(correct_runs),
        "wrong_runs": wrong_runs,
        "correct_runs": correct_runs,
        "decision": decision,
        "tags": tags,
        "support_ok": support_ok,
        "deterministic_rule_id": audit.get("deterministic_rule_id", ""),
        "support_summary": support_summary(audit.get("support_slots") or {}),
        "oracle_evidence_en": audit.get("oracle_evidence_en", ""),
        "oracle_evidence_zh": audit.get("oracle_evidence_zh", ""),
        "manual_review_decision": review_decision,
        "manual_review_note_zh": review_note,
        "natural_task_en": canonical.get("natural_task_en", ""),
        "natural_task_zh": canonical.get("natural_task_zh", ""),
        "model_results": model_results,
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def qwen_asset_rows(asset_json: Path) -> list[dict[str, Any]]:
    if not asset_json.is_file():
        return []
    payload = load_json(asset_json)
    return payload.get("models", [])


def reviewer_by_key(reviewer_jsonl: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows = load_jsonl(reviewer_jsonl)
    return {(row["id"], row["language"]): row for row in rows if "id" in row and "language" in row}


def write_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    top_run: dict[str, Any],
    asset_json: Path,
    reviewer_jsonl: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    reviews = reviewer_by_key(reviewer_jsonl)
    by_decision = Counter(row["decision"] for row in rows)
    by_domain = Counter(row["domain"] for row in rows if row["decision"] in {"candidate_hard_needs_review", "revise_before_hard"})
    top_wrong = [row for row in rows if not row["top_model_correct"]]
    revise = [row for row in rows if row["decision"] == "revise_before_hard"]
    scaling = [row for row in rows if row["decision"] == "scaling_sensitive_medium"]
    certified = [
        row
        for row in rows
        if reviews.get((row["id"], row["language"]), {}).get("hard_subset_eligible") is True
    ]
    reviewer_decisions = Counter(review.get("decision", "") for review in reviews.values())
    reviewer_eligible = Counter(str(review.get("hard_subset_eligible", False)).lower() for review in reviews.values())

    lines = [
        "# Public Raw TSQA v4 Hard-but-Fair 复核报告 2026-05-21",
        "",
        "## 结论",
        "",
        f"- 当前完整评测 run 数：`{len(runs)}`；顶级闭源参照模型：`{top_run['model']}` / `{top_run['run_name']}`。",
        f"- 顶级闭源模型错误 prompt：`{len(top_wrong)}/{len(rows)}`，全部来自 `water_service`。",
        f"- hard candidate reviewer 已复审：`{len(reviews)}` 条，decision `{dict(reviewer_decisions)}`，eligible `{dict(reviewer_eligible)}`。",
        f"- 当前可直接认证的 hard subset：`{len(certified)}`。原因：GPT-5.5 错题全部被 reviewer 判为需要修订，主要风险是事件分段和阈值表达不清。",
        "- 因此，现有 pilot 只能证明 benchmark 有模型区分度，不能直接声称“顶级闭源模型系统性答不上来”。下一步应先修复 hard case 的题面证据链，再扩增。",
        "",
        "## 完整模型结果",
        "",
        "| Run | Provider | Model | Acc. | EN | ZH | Water |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for run in runs:
        lines.append(
            f"| `{run['run_name']}` | `{run['provider']}` | `{run['model']}` | "
            f"{fmt_acc(run['accuracy'])} | {fmt_acc(run['en_accuracy'])} | "
            f"{fmt_acc(run['zh_accuracy'])} | {fmt_acc(run['water_service_accuracy'])} |"
        )

    lines.extend(
        [
            "",
            "## Hard-but-Fair Gate",
            "",
            "- `verifier_supported`：gold answer 必须来自 deterministic support slots，且 source seed/probe gate 通过。",
            "- `top_closed_model_wrong`：GPT-5.5 在完整原始时序 prompt 下答错，只作为候选信号。",
            "- `not_certified_hard`：如果错因可能来自窗口分段、阈值含糊、选项表达或隐藏上下文，则不能作为 hard subset。",
            "- `scaling_sensitive_medium`：GPT-5.5 可答对，但 GPT-5.4/Qwen 多数失败；适合作为中等难度或 scaling 分析。",
            "",
            "## 决策分布",
            "",
            f"- by decision: `{dict(by_decision)}`",
            f"- top-model wrong by domain: `{dict(by_domain)}`",
            "",
            "## 顶级模型错题复核",
            "",
            "| ID | Lang | Gold | GPT-5.5 Pred | Audit Decision | Reviewer | Eligible | Evidence | Review note |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in top_wrong:
        review = reviews.get((row["id"], row["language"]), {})
        gold = row["gold_answer"] if row["language"] == "en" else row["answer_label_zh"] or row["gold_answer"]
        pred = row["top_model_pred_answer"]
        review_note = review.get("reason_zh") or row["manual_review_note_zh"]
        lines.append(
            f"| `{row['id']}` | `{row['language']}` | `{gold}` | `{pred}` | "
            f"`{row['decision']}` | `{review.get('decision', 'pending')}` | "
            f"`{str(review.get('hard_subset_eligible', False)).lower()}` | "
            f"{short(row['support_summary'], 120)} | {short(review_note, 160)} |"
        )

    lines.extend(
        [
            "",
            "## Scaling-sensitive 样本",
            "",
            "这些样本 GPT-5.5 答对，但至少 3 个完整 run 答错，适合用来画模型能力曲线，不适合声称顶级闭源模型失败。",
            "",
            "| ID | Lang | Domain | Gold | Wrong Runs | Evidence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in scaling[:20]:
        lines.append(
            f"| `{row['id']}` | `{row['language']}` | `{row['domain']}` | `{row['gold_answer']}` | "
            f"`{len(row['wrong_runs'])}` | {short(row['support_summary'], 140)} |"
        )

    assets = qwen_asset_rows(asset_json)
    lines.extend(
        [
            "",
            "## Qwen 3B/4B/8B/32B 资产复核",
            "",
            "| Target | Status | Path/Route | Note |",
            "|---|---|---|---|",
        ]
    )
    for asset in assets:
        lines.append(
            f"| `{asset.get('target_scale','')}` | `{asset.get('status','')}` | "
            f"`{asset.get('path_or_route','')}` | {asset.get('note','')} |"
        )

    lines.extend(
        [
            "",
            "## 扩增建议",
            "",
            "1. 先重写 `water_service`：公开 prompt 必须给出事件分段或明确可由时间索引推断的分段规则，并把 `remains depressed / close to pre-event` 改成可审计阈值。",
            "2. 将 `building_energy` 的 balanced reserve、`aiops` 的 no dominant symptom、`market` 的 drawdown-priority 作为 scaling-sensitive medium pool。",
            "3. 扩增时每个样本先过 deterministic verifier，再过 reviewer gate，最后才用 GPT-5.5 失败率定义 hard subset。",
            "4. 论文中报告 easy/medium/hard 三层，不把当前 39 条直接包装成 hard benchmark。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--eval_dir", type=Path, default=DEFAULT_EVAL_DIR)
    parser.add_argument("--top_model", default="gpt-5.5")
    parser.add_argument("--out_jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    parser.add_argument("--out_md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--qwen_asset_json", type=Path, default=DEFAULT_MODEL_ASSET_JSON)
    parser.add_argument("--reviewer_jsonl", type=Path, default=DEFAULT_REVIEWER_JSONL)
    args = parser.parse_args()

    canonical = load_keyed_jsonl(args.data_dir / "canonical_raw_tsqa_v4.jsonl")
    audit = load_keyed_jsonl(args.data_dir / "audit_support.jsonl")
    runs = load_runs(args.eval_dir)
    top_run = select_top_run(runs, args.top_model)
    pred_index = build_prediction_index(runs)
    rows = [
        classify_prompt(key, preds, runs, top_run, audit, canonical)
        for key, preds in sorted(pred_index.items())
    ]
    write_jsonl(args.out_jsonl, rows)
    write_markdown(args.out_md, rows, runs, top_run, args.qwen_asset_json, args.reviewer_jsonl)
    print(
        json.dumps(
            {
                "n_prompts": len(rows),
                "runs": len(runs),
                "top_model": top_run["model"],
                "top_model_wrong": sum(1 for row in rows if not row["top_model_correct"]),
                "decisions": dict(Counter(row["decision"] for row in rows)),
                "out_jsonl": rel(args.out_jsonl),
                "out_md": rel(args.out_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
