#!/usr/bin/env python3
"""Review Natural-QCC seed artifacts before scaling or caption-model training."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CASE_DIR = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_case_quality_v1_20260521"
SELF_DIR = ROOT / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521"
DEFAULT_OUT = ROOT / ".research/general-qcc-captioner-20260515/seed_quality_review_v1_20260521"

DOMAINS = ("grid2op", "citylearn", "traffic", "water", "aiopslab", "finrl")
INTERNAL_PATTERNS = (
    "segment_tag",
    "post",
    "bucket",
    "window_start",
    "window_end",
    "support_slot",
    "source_row",
    "scenario_first_pilot",
)
SIMULATOR_NAMES = ("Grid2Op", "CityLearn", "SUMO", "WNTR", "AIOpsLab")
VAGUE_X2_TERMS = ("上下文", "辅助上下文", "背景价格信号")
CAPTION_ANSWER_LEAK_PATTERNS = (
    "Answer label",
    "答案是",
    "supports the answer",
    "therefore supports",
)
TASK_WEAKNESS = {
    "city_domain_demand_context": "阈值是当前 case 临时写入的经验阈值，仍需改成数据生成规范里的正式业务规则。",
    "water_domain_resilience_context": "漏损压力状态的判定依赖最低水压、平均水压、流量的组合，但题面还没有给出足够明确的优先级规则。",
    "water_leak_counterfactual_pressure": "选项里的“影响方向混合”不够自然，建议改成更业务化的复核/无明显变化选项。",
    "aiops_official_memory_extrema": "这题主要问峰值位置，推理深度偏弱，可保留作 easy split，但不应作为主打 case。",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def has_any(text: str, patterns: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    return [pattern for pattern in patterns if pattern.lower() in lower]


def has_number(text: str) -> bool:
    return bool(re.search(r"\d", text))


def score_from_issues(base: int, major: int, minor: int) -> int:
    return max(1, min(5, base - major - (1 if minor >= 2 else 0)))


def decision_from_scores(naturalness: int, answerability: int, accuracy_risk: str, caption_train_ready: bool) -> str:
    if accuracy_risk == "high" or naturalness <= 2 or answerability <= 2:
        return "reject"
    if naturalness >= 4 and answerability >= 4 and accuracy_risk == "low" and caption_train_ready:
        return "keep"
    return "revise"


def review_case_row(row: dict[str, Any]) -> dict[str, Any]:
    row_id = row["id"]
    issues: list[dict[str, str]] = []
    recommendations: list[str] = []
    scene = row.get("scene_zh", "")
    rule = row.get("rule_zh", "")
    question = row.get("question_zh", "")
    caption_zh = row.get("caption_zh", "")
    caption_en = row.get("caption_en", "")
    options = row.get("options_zh") or []
    answer_zh = row.get("answer_zh", "")
    combined_reader_text = "\n".join([scene, rule, question, "\n".join(options), caption_zh])

    required_fields = ("scene_zh", "rule_zh", "question_zh", "caption_zh", "caption_en", "answer_zh")
    for field in required_fields:
        if not row.get(field):
            issues.append({"severity": "major", "code": f"missing_{field}", "message": f"缺少 {field}"})
    if len(options) != 4:
        issues.append({"severity": "major", "code": "bad_option_count", "message": "选项数量不是 4 个"})

    leaked = has_any(combined_reader_text, INTERNAL_PATTERNS)
    if leaked:
        issues.append({"severity": "major", "code": "internal_id_leak", "message": f"读者文本仍含内部标识: {', '.join(leaked)}"})
    simulators = has_any(scene, SIMULATOR_NAMES)
    if simulators:
        issues.append({"severity": "minor", "code": "simulator_name_in_scene", "message": f"场景仍使用 simulator 名称: {', '.join(simulators)}"})
        recommendations.append("把 simulator 名称改成普通领域表述，例如“电网运行窗口”“建筑能耗窗口”“路网窗口”。")
    if any(term in scene for term in VAGUE_X2_TERMS):
        issues.append({"severity": "minor", "code": "vague_variable_definition", "message": "变量定义仍有“上下文/辅助信号”等模糊表述"})
        recommendations.append("把 x1/x2/x3 的业务含义写成可操作变量，不能只说上下文或辅助信号。")
    if len(rule) < 30:
        issues.append({"severity": "major", "code": "rule_too_thin", "message": "前置规则过短，难以支撑业务判断"})
    if not has_number(caption_zh):
        issues.append({"severity": "major", "code": "caption_no_numeric_evidence", "message": "中文 caption 没有可复核数值证据"})
    if answer_zh and answer_zh not in caption_zh and row.get("answer_label", "") not in caption_en:
        issues.append({"severity": "minor", "code": "caption_conclusion_implicit", "message": "caption 结论与答案标签的对应不够直接"})
    if not caption_en or not caption_zh:
        zh_en_aligned = False
    else:
        zh_en_aligned = has_number(caption_zh) == has_number(caption_en)
        if not zh_en_aligned:
            issues.append({"severity": "minor", "code": "zh_en_numeric_alignment_weak", "message": "中英文 caption 的数值证据呈现不一致"})
    if row["task_family"] in TASK_WEAKNESS:
        issues.append({"severity": "minor", "code": "known_task_weakness", "message": TASK_WEAKNESS[row["task_family"]]})
        recommendations.append(TASK_WEAKNESS[row["task_family"]])
    answer_leaks = has_any(caption_en, CAPTION_ANSWER_LEAK_PATTERNS)
    if answer_leaks:
        issues.append({"severity": "minor", "code": "caption_answer_phrase", "message": "英文 caption 有显式 answer-support 模板句，训练目标应改成更自然的 evidence-only 表述"})
        recommendations.append("训练 caption 时去掉“supports the answer”等模板句，保留时序现象和判断依据。")

    major = sum(1 for issue in issues if issue["severity"] == "major")
    minor = sum(1 for issue in issues if issue["severity"] == "minor")
    naturalness = score_from_issues(5, major, minor)
    answerability = score_from_issues(5, major, 0)
    accuracy_risk = "high" if major >= 2 else "medium" if major == 1 or minor >= 3 else "low"
    caption_train_ready = major == 0 and not answer_leaks and not any(issue["code"] == "caption_no_numeric_evidence" for issue in issues)
    decision = decision_from_scores(naturalness, answerability, accuracy_risk, caption_train_ready)
    if not recommendations and decision == "keep":
        recommendations.append("可作为高质量 case seed；扩增时保持当前场景-规则-问题-caption 结构。")
    elif not recommendations:
        recommendations.append("按 issues 修订题面、变量说明和 caption 后再进入扩增。")

    return {
        "id": row_id,
        "seed_set": "natural_qcc_case_quality_v1",
        "domain": row["merge_source_name"],
        "task_family": row["task_family"],
        "decision": decision,
        "qa_seed_ready": major == 0 and accuracy_risk != "high",
        "caption_train_ready": caption_train_ready,
        "naturalness_score": naturalness,
        "answerability_score": answerability,
        "accuracy_risk": accuracy_risk,
        "zh_en_aligned": zh_en_aligned,
        "issue_count": len(issues),
        "issues": issues,
        "recommendations": recommendations,
    }


def review_self_row(row: dict[str, Any], probe_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    recommendations: list[str] = []
    scene_zh = row.get("scene_zh", "")
    rule_zh = row.get("decision_rule_zh", "")
    variables_zh = row.get("variables_zh") or []
    question_zh = row.get("question_zh", "")
    evidence = row.get("natural_evidence_caption", "")
    evidence_zh = row.get("natural_evidence_zh", "")
    target_caption = row.get("target_caption", "")
    options = row.get("options_zh") or []
    probe = probe_by_id.get(row["id"])
    combined_reader_text = "\n".join([scene_zh, rule_zh, "\n".join(variables_zh), question_zh, "\n".join(options)])

    required = {
        "scene_zh": scene_zh,
        "decision_rule_zh": rule_zh,
        "question_zh": question_zh,
        "natural_evidence_zh": evidence_zh,
        "target_caption": target_caption,
    }
    for field, value in required.items():
        if not value:
            issues.append({"severity": "major", "code": f"missing_{field}", "message": f"缺少 {field}"})
    if len(variables_zh) < 2:
        issues.append({"severity": "major", "code": "too_few_variables", "message": "变量定义不足"})
    if len(options) != 4:
        issues.append({"severity": "major", "code": "bad_option_count", "message": "选项数量不是 4 个"})
    leaked = has_any(combined_reader_text, INTERNAL_PATTERNS)
    if leaked:
        issues.append({"severity": "major", "code": "internal_id_leak", "message": f"读者文本仍含内部标识: {', '.join(leaked)}"})
    if not row.get("background_self_contained", False) or row.get("simulator_prior_required", True):
        issues.append({"severity": "major", "code": "not_self_contained_by_flag", "message": "自包含标记不满足"})
    if row.get("requires_reasoning") is not True:
        issues.append({"severity": "major", "code": "requires_reasoning_false", "message": "没有标记为需要推理"})
    if not has_number(rule_zh):
        issues.append({"severity": "minor", "code": "rule_without_numeric_threshold", "message": "规则没有显式数字阈值或比例"})
    if has_any(target_caption, ("Answer label",)):
        issues.append({"severity": "major", "code": "target_caption_answer_label_leak", "message": "target_caption 包含 Answer label，不适合作为 evidence-only caption 训练目标"})
        recommendations.append("生成 SFT 前移除 target_caption 中的 Answer label 句子。")
    if has_any(evidence, ("the rule maps this to",)) or has_any(evidence_zh, ("按规则判断为",)):
        issues.append({"severity": "minor", "code": "caption_too_rule_template_like", "message": "evidence caption 仍偏规则模板，缺少自然时序总述"})
        recommendations.append("caption 应先概括时序整体形态，再给关键派生量和结论。")
    if row["merge_source_name"] in {"citylearn", "water"}:
        issues.append({"severity": "minor", "code": "domain_known_review_priority", "message": "该域在 GPT data-only probe 中错误较多，需要优先人工复核规则边界。"})
    if probe:
        if not probe.get("semantic_correct", False):
            issues.append({"severity": "major", "code": "gpt_data_only_wrong", "message": "GPT data-only probe 未能从题面和数据推出正确语义答案"})
            recommendations.append("重写规则、变量说明或 compact features；这条暂不进入正例扩增。")
        if probe.get("label_letter_mismatch"):
            issues.append({"severity": "major", "code": "probe_letter_label_mismatch", "message": "probe 输出的答案字母和标签不一致"})
    else:
        issues.append({"severity": "minor", "code": "missing_probe_result", "message": "缺少 GPT data-only probe 结果"})

    qa_blocking_codes = {
        "missing_scene_zh",
        "missing_decision_rule_zh",
        "missing_question_zh",
        "too_few_variables",
        "bad_option_count",
        "internal_id_leak",
        "not_self_contained_by_flag",
        "requires_reasoning_false",
        "gpt_data_only_wrong",
        "probe_letter_label_mismatch",
    }
    caption_blocking_codes = {
        "missing_natural_evidence_zh",
        "missing_target_caption",
        "target_caption_answer_label_leak",
    }
    major = sum(1 for issue in issues if issue["severity"] == "major")
    qa_major = sum(1 for issue in issues if issue["code"] in qa_blocking_codes)
    caption_major = sum(1 for issue in issues if issue["code"] in caption_blocking_codes)
    minor = sum(1 for issue in issues if issue["severity"] == "minor")
    naturalness = max(1, min(5, int(row.get("review_naturalness_score", 4)) - (1 if minor >= 3 else 0) - qa_major))
    answerability = max(1, min(5, int(row.get("review_answerability_score", 4)) - qa_major))
    accuracy_risk = "high" if qa_major >= 2 else "medium" if qa_major == 1 or minor >= 3 else row.get("review_accuracy_risk", "low")
    qa_seed_ready = qa_major == 0 and probe is not None and probe.get("semantic_correct", False)
    caption_train_ready = qa_seed_ready and caption_major == 0
    decision = decision_from_scores(naturalness, answerability, accuracy_risk, caption_train_ready)
    if decision == "keep" and not recommendations:
        recommendations.append("可作为 self-contained reasoning seed；扩增时仍需做答案字母平衡。")
    elif not recommendations:
        recommendations.append("先修复 major/minor issues，再进入扩增或训练。")

    return {
        "id": row["id"],
        "seed_set": "self_contained_reasoning_qa_v2",
        "domain": row["merge_source_name"],
        "task_family": row["task_family"],
        "decision": decision,
        "qa_seed_ready": qa_seed_ready,
        "caption_train_ready": caption_train_ready,
        "naturalness_score": naturalness,
        "answerability_score": answerability,
        "accuracy_risk": accuracy_risk,
        "gpt_data_only_semantic_correct": None if probe is None else bool(probe.get("semantic_correct", False)),
        "gpt_data_only_letter_correct": None if probe is None else bool(probe.get("letter_correct", False)),
        "issue_count": len(issues),
        "issues": issues,
        "recommendations": recommendations,
    }


def load_probe(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row for row in data.get("predictions", [])}


def counter_dict(values: list[str]) -> dict[str, int]:
    return dict(Counter(values))


def summarize(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    by_seed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for review in reviews:
        by_seed[review["seed_set"]].append(review)
    out: dict[str, Any] = {
        "n": len(reviews),
        "decision_counts": counter_dict([r["decision"] for r in reviews]),
        "qa_seed_ready_count": sum(1 for r in reviews if r["qa_seed_ready"]),
        "caption_train_ready_count": sum(1 for r in reviews if r["caption_train_ready"]),
        "by_seed": {},
        "by_domain": {},
        "top_issue_codes": counter_dict([issue["code"] for r in reviews for issue in r["issues"]]),
    }
    for seed, rows in by_seed.items():
        out["by_seed"][seed] = {
            "n": len(rows),
            "decision_counts": counter_dict([r["decision"] for r in rows]),
            "qa_seed_ready_count": sum(1 for r in rows if r["qa_seed_ready"]),
            "caption_train_ready_count": sum(1 for r in rows if r["caption_train_ready"]),
        }
    for domain in sorted({r["domain"] for r in reviews}):
        rows = [r for r in reviews if r["domain"] == domain]
        out["by_domain"][domain] = {
            "n": len(rows),
            "decision_counts": counter_dict([r["decision"] for r in rows]),
            "qa_seed_ready_count": sum(1 for r in rows if r["qa_seed_ready"]),
            "caption_train_ready_count": sum(1 for r in rows if r["caption_train_ready"]),
        }
    return out


def zh_report(summary: dict[str, Any], case_reviews: list[dict[str, Any]], self_reviews: list[dict[str, Any]], out_dir: Path) -> str:
    def primary_suggestion(review: dict[str, Any]) -> str:
        if not review["qa_seed_ready"]:
            for suggestion in review["recommendations"]:
                if "重写规则" in suggestion or "暂不进入正例扩增" in suggestion:
                    return suggestion
        if review["qa_seed_ready"] and not review["caption_train_ready"]:
            for suggestion in review["recommendations"]:
                if "Answer label" in suggestion or "supports the answer" in suggestion:
                    return suggestion
        return review["recommendations"][0] if review["recommendations"] else ""

    qa_rewrite = [r for r in self_reviews if not r["qa_seed_ready"]]
    caption_only_repair = [r for r in self_reviews if r["qa_seed_ready"] and not r["caption_train_ready"]]
    clean_case_studies = [r for r in case_reviews if r["decision"] == "keep"]
    caption_ready_cases = [r for r in case_reviews if r["caption_train_ready"]]

    lines: list[str] = []
    lines.append("# Natural-QCC Seed Quality Review v1（2026-05-21）")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    lines.append("这轮 review 的核心结论是：现有 seed 可以作为下一版扩增规范的起点，但还不能直接大规模扩增或训练 caption model。")
    lines.append("")
    lines.append(f"- 总 review 条目：{summary['n']}")
    lines.append(f"- QA seed ready：{summary['qa_seed_ready_count']}/{summary['n']}")
    lines.append(f"- caption train ready：{summary['caption_train_ready_count']}/{summary['n']}")
    lines.append(f"- decision counts：{summary['decision_counts']}")
    lines.append("")
    lines.append("最重要的问题是：`self_contained_reasoning_qa_v2` 的 QA 结构比早期版本更好，但 `target_caption` 里仍带 `Answer label`，所以不能直接当 evidence-only caption 训练目标。`natural_qcc_case_quality_v1` 更适合人工看 case，但其中若干变量解释和业务规则仍需重写。")
    lines.append("")
    lines.append("## 一句话判断")
    lines.append("")
    lines.append("- **可以继续当 QA seed 的样本较多**：72 条里有 57 条 QA seed ready。")
    lines.append("- **不能直接训练 caption model**：只有 10 条 caption train ready；self-contained v2 的 60 条都需要先清洗 target caption。")
    lines.append("- **最该先修的不是扩量，而是 target caption 和 CityLearn/Water 规则边界**。")
    lines.append("")
    lines.append("## 修复队列")
    lines.append("")
    lines.append("| 队列 | 数量 | 含义 | 下一步 |")
    lines.append("| --- | ---: | --- | --- |")
    lines.append(f"| case-study 可展示 seed | {len(clean_case_studies)} | `natural_qcc_case_quality_v1` 中基本可给人看的 case | 去掉 simulator 名称和少量模板句后可继续用 |")
    lines.append(f"| case-study caption-ready seed | {len(caption_ready_cases)} | 12 条 case 中 caption 监督基本可用的条目 | 可作为 v3 caption 写法模板 |")
    lines.append(f"| self-contained QA 可用但 caption 需清洗 | {len(caption_only_repair)} | 题面/规则/数据基本可答，但 target caption 不合格 | 删除 `Answer label`，把规则模板改成自然 evidence caption |")
    lines.append(f"| self-contained QA 需重写 | {len(qa_rewrite)} | GPT data-only probe 语义答错或规则边界不清 | 优先重写 CityLearn/Water/Traffic/AIOps/FinRL 的失败样本 |")
    lines.append("")
    lines.append("## 分集合结果")
    lines.append("")
    lines.append("| seed set | n | decision | QA ready | caption train ready |")
    lines.append("| --- | ---: | --- | ---: | ---: |")
    for seed, stats in summary["by_seed"].items():
        lines.append(
            f"| `{seed}` | {stats['n']} | {stats['decision_counts']} | "
            f"{stats['qa_seed_ready_count']} | {stats['caption_train_ready_count']} |"
        )
    lines.append("")
    lines.append("## 分域结果")
    lines.append("")
    lines.append("| domain | n | decision | QA ready | caption train ready |")
    lines.append("| --- | ---: | --- | ---: | ---: |")
    for domain, stats in summary["by_domain"].items():
        lines.append(
            f"| `{domain}` | {stats['n']} | {stats['decision_counts']} | "
            f"{stats['qa_seed_ready_count']} | {stats['caption_train_ready_count']} |"
        )
    lines.append("")
    lines.append("## 主要问题")
    lines.append("")
    for code, count in sorted(summary["top_issue_codes"].items(), key=lambda x: (-x[1], x[0]))[:12]:
        lines.append(f"- `{code}`: {count}")
    lines.append("")
    lines.append("解释：")
    lines.append("")
    lines.append("- `target_caption_answer_label_leak`：caption 目标里显式写了答案标签，这会把 evidence caption 训练成答案复述，不符合 evidence-only QCC。")
    lines.append("- `caption_too_rule_template_like`：caption 更像规则执行结果，而不是先描述时序形态再解释判断。")
    lines.append("- `gpt_data_only_wrong`：强 LLM 只看题面和数据时答错，说明题面/规则/compact features 仍有歧义。")
    lines.append("- `vague_variable_definition`：变量仍写成上下文/辅助信号，普通回答者不知道怎么用。")
    lines.append("")
    lines.append("## Natural-QCC Case Quality v1 逐条结论")
    lines.append("")
    lines.append("| domain | task | decision | QA ready | caption ready | 主要建议 |")
    lines.append("| --- | --- | --- | ---: | ---: | --- |")
    for r in case_reviews:
        suggestion = primary_suggestion(r)
        lines.append(
            f"| `{r['domain']}` | `{r['task_family']}` | `{r['decision']}` | "
            f"{int(r['qa_seed_ready'])} | {int(r['caption_train_ready'])} | {suggestion} |"
        )
    lines.append("")
    lines.append("其中最适合先给你人工看的 case：")
    lines.append("")
    for r in clean_case_studies:
        lines.append(f"- `{r['domain']}` / `{r['task_family']}`")
    lines.append("")
    lines.append("## Self-contained Reasoning QA v2 逐条结论")
    lines.append("")
    lines.append("这 60 条的主要作用是扩增 seed，不是 case-study 展示稿。当前有 45 条 QA 本身可用但 caption target 需要统一清洗；15 条 QA 本身也要改。")
    lines.append("")
    lines.append("| domain | task | decision | QA ready | caption ready | 主要建议 |")
    lines.append("| --- | --- | --- | ---: | ---: | --- |")
    for r in self_reviews:
        suggestion = primary_suggestion(r)
        lines.append(
            f"| `{r['domain']}` | `{r['task_family']}` | `{r['decision']}` | "
            f"{int(r['qa_seed_ready'])} | {int(r['caption_train_ready'])} | {suggestion} |"
        )
    lines.append("")
    lines.append("## Self-contained QA 需重写样本分布")
    lines.append("")
    if qa_rewrite:
        by_domain = Counter(r["domain"] for r in qa_rewrite)
        by_task = Counter(r["task_family"] for r in qa_rewrite)
        lines.append(f"- by domain: {dict(by_domain)}")
        lines.append(f"- by task: {dict(by_task)}")
        lines.append("")
        lines.append("这些样本不应该进入下一版正例池，除非先重写规则/变量说明并重新跑 data-only probe。")
    else:
        lines.append("- 暂无 QA 需重写样本。")
    lines.append("")
    lines.append("## 下一步修复顺序")
    lines.append("")
    lines.append("1. 先修 caption target：从 self-contained v2 的 `target_caption/output` 中移除 `Answer label`，改成 evidence-only。")
    lines.append("2. 再修 CityLearn/Water：把负类、阈值边界和优先级规则写得更清楚，重新跑 GPT data-only probe。")
    lines.append("3. 重写 Natural-QCC case-quality 中的模糊变量：尤其是 `上下文/辅助信号/背景价格信号`。")
    lines.append("4. 用本脚本作为 reviewer gate，只有 QA ready 和 caption train ready 都通过的样本才进入扩增和 qcond/no-question 训练。")
    lines.append("")
    lines.append("## 产物")
    lines.append("")
    lines.append(f"- review JSONL: `{out_dir / 'natural_qcc_seed_quality_review_v1.jsonl'}`")
    lines.append(f"- summary JSON: `{out_dir / 'natural_qcc_seed_quality_review_v1_summary.json'}`")
    lines.append(f"- report: `{out_dir / 'NATURAL_QCC_SEED_QUALITY_REVIEW_V1_20260521_ZH.md'}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case_rows", type=Path, default=CASE_DIR / "natural_qcc_case_quality_v1.jsonl")
    parser.add_argument("--self_rows", type=Path, default=SELF_DIR / "self_contained_reasoning_tsqa.jsonl")
    parser.add_argument("--probe", type=Path, default=SELF_DIR / "self_contained_reasoning_tsqa_gpt_data_only_probe.json")
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    case_rows = load_jsonl(args.case_rows)
    self_rows = load_jsonl(args.self_rows)
    probe_by_id = load_probe(args.probe)

    case_reviews = [review_case_row(row) for row in case_rows]
    self_reviews = [review_self_row(row, probe_by_id) for row in self_rows]
    reviews = case_reviews + self_reviews
    summary = summarize(reviews)
    summary["inputs"] = {
        "case_rows": str(args.case_rows.relative_to(ROOT)),
        "self_rows": str(args.self_rows.relative_to(ROOT)),
        "probe": str(args.probe.relative_to(ROOT)),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "natural_qcc_seed_quality_review_v1.jsonl", reviews)
    write_json(args.out_dir / "natural_qcc_seed_quality_review_v1_summary.json", summary)
    report = zh_report(summary, case_reviews, self_reviews, args.out_dir.relative_to(ROOT))
    (args.out_dir / "NATURAL_QCC_SEED_QUALITY_REVIEW_V1_20260521_ZH.md").write_text(report + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
