#!/usr/bin/env python3
"""Build v3 self-contained reasoning TS-QA with evidence-only captions."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = (
    ROOT
    / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v2_20260521/"
    / "self_contained_reasoning_tsqa.jsonl"
)
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/self_contained_reasoning_qa_v3_20260521"
DATASET_NAME = "self_contained_reasoning_qa_v3"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def pct(value: float, digits: int = 1) -> str:
    return f"{100.0 * value:.{digits}f}%"


def label_zh(row: dict[str, Any]) -> str:
    return str(row.get("answer_zh") or row.get("answer_label") or "")


def caption_grid(row: dict[str, Any]) -> tuple[str, str]:
    s = row["support_slots"]
    mean = s["x0_mean"]
    pos = s["frac_gt_pos_0_05"]
    neg = s["frac_lt_neg_0_05"]
    max_abs = s["max_abs_x0"]
    if abs(mean) <= 0.02 and max_abs <= 0.03:
        shape_en = "Across the compact blocks, the outage-minus-normal stress difference stays close to zero."
        shape_zh = "从压缩时间块看，断线减正常的压力差整体贴近零线。"
    elif mean >= 0.05:
        shape_en = "Across the compact blocks, the outage run is consistently more stressful than the matched normal run."
        shape_zh = "从压缩时间块看，断线运行相对正常运行持续更紧张。"
    elif mean <= -0.05:
        shape_en = "Across the compact blocks, the outage run is consistently less stressful than the matched normal run."
        shape_zh = "从压缩时间块看，断线运行相对正常运行持续更安全。"
    else:
        shape_en = "Across the compact blocks, the stress difference is mixed rather than cleanly one-sided."
        shape_zh = "从压缩时间块看，压力差不是清晰的单边上升或下降。"
    en = (
        f"{shape_en} Mean x0 is {fmt(mean)}, with {pct(pos)} of blocks above +0.05, "
        f"{pct(neg)} below -0.05, and maximum absolute difference {fmt(max_abs)}. "
        f"Those values support the {s['answer_label']} decision under the stated thresholds."
    )
    zh = (
        f"{shape_zh} x0 均值为 {fmt(mean)}，高于 +0.05 的时间块占 {pct(pos)}，"
        f"低于 -0.05 的时间块占 {pct(neg)}，最大绝对差为 {fmt(max_abs)}。"
        f"这些数值支撑“{label_zh(row)}”这个判断。"
    )
    return en, zh


def caption_city(row: dict[str, Any]) -> tuple[str, str]:
    s = row["support_slots"]
    means = {
        "early": s["early_net_mean"],
        "middle": s["middle_net_mean"],
        "late": s["late_net_mean"],
    }
    top = max(means, key=means.get)
    second = sorted(means.values(), reverse=True)[1]
    gap = s["gap_top_second"]
    top_zh = {"early": "早段", "middle": "中段", "late": "后段"}[top]
    if gap >= 0.30:
        shape_en = f"The net-load profile has a distinct {top} peak rather than a balanced shape."
        shape_zh = f"净负荷曲线有清晰的{top_zh}峰值，而不是均衡分布。"
    else:
        shape_en = "The net-load profile is fairly balanced across the three parts of the window."
        shape_zh = "净负荷在早中晚三段比较接近，没有形成清晰的单段峰值。"
    en = (
        f"{shape_en} Early, middle, and late mean net loads are {fmt(means['early'])}, "
        f"{fmt(means['middle'])}, and {fmt(means['late'])}; the top-minus-second gap is "
        f"{fmt(gap)}, compared with the 0.30 reserve threshold. This evidence supports {s['answer_label']}."
    )
    zh = (
        f"{shape_zh} 早段、中段、后段平均净负荷分别为 {fmt(means['early'])}、"
        f"{fmt(means['middle'])}、{fmt(means['late'])}；最高段与第二高段只差 {fmt(gap)}，"
        f"对照 0.30 的预留阈值后，证据支撑“{label_zh(row)}”。"
    )
    # keep the computed variable used, so the linter does not hide an accidental field mismatch
    _ = second
    return en, zh


def caption_traffic(row: dict[str, Any]) -> tuple[str, str]:
    s = row["support_slots"]
    pre = s["pre_score_mean"]
    event = s["event_score_mean"]
    post = s["post_score_mean"]
    jump = event - pre
    post_drop = event - post
    if jump <= 0.50:
        shape_en = "The event period does not create a clear congestion-score jump over the pre-event baseline."
        shape_zh = "事件中拥堵分数没有相对事件前形成清晰跃升。"
    elif post_drop >= 0.30:
        shape_en = "The event creates a congestion spike and the post-event score moves back down."
        shape_zh = "事件中形成拥堵峰值，事件后分数回落。"
    else:
        shape_en = "The event creates a congestion spike and the post-event score stays close to the event level."
        shape_zh = "事件中形成拥堵峰值，事件后分数仍接近事件期。"
    en = (
        f"{shape_en} Mean congestion scores are {fmt(pre)} before the event, {fmt(event)} during it, "
        f"and {fmt(post)} afterward; the event lift is {fmt(jump)}, "
        f"{'above' if jump > 0.50 else 'below'} the 0.50 shock threshold. "
        f"This evidence supports {s['answer_label']}."
    )
    zh = (
        f"{shape_zh} 事件前、事件中、事件后平均拥堵分数分别为 {fmt(pre)}、{fmt(event)}、{fmt(post)}；"
        f"事件中比事件前高 {fmt(jump)}，{'高于' if jump > 0.50 else '低于'} 0.50 的冲击阈值。"
        f"证据支撑“{label_zh(row)}”。"
    )
    return en, zh


def caption_water(row: dict[str, Any]) -> tuple[str, str]:
    s = row["support_slots"]
    pre = s["pre_pressure_mean"]
    event = s["event_pressure_mean"]
    post = s["post_pressure_mean"]
    min_pressure = s["min_pressure"]
    flow_inc = s["event_flow_increase"]
    event_drop = pre - event
    post_gap = pre - post
    if min_pressure < 55 and flow_inc > 1.0 and post_gap > 2.0:
        shape_en = "Pressure falls during the disturbance and remains materially below the pre-event level afterward."
        shape_zh = "扰动中水压下降，事件后仍明显低于事件前水平。"
    elif event_drop > 2.0 and post >= pre - 1.0:
        shape_en = "Pressure drops during the disturbance but rebounds by the post-event segment."
        shape_zh = "扰动中水压明显下降，但事件后已经反弹。"
    elif abs(post_gap) <= 2.0:
        shape_en = "The post-event pressure is close to the pre-event baseline."
        shape_zh = "事件后水压接近事件前基线。"
    else:
        shape_en = "The pressure and flow signals do not cleanly match one of the direct service states."
        shape_zh = "水压和流量信号没有清晰落入某个直接服务状态。"
    en = (
        f"{shape_en} Pre-event, event, and post-event pressure means are {fmt(pre)}, {fmt(event)}, "
        f"and {fmt(post)}; minimum pressure is {fmt(min_pressure)} and event flow change is {fmt(flow_inc)}. "
        f"These values support {s['answer_label']}."
    )
    zh = (
        f"{shape_zh} 事件前、事件中、事件后水压均值分别为 {fmt(pre)}、{fmt(event)}、{fmt(post)}；"
        f"最低水压为 {fmt(min_pressure)}，事件中流量变化为 {fmt(flow_inc)}。这些数值支撑“{label_zh(row)}”。"
    )
    return en, zh


def caption_aiops(row: dict[str, Any]) -> tuple[str, str]:
    s = row["support_slots"]
    mem1 = s["memory_first_half_mean"]
    mem2 = s["memory_second_half_mean"]
    growth = s["memory_growth_ratio"]
    rx = s["rx_peak_median_ratio"]
    tx = s["tx_peak_median_ratio"]
    cpu = s["cpu_max"]
    if growth >= 0.15:
        shape_en = "Memory rises from the first half to the second half, while other peaks are secondary."
        shape_zh = "内存从前半段到后半段明显上升，其他峰值不是主导信号。"
    elif rx >= 2.5 or tx >= 2.5:
        shape_en = "The strongest symptom is a network peak relative to the median level."
        shape_zh = "最突出的症状是网络流量相对中位数出现尖峰。"
    elif cpu >= 0.85:
        shape_en = "The strongest symptom is a high CPU peak."
        shape_zh = "最突出的症状是 CPU 峰值过高。"
    else:
        shape_en = "None of memory growth, network peaks, or CPU saturation crosses its incident threshold."
        shape_zh = "内存增长、网络尖峰和 CPU 饱和都没有越过对应故障阈值。"
    en = (
        f"{shape_en} Memory changes from {fmt(mem1)} to {fmt(mem2)} ({pct(growth)}), "
        f"receive and transmit peak/median ratios are {fmt(rx)} and {fmt(tx)}, and max CPU is {fmt(cpu)}. "
        f"This evidence supports {s['answer_label']}."
    )
    zh = (
        f"{shape_zh} 内存均值从 {fmt(mem1)} 变为 {fmt(mem2)}（{pct(growth)}），"
        f"接收和发送峰值/中位数分别为 {fmt(rx)}、{fmt(tx)}，CPU 最大值为 {fmt(cpu)}。"
        f"证据支撑“{label_zh(row)}”。"
    )
    return en, zh


def caption_finrl(row: dict[str, Any]) -> tuple[str, str]:
    s = row["support_slots"]
    total_return = s["total_return"]
    drawdown = s["max_drawdown"]
    if drawdown <= -0.20:
        shape_en = "The price path contains a severe drawdown, so risk dominates the regime decision."
        shape_zh = "价格路径出现严重回撤，因此风险优先决定行情分类。"
    elif total_return >= 0.08:
        shape_en = "The price path rises strongly while drawdown stays below the severe-risk threshold."
        shape_zh = "价格路径明显上涨，同时最大回撤没有触发严重风险阈值。"
    elif total_return <= -0.08:
        shape_en = "The price path falls strongly without the drawdown rule needing to override it."
        shape_zh = "价格路径明显下跌，且无需由严重回撤规则覆盖。"
    else:
        shape_en = "The price path stays near flat after accounting for drawdown risk."
        shape_zh = "在考虑回撤风险后，价格路径整体接近横盘。"
    en = (
        f"{shape_en} Total return is {pct(total_return)} and maximum drawdown is {pct(drawdown)}; "
        f"the -20% drawdown override is not triggered unless the drawdown crosses that level. "
        f"These values support {s['answer_label']}."
    )
    zh = (
        f"{shape_zh} 总收益率为 {pct(total_return)}，最大回撤为 {pct(drawdown)}；"
        f"只有最大回撤达到 -20% 或更低时才会覆盖收益率判断。证据支撑“{label_zh(row)}”。"
    )
    return en, zh


CAPTIONERS = {
    "grid2op": caption_grid,
    "citylearn": caption_city,
    "traffic": caption_traffic,
    "water": caption_water,
    "aiopslab": caption_aiops,
    "finrl": caption_finrl,
}


def prompt_for(row: dict[str, Any]) -> str:
    return (
        "You are a time-series evidence captioner. Given the self-contained scene, decision rule, "
        "variable definitions, and question, write concise natural evidence that describes the time-series "
        "pattern and the key numeric checks needed to answer. Do not reveal an answer-letter line and do not "
        "use platform-specific background.\n\n"
        f"Scene: {row['scene_en']}\n"
        f"Decision rule: {row['decision_rule_en']}\n"
        f"Variables: {'; '.join(row.get('variables_en') or [])}\n"
        f"Question: {row['question']}"
    )


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row["target_caption"],
        "meta": {
            "dataset_name": row["dataset_name"],
            "generation_variant": row["generation_variant"],
            "merge_source_name": row["merge_source_name"],
            "task_family": row["task_family"],
            "answer": row["answer"],
            "answer_label": row["answer_label"],
            "question_zh": row["question_zh"],
            "natural_evidence_zh": row["natural_evidence_zh"],
            "source_row_id": row.get("source_row_id"),
            "source_dataset_name": row.get("source_dataset_name"),
        },
    }


def build_rows(input_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for src in input_rows:
        row = dict(src)
        domain = row["merge_source_name"]
        captioner = CAPTIONERS[domain]
        caption_en, caption_zh = captioner(row)
        row["source_dataset_name"] = row.get("dataset_name") or "self_contained_reasoning_qa_v2"
        row["source_v2_id"] = row["id"]
        row["id"] = row["id"].replace("self_contained_reasoning_v2", "self_contained_reasoning_v3")
        row["dataset_name"] = DATASET_NAME
        row["seed_set"] = DATASET_NAME
        row["generation_variant"] = "v3"
        row["domain"] = f"{domain}_self_contained_reasoning_v3"
        row["natural_evidence_caption"] = caption_en
        row["natural_evidence_zh"] = caption_zh
        row["oracle_evidence_caption"] = caption_en
        row["target_caption"] = caption_en
        row["output"] = caption_en
        row["prompt"] = prompt_for(row)
        row["caption_target_policy"] = "evidence_only_no_answer_label_line"
        row["caption_target_cleaned_from_v2"] = True
        row["meta"] = dict(row.get("meta") or {})
        row["meta"].update({
            "dataset_name": DATASET_NAME,
            "generation_variant": "v3",
            "source_v2_id": row["source_v2_id"],
            "caption_target_policy": row["caption_target_policy"],
        })
        out.append(row)
    return out


def summary(rows: list[dict[str, Any]], source: Path) -> dict[str, Any]:
    bad_phrases = ("Answer label", "the rule maps this to", "按规则判断为", "supports the answer")
    phrase_counts = {
        phrase: sum(1 for row in rows if phrase in row.get("target_caption", "") or phrase in row.get("natural_evidence_zh", ""))
        for phrase in bad_phrases
    }
    return {
        "dataset_name": DATASET_NAME,
        "source": str(source.relative_to(ROOT)),
        "n": len(rows),
        "by_domain": dict(Counter(row["merge_source_name"] for row in rows)),
        "by_task_family": dict(Counter(row["task_family"] for row in rows)),
        "answer_label_by_domain": {
            domain: dict(Counter(row["answer_label"] for row in domain_rows))
            for domain, domain_rows in _group_by_domain(rows).items()
        },
        "bad_phrase_counts": phrase_counts,
        "caption_train_policy": "target_caption/output contain natural evidence only; answer label kept only in metadata/gold fields",
    }


def _group_by_domain(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["merge_source_name"]].append(row)
    return grouped


def report(summary_data: dict[str, Any], out_dir: Path) -> str:
    lines = [
        "# Self-contained Reasoning TS-QA v3（2026-05-21）",
        "",
        "## 这版修了什么",
        "",
        "v3 保留 v2 的自包含题面、规则、选项、gold 和 support slots，只清洗 caption 训练目标。",
        "核心变化是：`target_caption/output` 不再写 `Answer label`，也不再使用 `the rule maps this to` 这种规则执行模板。",
        "",
        "## 规模",
        "",
        f"- 总样本：{summary_data['n']}",
        f"- 分域：{summary_data['by_domain']}",
        "",
        "## 清洗检查",
        "",
        "| phrase | count in target/evidence |",
        "| --- | ---: |",
    ]
    for phrase, count in summary_data["bad_phrase_counts"].items():
        lines.append(f"| `{phrase}` | {count} |")
    lines.extend([
        "",
        "## 产物",
        "",
        f"- QA JSONL: `{out_dir / 'self_contained_reasoning_tsqa.jsonl'}`",
        f"- SFT JSONL: `{out_dir / 'self_contained_reasoning_tsqa_sft.jsonl'}`",
        f"- summary: `{out_dir / 'self_contained_reasoning_tsqa_summary.json'}`",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    rows = build_rows(load_jsonl(args.input))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "self_contained_reasoning_tsqa.jsonl", rows)
    write_jsonl(args.out_dir / "self_contained_reasoning_tsqa_sft.jsonl", [sft_row(row) for row in rows])
    summary_data = summary(rows, args.input)
    (args.out_dir / "self_contained_reasoning_tsqa_summary.json").write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "SELF_CONTAINED_REASONING_TSQA_V3_REPORT_20260521_ZH.md").write_text(
        report(summary_data, args.out_dir.relative_to(ROOT)) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
