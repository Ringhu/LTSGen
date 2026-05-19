#!/usr/bin/env python3
"""Build a small natural-language TS-QA case pilot for review.

The pilot keeps gold answers tied to deterministic support slots. It rewrites
only the presentation layer: scene, question, options, and bilingual report.
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
CASE_ROOT = ROOT / ".research/general-qcc-captioner-20260515/natural_qa_pilot_20260519"
RAW = (
    ROOT
    / ".research/general-qcc-captioner-20260515/multisim_qcc_v5_aiops_v3/"
    / "case_study_simulator_data_20260518/raw_samples/balanced_eval_per_source8.jsonl"
)
OUT_JSON = CASE_ROOT / "natural_tsqa_case_pilot.json"
OUT_MD = CASE_ROOT / "NATURAL_TSQA_CASE_PILOT_20260519_ZH.md"
FIG_DIR = CASE_ROOT / "figures"

for font_path in (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
):
    if Path(font_path).exists():
        font_manager.fontManager.addfont(font_path)
        plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        break


PILOT_CASES = [
    {
        "case_key": "grid2op_counterfactual_stress",
        "source": "grid2op",
        "row_id": "multisim_qcc_v5_aiops_v3::grid2op::grid2op_broad_cf::h2048_c-1_t512_line1::post769_1025::grid_counterfactual_peak_stress",
        "title_en": "Grid2Op line-disconnection stress check",
        "title_zh": "Grid2Op 断线后的线路压力检查",
        "variables_en": [
            "x0: intervention-minus-factual maximum line-loading stress",
            "x1: demand-context difference",
            "x2: generation-margin-context difference",
        ],
        "variables_zh": [
            "x0：干预轨迹减事实轨迹后的最大线路负载压力差",
            "x1：需求上下文差异",
            "x2：发电裕度上下文差异",
        ],
        "scene_en": (
            "A Grid2Op operator is reviewing a 256-step local window after line 1 was disconnected. "
            "The disconnection happened earlier at global step 512; this plot starts at global step 769, "
            "so every point shown is already post-event. In this counterfactual plot, positive x0 means "
            "the disconnection makes maximum line-loading stress higher than the original factual run."
        ),
        "scene_zh": (
            "一名 Grid2Op 电网调度员正在查看 1 号线路断开后的 256 步局部窗口。断线发生在更早的全局第 512 步；"
            "这张图从全局第 769 步开始，因此图中所有点都已经是事件后片段。在这张反事实图里，x0 为正表示"
            "断线让最大线路负载压力高于原始事实运行。"
        ),
        "question_en": "In this post-event window, what is the main effect of disconnecting line 1 on maximum line-loading stress?",
        "question_zh": "在这个事件后窗口里，断开 1 号线路对最大线路负载压力的主要影响是什么？",
        "options": [
            {"letter": "A", "en": "It mainly lowers the stress.", "zh": "主要降低线路压力。"},
            {"letter": "B", "en": "It causes no material stress change.", "zh": "没有造成实质压力变化。"},
            {"letter": "C", "en": "It raises the stress with a clear positive deviation.", "zh": "产生清晰的正向偏差，使线路压力升高。"},
            {"letter": "D", "en": "The plotted window is not enough to tell.", "zh": "仅凭这个窗口无法判断。"},
        ],
        "gold_answer": "C",
        "gold_answer_zh": "产生清晰的正向偏差，使线路压力升高。",
        "evidence_en": "x0 stays positive throughout the post-event segment, with post-event differences from about 0.37 to 0.56.",
        "evidence_zh": "事件后片段里 x0 始终为正，差值大约在 0.37 到 0.56 之间。",
        "design_note_zh": "把 global step 和局部窗口的关系放进场景说明，问题本身只问调度员关心的效果。",
    },
    {
        "case_key": "citylearn_energy_planning",
        "source": "citylearn",
        "row_id": "multisim_qcc_v5_aiops_v3::citylearn::citylearn_broad::citylearn_challenge_2022_phase_1_start6144_h2048_b5::w1664_1920::city_window_total_load",
        "title_en": "CityLearn building-load planning",
        "title_zh": "CityLearn 建筑负载调度判断",
        "variables_en": [
            "x0: total building electricity load",
            "x1: outdoor/weather context",
            "x2: solar or auxiliary context",
        ],
        "variables_zh": [
            "x0：建筑总用电负载",
            "x1：室外/天气上下文",
            "x2：太阳能或辅助上下文",
        ],
        "scene_en": (
            "A building energy controller uses x0 as the electricity demand signal. Higher average x0 "
            "means the controller should reserve more grid or battery supply for that part of the window."
        ),
        "scene_zh": "建筑能耗控制器把 x0 作为用电需求信号。x0 平均值越高，表示这一段需要预留更多电网或电池供给。",
        "question_en": "For this window, when should the controller plan for higher average electricity demand?",
        "question_zh": "在这个窗口里，控制器应该在哪一段为更高的平均用电需求做准备？",
        "options": [
            {"letter": "A", "en": "The second half of the window.", "zh": "窗口后半段。"},
            {"letter": "B", "en": "The first half of the window.", "zh": "窗口前半段。"},
            {"letter": "C", "en": "Both halves are about the same.", "zh": "前后两半差不多。"},
            {"letter": "D", "en": "The plot is not enough to determine this.", "zh": "仅凭图无法判断。"},
        ],
        "gold_answer": "B",
        "gold_answer_zh": "窗口前半段。",
        "evidence_en": "The first-half mean of x0 is 7.77, higher than the second-half mean of 6.65.",
        "evidence_zh": "x0 前半段均值为 7.77，高于后半段均值 6.65。",
        "design_note_zh": "从“比较均值”改成“建筑控制器做供能计划”的自然决策问题。",
    },
    {
        "case_key": "finrl_mrk_drawdown_risk",
        "source": "finrl_scaled",
        "row_id": "multisim_qcc_v5_aiops_v3::finrl_scaled::finrl_broad::MRK::w2043_2555::fin_drawdown_price",
        "title_en": "FinRL MRK drawdown-risk review",
        "title_zh": "FinRL MRK 回撤风险复盘",
        "variables_en": [
            "x0: MRK target close price",
            "x1: equal-weight market index",
            "x2: trading volume",
        ],
        "variables_zh": [
            "x0：MRK 目标收盘价",
            "x1：等权市场指数",
            "x2：交易量",
        ],
        "scene_en": (
            "A risk analyst is reviewing the MRK price window. In this setting, drawdown means the largest "
            "peak-to-trough percentage loss inside the window; a fall around one third of the price level is treated as severe."
        ),
        "scene_zh": "一名风险分析师正在复盘 MRK 的价格窗口。这里的回撤指窗口内从峰值到谷值的最大百分比损失；接近三分之一价格水平的下跌应视为严重回撤。",
        "question_en": "From a risk-management perspective, how should this MRK window be described?",
        "question_zh": "从风险管理角度看，这段 MRK 窗口应该如何描述？",
        "options": [
            {"letter": "A", "en": "Moderate drawdown.", "zh": "中等回撤。"},
            {"letter": "B", "en": "Mild drawdown.", "zh": "轻微回撤。"},
            {"letter": "C", "en": "Severe drawdown.", "zh": "严重回撤。"},
            {"letter": "D", "en": "Little drawdown.", "zh": "回撤很小。"},
        ],
        "gold_answer": "C",
        "gold_answer_zh": "严重回撤。",
        "evidence_en": "The maximum drawdown is about 36.65% during the 2023-02-14 to 2025-02-28 review window.",
        "evidence_zh": "在 2023-02-14 到 2025-02-28 的复盘窗口中，最大回撤约为 36.65%。",
        "design_note_zh": "明确股票是 MRK，不再写“ticker named in the question”；问题面向风险管理语境。",
    },
    {
        "case_key": "water_service_resilience",
        "source": "water",
        "row_id": "multisim_qcc_v5_aiops_v3::water::water_broad::water_scenario_015::water_domain_resilience_context",
        "title_en": "Water-network service-state check",
        "title_zh": "供水网络服务状态判断",
        "variables_en": [
            "x0: water pressure",
            "x1: pipe flow",
            "x2: tank storage",
        ],
        "variables_zh": [
            "x0：水压",
            "x1：管道流量",
            "x2：水箱蓄水量",
        ],
        "scene_en": (
            "A water-network operator is checking whether the service looks stressed. Low pressure would suggest service risk, "
            "while stable pressure with ordinary flow is consistent with normal operation."
        ),
        "scene_zh": "供水网络运维人员正在判断服务是否承压。低水压会提示供水风险；水压稳定且流量正常则更符合正常运行。",
        "question_en": "Which operational state best matches this water-network window?",
        "question_zh": "这个供水网络窗口最符合哪种运行状态？",
        "options": [
            {"letter": "A", "en": "Leak-stressed network.", "zh": "漏水压力下的网络。"},
            {"letter": "B", "en": "Low-pressure service risk.", "zh": "低水压服务风险。"},
            {"letter": "C", "en": "Unclear hydraulic state.", "zh": "水力状态不清楚。"},
            {"letter": "D", "en": "Stable water service.", "zh": "稳定供水服务。"},
        ],
        "gold_answer": "D",
        "gold_answer_zh": "稳定供水服务。",
        "evidence_en": "Mean pressure is 83.43, minimum pressure is 57.73, and mean flow is 10.71, matching a stable-service label.",
        "evidence_zh": "平均水压为 83.43，最低水压为 57.73，平均流量为 10.71，对应稳定供水服务标签。",
        "design_note_zh": "用水务运维状态来表达，而不是直接问某个统计量。",
    },
    {
        "case_key": "traffic_signal_queue_effect",
        "source": "traffic",
        "row_id": "multisim_qcc_v5_aiops_v3::traffic::traffic_broad::traffic_scenario_025::traffic_signal_counterfactual_queue",
        "title_en": "Traffic signal-policy queue comparison",
        "title_zh": "交通信号策略的队列影响比较",
        "variables_en": [
            "x0: mean traffic speed",
            "x1: queue length",
            "x2: occupancy or control context",
        ],
        "variables_zh": [
            "x0：平均车速",
            "x1：队列长度",
            "x2：占有率或控制上下文",
        ],
        "scene_en": (
            "A traffic engineer compares an adaptive signal policy against a matched fixed-signal baseline under the same demand window. "
            "For queue length, lower is better."
        ),
        "scene_zh": "交通工程师在相同需求窗口下比较自适应信号策略和匹配的固定信号基线。对队列长度来说，越低越好。",
        "question_en": "Did the adaptive signal policy improve queueing in this window?",
        "question_zh": "在这个窗口里，自适应信号策略是否改善了排队情况？",
        "options": [
            {"letter": "A", "en": "Yes, it lowered the mean queue.", "zh": "是，它降低了平均队列长度。"},
            {"letter": "B", "en": "The two policies have the same mean queue.", "zh": "两种策略的平均队列长度相同。"},
            {"letter": "C", "en": "The mean queue values are not enough to decide.", "zh": "给出的平均队列长度不足以判断。"},
            {"letter": "D", "en": "No, it raised the mean queue.", "zh": "没有，它提高了平均队列长度。"},
        ],
        "gold_answer": "D",
        "gold_answer_zh": "没有，它提高了平均队列长度。",
        "evidence_en": "The adaptive-signal mean queue is 2.91, higher than the matched fixed-signal baseline mean of 2.56.",
        "evidence_zh": "自适应信号下平均队列为 2.91，高于匹配固定信号基线的 2.56。",
        "design_note_zh": "把“factual vs baseline”改成交通工程师关心的策略是否改善排队。",
    },
    {
        "case_key": "aiops_memory_pressure",
        "source": "aiopslab_official_v3",
        "row_id": "multisim_qcc_v5_aiops_v3::aiopslab_official_v3::aiopslab_official::scale_pod_zero_seed0_user-service::case005::aiops_official_window_memory",
        "title_en": "AIOpsLab memory-pressure triage",
        "title_zh": "AIOpsLab 内存压力排查",
        "variables_en": [
            "x0: service CPU load",
            "x1: memory working set",
            "x2: network receive rate",
            "x3: network transmit rate",
        ],
        "variables_zh": [
            "x0：服务 CPU 负载",
            "x1：内存工作集",
            "x2：网络接收速率",
            "x3：网络发送速率",
        ],
        "scene_en": (
            "An SRE is triaging an AIOpsLab microservice incident window. The memory working set x1 is used as a memory-pressure signal; "
            "a higher second-half average means pressure is building rather than easing."
        ),
        "scene_zh": "一名 SRE 正在排查 AIOpsLab 微服务事故窗口。内存工作集 x1 用作内存压力信号；后半段平均值更高表示压力在累积，而不是缓解。",
        "question_en": "Does memory pressure ease or build up over this incident window?",
        "question_zh": "在这个事故窗口中，内存压力是在缓解还是在累积？",
        "options": [
            {"letter": "A", "en": "It is higher in the first half, so pressure eases later.", "zh": "前半段更高，因此后面压力缓解。"},
            {"letter": "B", "en": "It is higher in the second half, so pressure builds up.", "zh": "后半段更高，因此压力在累积。"},
            {"letter": "C", "en": "Both halves are about the same.", "zh": "前后两半差不多。"},
            {"letter": "D", "en": "The telemetry is not enough to tell.", "zh": "这些遥测不足以判断。"},
        ],
        "gold_answer": "B",
        "gold_answer_zh": "后半段更高，因此压力在累积。",
        "evidence_en": "The first-half mean of x1 is 12,725,660.44, while the second-half mean is 14,534,246.40.",
        "evidence_zh": "x1 前半段均值为 12,725,660.44，后半段均值为 14,534,246.40。",
        "design_note_zh": "把窗口均值比较转成 SRE 事故排查中的“压力是否累积”。",
    },
]


def load_rows() -> dict[str, dict]:
    rows = {}
    with RAW.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def sanitize(name: str) -> str:
    keep = []
    for ch in name:
        keep.append(ch if ch.isalnum() or ch in "-_" else "_")
    return "".join(keep)


def plot_case(case: dict, row: dict) -> str:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    raw = np.asarray(row.get("raw_compact_values") or row["values"], dtype=float)
    t = np.arange(raw.shape[0])
    height = 1.65 * raw.shape[1] + 1.2
    fig, axes = plt.subplots(raw.shape[1], 1, figsize=(8.2, height), sharex=True)
    if raw.shape[1] == 1:
        axes = [axes]

    for idx, ax in enumerate(axes):
        ax.plot(t, raw[:, idx], color=f"C{idx}", lw=1.25)
        en = case["variables_en"][idx] if idx < len(case["variables_en"]) else f"x{idx}"
        zh = case["variables_zh"][idx] if idx < len(case["variables_zh"]) else f"x{idx}"
        ax.set_ylabel(f"x{idx}")
        ax.set_title(f"{en}\n{zh}", fontsize=9, loc="left")
        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("local time step / 局部时间步")
    fig.suptitle(f"{case['title_en']} | {case['title_zh']}", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    path = FIG_DIR / f"{sanitize(case['case_key'])}.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return str(path.relative_to(CASE_ROOT))


def option_lines(case: dict) -> list[str]:
    return [f"- {opt['letter']}. {opt['en']} / {opt['zh']}" for opt in case["options"]]


def build_markdown(cases: list[dict]) -> str:
    sections = []
    for idx, case in enumerate(cases, start=1):
        slots = case["support_slots"]
        slot_str = ", ".join(f"`{k}={v}`" for k, v in slots.items())
        sections.append(
            "\n".join(
                [
                    f"## {idx}. {case['title_en']}（{case['title_zh']}）",
                    "",
                    f"![]({case['figure']})",
                    "",
                    f"**Domain/source:** `{case['source']}`  ",
                    f"**Task family:** `{case['task_family']}`  ",
                    f"**Row ID:** `{case['row_id']}`",
                    "",
                    f"**Scene EN:** {case['scene_en']}",
                    "",
                    f"**场景中文:** {case['scene_zh']}",
                    "",
                    f"**Question EN:** {case['question_en']}  ",
                    f"**问题中文:** {case['question_zh']}",
                    "",
                    "**Options / 选项:**",
                    "",
                    *option_lines(case),
                    "",
                    f"**Gold:** `{case['gold_answer']}` / {case['gold_answer_zh']}",
                    "",
                    f"**Evidence EN:** {case['evidence_en']}  ",
                    f"**证据中文:** {case['evidence_zh']}",
                    "",
                    f"**Support slots:** {slot_str}",
                    "",
                    f"**原始问题:** {case['original_question']}",
                    "",
                    f"**设计说明:** {case['design_note_zh']}",
                ]
            )
        )

    return dedent(
        """
        # Natural TS-QA Case Pilot（2026-05-19）

        目标：把 MultiSim/QCC case study 从“slot/verifier 拼接题”改成更像正常 QA 的自然语言问题，同时保持答案仍由 deterministic support slots 验证。这里先给 6 个小样本供人工审核；审核通过后再扩展到大规模造数据。

        设计原则：

        - 场景说明负责交代 domain、变量含义、时间轴和必要背景。
        - 问题本身只问一个自然决策，不暴露内部 row id、segment tag、verifier 实现细节。
        - 选项是普通读者能理解的短答案，不是 support slot 名称。
        - gold answer 不由 LLM 决定，只从原始 support slots 映射。
        - reviewer 可以评审自然性和可答性，但不能改 gold。

        """
    ).strip() + "\n\n" + "\n\n".join(sections) + "\n"


def main() -> None:
    rows = load_rows()
    CASE_ROOT.mkdir(parents=True, exist_ok=True)
    cases = []
    for template in PILOT_CASES:
        row = rows[template["row_id"]]
        case = dict(template)
        case["task_family"] = row["task_family"]
        case["original_question"] = row["question"]
        case["original_options"] = row["options"]
        case["original_answer"] = row["answer"]
        case["original_answer_label"] = row["answer_label"]
        case["support_slots"] = row.get("support_slots") or {}
        case["figure"] = plot_case(case, row)
        cases.append(case)

    OUT_JSON.write_text(json.dumps({"cases": cases}, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(cases), encoding="utf-8")
    print(OUT_JSON)
    print(OUT_MD)


if __name__ == "__main__":
    main()
