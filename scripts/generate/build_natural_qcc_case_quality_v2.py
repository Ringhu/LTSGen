#!/usr/bin/env python3
"""Repair the 12 Natural-QCC case-study examples for reader-facing quality."""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = (
    ROOT
    / ".research/general-qcc-captioner-20260515/natural_qcc_case_quality_v1_20260521/"
    / "natural_qcc_case_quality_v1.jsonl"
)
DEFAULT_OUT_DIR = ROOT / ".research/general-qcc-captioner-20260515/natural_qcc_case_quality_v2_20260521"
DATASET_NAME = "natural_qcc_case_quality_v2"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def f(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def pct(value: float, digits: int = 2) -> str:
    return f"{100.0 * value:.{digits}f}%"


def rewrite(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    task = out["task_family"]
    s = out.get("support_slots") or {}
    out["id"] = out["id"].replace("natural_qcc_quality_v1", "natural_qcc_quality_v2")
    out["dataset_name"] = DATASET_NAME
    out["seed_set"] = DATASET_NAME
    out["source_v1_id"] = row["id"]
    out["quality_revision"] = {
        "version": "v2",
        "goals": [
            "remove simulator names from reader-facing scene",
            "replace vague variable definitions with domain meanings",
            "make English and Chinese evidence captions describe the same facts",
            "remove answer-support template phrases from caption targets",
        ],
    }

    if task == "grid_counterfactual_overload_exposure":
        out.update({
            "scene_zh": "一名电网调度员在复盘计划断线。图中正常基线表示同一负荷条件下不执行断线的运行，断线轨迹表示执行计划断线后的运行；x0 是断线轨迹减正常基线的线路压力差，x2 是断线后的最大线路负载压力。",
            "rule_zh": "最大线路负载压力超过 1.0 表示进入过载风险区。过载暴露是窗口内高于 1.0 的时间比例。比较断线轨迹和正常基线时，如果断线后的过载暴露明显更高，就说明计划断线提高了过载风险。",
            "question_zh": "和正常基线相比，这次计划断线会怎样改变事件后窗口的过载风险？",
            "caption_en": (
                f"The matched normal baseline stays below the overload threshold for this post-event window, "
                f"while the planned-outage trace is above 1.0 for most of it. Overload exposure changes from "
                f"{f(s['factual_overload_exposure'])} in the baseline to {f(s['intervention_overload_exposure'])} after the outage, "
                "so the relevant time-series evidence points to higher overload risk."
            ),
            "caption_zh": (
                f"同一负荷条件下的正常基线在事件后窗口没有进入过载区，而计划断线后的最大线路负载压力大部分时间超过 1.0。"
                f"过载暴露从基线的 {f(s['factual_overload_exposure'])} 变为断线后的 {f(s['intervention_overload_exposure'])}，"
                "因此这段时序证据指向过载风险升高。"
            ),
        })
    elif task == "grid_domain_stress_context":
        out.update({
            "scene_zh": "一名电网调度员在查看运行窗口。x0 是最大线路负载率，数值越接近或超过 1.0，线路压力越高；x1 是总需求；x2 是备用裕度指标，数值越低表示调度余量越紧。",
            "rule_zh": "从整段窗口判断电网压力时，先看 x0 的整体水平，再看是否长时间超过 1.0。均值接近 0.9 且只有短暂峰值超过 1.0，更像中等压力；若长时间高于 1.0，则更接近高压力运行。",
            "caption_en": (
                f"Maximum line-loading stress is elevated but not sustained at overload level: mean x0 is about {f(s['x0_mean'])}, "
                f"and the peak is about {f(s['x0_peak'])}. The series has a short excursion above 1.0 rather than a long high-stress plateau, "
                "which matches a medium-stress operating state."
            ),
            "caption_zh": (
                f"最大线路负载率整体偏高但没有长时间处在过载区：x0 均值约 {f(s['x0_mean'])}，峰值约 {f(s['x0_peak'])}。"
                "曲线只是短暂超过 1.0，而不是形成持续高压平台，因此更符合中等压力运行。"
            ),
        })
    elif task == "city_domain_demand_context":
        out.update({
            "scene_zh": "建筑能耗控制器在查看建筑负荷窗口。x0 是建筑总用电负荷；x1 是室外温度，代表天气带来的用能压力；x2 是本地太阳能发电强度，可抵消部分电网供电需求。",
            "rule_zh": "供能预留看总负荷的整体水平和峰值。若 x0 长时间偏高，且峰值超过约 15，控制器应按高需求压力准备更多电网供电或储能。",
            "caption_en": (
                f"Building load stays high across the window rather than appearing as a single isolated spike. "
                f"Mean x0 is about {f(s['x0_mean'])}, and the peak reaches {f(s['x0_peak'])}, above the high-demand reference level. "
                "This pattern points to a high demand-pressure planning window."
            ),
            "caption_zh": (
                f"建筑总负荷不是单个孤立尖峰，而是在窗口内整体维持较高水平。x0 平均约 {f(s['x0_mean'])}，峰值达到 {f(s['x0_peak'])}，"
                "超过高需求参考水平，因此这段窗口应按高需求压力做供能预留。"
            ),
        })
    elif task == "city_window_total_load":
        out.update({
            "scene_zh": "建筑控制器把同一负荷窗口分成前半段和后半段来安排供能。x0 是总用电负荷；平均负荷更高的一段更需要提前预留电网供电或储能。",
            "caption_en": (
                f"The load profile is front-heavy: average x0 is about {f(s['first_mean'])} in the first half and {f(s['second_mean'])} in the second half. "
                "Because the earlier half carries the larger demand, the reserve plan should prioritize the first half."
            ),
            "caption_zh": (
                f"这段负荷曲线前半段更重：前半段平均 x0 约 {f(s['first_mean'])}，后半段约 {f(s['second_mean'])}。"
                "由于更大的用电需求集中在前半段，供能预留应优先覆盖前半段。"
            ),
        })
    elif task == "traffic_domain_congestion_context":
        out.update({
            "scene_zh": "交通工程师在查看路网监测窗口。x0 是平均车速，越低表示车辆移动越慢；x1 是排队长度，越高表示等待车辆越多；x2 是车道占有率，越高表示道路被车辆占用越充分。",
            "rule_zh": "交通状态同时看车速和队列。低车速配合长队列说明拥堵较重；如果平均车速约 30 且最大队列接近 9，应按严重拥堵处理。",
            "caption_en": (
                f"The road segment is both slow and queued: mean speed is about {f(s['mean_speed'])}, "
                f"while maximum queue length reaches {f(s['max_queue'])}. Low speed together with a long queue is the time-series signature of severe congestion here."
            ),
            "caption_zh": (
                f"这段路网同时表现出低速和长队列：平均车速约 {f(s['mean_speed'])}，最大队列达到 {f(s['max_queue'])}。"
                "低车速与长队列同时出现，是这里严重拥堵的主要时序证据。"
            ),
        })
    elif task == "traffic_event_recovery_context":
        out.update({
            "scene_zh": "交通工程师在复盘一次事件前后窗口。x0 是平均车速；如果事件后车速回到事件前水平，才算明显恢复，否则说明拥堵影响仍在延续。",
            "caption_en": (
                f"Speed drops sharply from about {f(s['pre_mean'])} before the event to {f(s['event_mean'])} during the event, "
                f"then remains low at about {f(s['post_mean'])} afterward. The post-event segment stays near the event-period speed, so the congestion has not recovered."
            ),
            "caption_zh": (
                f"车速从事件前约 {f(s['pre_mean'])} 明显降到事件中的 {f(s['event_mean'])}，事件后也只有 {f(s['post_mean'])} 左右。"
                "事件后仍接近事件期低速，而不是回到事件前水平，因此拥堵仍在持续。"
            ),
        })
    elif task == "water_domain_resilience_context":
        out.update({
            "scene_zh": "供水网络运维人员在查看服务窗口。x0 是服务水压，越低表示用户侧压力越差；x1 是管道流量；x2 是水箱蓄水量，用来判断系统是否还有缓冲。",
            "rule_zh": "供水服务状态不能只看平均水压，也要看最低水压和流量。若平均水压看似正常，但最低水压明显跌落，并且窗口内仍有持续流量，更像漏损压力状态；若水压始终稳定且没有异常低点，才更像稳定服务。",
            "caption_en": (
                f"Pressure is not uniformly stable: mean pressure is about {f(s['mean_pressure'])}, but the minimum falls to {f(s['min_pressure'])}, "
                f"with mean flow about {f(s['mean_flow'])}. The combination of a clear pressure low point and continuing flow points to a leak-pressure state."
            ),
            "caption_zh": (
                f"这段水压并不是均匀稳定：平均水压约 {f(s['mean_pressure'])}，但最低水压降到 {f(s['min_pressure'])}，平均流量约 {f(s['mean_flow'])}。"
                "明显低压点和持续流量同时出现，因此更像漏损压力状态。"
            ),
        })
    elif task == "water_leak_counterfactual_pressure":
        out.update({
            "scene_zh": "供水运维人员在比较两个匹配窗口：一个是发生漏损的窗口，另一个是在相同需求条件下没有漏损的基线窗口。x0 是服务水压，判断重点是平均水压是否被漏损明显改变。",
            "rule_zh": "如果漏损窗口和无漏损基线的平均水压几乎相同，就不能说漏损显著改变了服务压力；只有平均水压差异达到可观幅度时，才判断为漏损使水压升高或降低。",
            "options_zh": ["A. 漏损使水压降低", "B. 漏损使水压升高", "C. 需要现场复核", "D. 水压没有实质变化"],
            "caption_en": (
                f"The leak window and the matched no-leak baseline have almost the same mean pressure: "
                f"{f(s['factual_mean'])} versus {f(s['counterfactual_mean'])}, with a difference near {f(s['delta'])}. "
                "The counterfactual comparison points to no material pressure change."
            ),
            "caption_zh": (
                f"漏损窗口和匹配的无漏损基线平均水压几乎相同：漏损窗口约 {f(s['factual_mean'])}，无漏损基线约 {f(s['counterfactual_mean'])}，"
                f"差值约 {f(s['delta'])}。这个反事实对照说明平均服务水压没有实质变化。"
            ),
        })
    elif task == "aiops_official_cross_signal_relation":
        out.update({
            "scene_zh": "SRE 在查看在线服务的遥测窗口。x0 是 CPU 负载，x1 是内存工作集，x2 是网络接收速率，x3 是网络发送速率；如果接收和发送同步变化，通常说明主要耦合来自网络通信侧。",
            "rule_zh": "排障时比较两组关系：CPU-内存关系代表计算/资源压力，网络接收-发送关系代表通信模式。若网络收发相关远高于 CPU-内存相关，应优先认为网络侧耦合更明显。",
            "caption_en": (
                f"Network receive and transmit move almost in lockstep, with correlation about {f(s['corr_net_rx_tx'])}. "
                f"CPU-memory correlation is only about {f(s['corr_cpu_memory'])}. The much stronger rx-tx relationship identifies network-side coupling."
            ),
            "caption_zh": (
                f"网络接收 x2 和发送 x3 几乎同步变化，相关约 {f(s['corr_net_rx_tx'])}；CPU x0 与内存 x1 的相关只有约 {f(s['corr_cpu_memory'])}。"
                "网络收发关系明显更强，因此主要耦合来自网络侧。"
            ),
        })
    elif task == "aiops_official_memory_extrema":
        out.update({
            "scene_zh": "SRE 在检查在线服务的内存工作集。x1 是服务实际占用的内存量；窗口从左到右分为早段、中段和后段，问题只关心峰值出现在哪一段。",
            "caption_en": (
                f"Memory working set x1 reaches its maximum at the beginning of the window, with a peak near {f(s['extrema_value'])}. "
                "The middle and late portions stay below that early peak, so the peak location is the early segment."
            ),
            "caption_zh": (
                f"内存工作集 x1 的最高点出现在窗口开头的早段，峰值约 {f(s['extrema_value'])}。"
                "中段和后段都没有超过这个早段峰值，因此峰值位置是早段。"
            ),
        })
    elif task == "fin_domain_market_regime":
        out.update({
            "scene_zh": "市场分析师在复盘 MSFT 的历史价格窗口。x0 是 MSFT 价格，x1 是同步市场基准价格，用来提供大盘背景，x2 是成交量；问题重点是 MSFT 自身收益方向和波动。",
            "rule_zh": "行情状态同时看总收益和收益波动。总收益接近零说明方向不明显；若收益波动较高，则更像高波动横盘，而不是低波动横盘。",
            "caption_en": (
                f"MSFT has little net direction in this window: total return is about {pct(s['total_return'])}. "
                f"At the same time, return volatility is about {f(s['return_std'], 3)}, so the series is not quiet. "
                "Near-flat direction plus visible volatility matches a volatile sideways regime."
            ),
            "caption_zh": (
                f"MSFT 在这个窗口里方向性很弱，总收益约 {pct(s['total_return'])}；但收益波动约 {f(s['return_std'], 3)}，并不平静。"
                "接近横盘的方向加上较明显波动，更符合高波动横盘。"
            ),
        })
    elif task == "fin_drawdown_price":
        out.update({
            "scene_zh": "市场分析师在查看 MSFT 的价格风险。x0 是目标资产价格；最大回撤表示价格从阶段高点跌到后续低点的最大比例。",
            "caption_en": (
                f"MSFT falls from a local high to a later low, producing a maximum drawdown of about {pct(abs(s['max_drawdown']))}. "
                "That drawdown is above the tiny-dip range but below the medium and severe thresholds, so the risk level is mild drawdown."
            ),
            "caption_zh": (
                f"MSFT 从阶段高点回落到后续低点，最大回撤约 {pct(abs(s['max_drawdown']))}。"
                "这个幅度超过很小回撤，但低于中等和严重回撤阈值，因此属于轻微回撤。"
            ),
        })
    else:
        raise ValueError(f"unhandled task {task}")

    out["target_caption"] = out["caption_en"]
    out["output"] = out["caption_en"]
    out["prompt"] = (
        "You are a question-conditioned time-series evidence captioner. Write a concise evidence caption "
        "that first describes the relevant time-series pattern and then explains the decision evidence. "
        "Do not output an option letter, JSON, or an answer-label-only sentence.\n\n"
        f"Scene: {out['scene_zh']}\n"
        f"Rule: {out['rule_zh']}\n"
        f"Question: {out['question_zh']}\n"
        f"Options: {'; '.join(out['options_zh'])}"
    )
    return out


def copy_figure(row: dict[str, Any], out_dir: Path) -> None:
    src = ROOT / row["figure_path"]
    name = src.name.replace("natural_qcc_quality_v1", "natural_qcc_quality_v2")
    dst = out_dir / "figures" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    row["figure_path"] = str(dst.relative_to(ROOT))


def sft_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "values": row["values"],
        "prompt": row["prompt"],
        "output": row["output"],
        "target_caption": row["target_caption"],
        "meta": {
            "dataset_name": DATASET_NAME,
            "domain": row["merge_source_name"],
            "task_family": row["task_family"],
            "answer": row["answer"],
            "answer_zh": row["answer_zh"],
            "source_v1_id": row["source_v1_id"],
        },
    }


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bad_terms = ("Grid2Op", "CityLearn", "SUMO", "WNTR", "AIOpsLab", "上下文", "辅助上下文", "背景价格信号")
    bad_caption = ("supports the answer", "therefore supports", "Answer label")
    issues = []
    for row in rows:
        reader_text = "\n".join([row.get("scene_zh", ""), row.get("rule_zh", ""), row.get("question_zh", ""), row.get("caption_zh", "")])
        for term in bad_terms:
            if term in reader_text:
                issues.append({"id": row["id"], "issue": "reader_bad_term", "term": term})
        for term in bad_caption:
            if term.lower() in row.get("caption_en", "").lower():
                issues.append({"id": row["id"], "issue": "caption_template_phrase", "term": term})
        if not (ROOT / row["figure_path"]).exists():
            issues.append({"id": row["id"], "issue": "missing_figure"})
    return {
        "pass": not issues,
        "n": len(rows),
        "issue_count": len(issues),
        "issues": issues,
        "by_domain": dict(Counter(row["merge_source_name"] for row in rows)),
    }


def report(rows: list[dict[str, Any]], audit_data: dict[str, Any], out_dir: Path) -> str:
    lines = [
        "# Natural-QCC Case Quality v2（2026-05-21）",
        "",
        "## 这版修了什么",
        "",
        "v2 专门回应上一轮 case 的可读性问题：去掉 simulator 名称，补清变量含义，说明对照/基线，删除英文 caption 的 answer-support 模板句，并让中英文 caption 聚焦同一组证据。",
        "",
        f"- case 数量：{len(rows)}",
        f"- 分域：{audit_data['by_domain']}",
        f"- audit pass：{audit_data['pass']}",
        "",
        "## Case Studies",
        "",
    ]
    for idx, row in enumerate(rows, start=1):
        fig = Path(row["figure_path"]).name
        lines.extend([
            f"### {idx}. `{row['merge_source_name']}` / `{row['task_family']}`",
            "",
            f"![](figures/{fig})",
            "",
            f"**场景：** {row['scene_zh']}",
            "",
            f"**前置规则：** {row['rule_zh']}",
            "",
            f"**问题：** {row['question_zh']}",
            "",
            "**选项：**",
            "",
        ])
        lines.extend(f"- {option}" for option in row["options_zh"])
        lines.extend([
            "",
            f"**答案：** `{row['answer']}` / {row['answer_zh']}",
            "",
            f"**中文 caption：** {row['caption_zh']}",
            "",
            f"**English target caption：** {row['caption_en']}",
            "",
            f"**Audit source row：** `{row['source_row_id']}`",
            "",
        ])
    lines.extend([
        "## 产物",
        "",
        f"- case JSONL: `{out_dir / 'natural_qcc_case_quality_v2.jsonl'}`",
        f"- SFT JSONL: `{out_dir / 'natural_qcc_case_quality_v2_sft.jsonl'}`",
        f"- audit JSON: `{out_dir / 'natural_qcc_case_quality_v2_audit.json'}`",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out_dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    rows = [rewrite(row) for row in load_jsonl(args.input)]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        copy_figure(row, args.out_dir)
    audit_data = audit(rows)
    write_jsonl(args.out_dir / "natural_qcc_case_quality_v2.jsonl", rows)
    write_jsonl(args.out_dir / "natural_qcc_case_quality_v2_sft.jsonl", [sft_row(row) for row in rows])
    (args.out_dir / "natural_qcc_case_quality_v2_audit.json").write_text(
        json.dumps(audit_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "NATURAL_QCC_CASE_QUALITY_V2_REPORT_20260521_ZH.md").write_text(
        report(rows, audit_data, args.out_dir.relative_to(ROOT)) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit_data, ensure_ascii=False, indent=2))
    if not audit_data["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
