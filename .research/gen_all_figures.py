#!/usr/bin/env python3
"""Generate all SVG figures for the 2026-04-21 full experimental report."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

ROOT = Path("/home/cris/Research/LTSGEN-ext-a")
OUT = Path("/home/cris/Research/LTSGEN/.research/figures-20260421")
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "legend.fontsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "svg.fonttype": "none", "axes.spines.top": False, "axes.spines.right": False,
})

def J(p):
    return json.loads(Path(p).read_text())

def save(fig, name):
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", format="svg")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", format="png", dpi=150)
    plt.close(fig)
    print(f"  → {name}.svg + .png")


# ============================================================
# Fig 1: Vision paradigm 类比 schematic
# ============================================================
def fig1():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 5)
    # Vision row
    ax.text(0.2, 4.3, "Vision", fontsize=12, fontweight="bold", color="#444")
    for i, (x, label, color) in enumerate([
        (1.5, "Image-text\npaired data", "#90caf9"),
        (4.5, "CLIP\n(contrastive)", "#64b5f6"),
        (7.5, "MLLM\n(LLaVA, GPT-4V)", "#1976d2"),
        (10.5, "Multimodal\nreasoning", "#0d47a1"),
    ]):
        ax.add_patch(FancyBboxPatch((x-1, 3.5), 2, 1, boxstyle="round,pad=0.05", fc=color, ec="white"))
        ax.text(x, 4.0, label, ha="center", va="center", fontsize=9, color="white" if i>=2 else "#0d3a66")
    for x in [2.5, 5.5, 8.5]:
        ax.annotate("", xy=(x+1, 4), xytext=(x, 4), arrowprops=dict(arrowstyle="->", color="#666"))
    # TS row
    ax.text(0.2, 1.8, "Time Series\n(this work)", fontsize=12, fontweight="bold", color="#444")
    for i, (x, label, color) in enumerate([
        (1.5, "LTSGen\n(synthetic\ncaption data)", "#ffcc80"),
        (4.5, "OpenTSLM\n(TS captioner)", "#ff9800"),
        (7.5, "caption →\nfrozen LLM\n(this report)", "#fb8c00"),
        (10.5, "TS multimodal\nreasoning?", "#bf360c"),
    ]):
        ax.add_patch(FancyBboxPatch((x-1, 1.0), 2, 1.4, boxstyle="round,pad=0.05", fc=color, ec="white"))
        ax.text(x, 1.7, label, ha="center", va="center", fontsize=9, color="white" if i>=2 else "#5d2900")
    for x in [2.5, 5.5, 8.5]:
        ax.annotate("", xy=(x+1, 1.7), xytext=(x, 1.7), arrowprops=dict(arrowstyle="->", color="#666"))
    ax.text(6, 0.3, "Question: does the caption interface from step-3 actually help downstream LLM understand TS?",
            ha="center", fontsize=10, style="italic", color="#444")
    save(fig, "fig01_paradigm_analogy")

# ============================================================
# Fig 2: LTSGen pipeline schematic
# ============================================================
def fig2():
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 5)
    sources = ["FRED", "ETT", "Traffic", "Weather", "NAB", "UCR"]
    for i, s in enumerate(sources):
        ax.add_patch(FancyBboxPatch((0.2, 4.0-i*0.55), 1.5, 0.4, boxstyle="round,pad=0.02", fc="#e3f2fd", ec="#1976d2"))
        ax.text(0.95, 4.2-i*0.55, s, ha="center", va="center", fontsize=9)
    for stage, (x, label, sublabel, color) in enumerate([
        (3.5, "Sliding-window\nsampling", "len=128/256/512", "#90caf9"),
        (5.8, "GPT-5 caption\ngeneration", "12+ semantic slots\n(trend, vol, seasonality,\npeaks/valleys, ...)", "#42a5f5"),
        (8.5, "QC + dedupe", "55,550 train\n6,234 val\n1,171 test", "#1e88e5"),
        (10.8, "Mixed corpus\nfor SFT", "FC + AN + CLS\ncurriculum", "#1565c0"),
    ]):
        w = 1.7 if stage in (1,2) else 1.5
        ax.add_patch(FancyBboxPatch((x-w/2, 1.6), w, 2.5, boxstyle="round,pad=0.05", fc=color, ec="white"))
        ax.text(x, 3.3, label, ha="center", va="center", fontsize=10, fontweight="bold", color="white")
        ax.text(x, 2.3, sublabel, ha="center", va="center", fontsize=8, color="white")
    for x1, x2 in [(1.7, 2.7), (4.5, 5.0), (6.7, 7.6), (9.3, 10.0)]:
        ax.annotate("", xy=(x2, 2.85), xytext=(x1, 2.85), arrowprops=dict(arrowstyle="->", color="#666", lw=1.4))
    ax.text(6, 0.5, "LTSGen pipeline: 6 public TS datasets → window → GPT-5 caption → QC → 62K paired (TS, caption) for SFT",
            ha="center", fontsize=9, style="italic", color="#444")
    save(fig, "fig02_ltsgen_pipeline")

# ============================================================
# Fig 3: OpenTSLM-Flamingo architecture
# ============================================================
def fig3():
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 5.5)
    # TS encoder branch
    ax.add_patch(FancyBboxPatch((0.5, 0.5), 2.2, 0.8, boxstyle="round,pad=0.05", fc="#e3f2fd", ec="#1976d2"))
    ax.text(1.6, 0.9, "Time Series\n[B, T, vars]", ha="center", va="center", fontsize=9)
    ax.add_patch(FancyBboxPatch((0.5, 1.8), 2.2, 1.0, boxstyle="round,pad=0.05", fc="#1976d2", ec="white"))
    ax.text(1.6, 2.3, "Chronos-2 encoder\n(frozen, vars=1 winner)", ha="center", va="center", fontsize=9, color="white")
    ax.text(1.6, 3.4, "TS embedding\n[B, N_ts, d_ts]", ha="center", va="center", fontsize=8, color="#444")
    ax.annotate("", xy=(1.6, 1.8), xytext=(1.6, 1.3), arrowprops=dict(arrowstyle="->", color="#1976d2"))
    ax.annotate("", xy=(1.6, 3.7), xytext=(1.6, 2.85), arrowprops=dict(arrowstyle="->", color="#1976d2"))
    # Cross-attn block
    ax.add_patch(FancyBboxPatch((3.5, 2.2), 3, 1.8, boxstyle="round,pad=0.05", fc="#ff7043", ec="white"))
    ax.text(5, 3.3, "Flamingo cross-attention\n(trainable)", ha="center", va="center", fontsize=10, color="white", fontweight="bold")
    ax.text(5, 2.6, "TS embed   ⨯   text token\nKV from Chronos, Q from Qwen", ha="center", va="center", fontsize=8, color="white")
    # LLM branch
    ax.add_patch(FancyBboxPatch((7.0, 0.5), 2.2, 0.8, boxstyle="round,pad=0.05", fc="#fff3e0", ec="#f57c00"))
    ax.text(8.1, 0.9, "Prompt: \"Describe\nthis TS in detail.\"", ha="center", va="center", fontsize=9)
    ax.add_patch(FancyBboxPatch((7.0, 1.8), 2.2, 1.0, boxstyle="round,pad=0.05", fc="#f57c00", ec="white"))
    ax.text(8.1, 2.3, "Qwen3-4B\nLLM (LoRA-tuned)", ha="center", va="center", fontsize=9, color="white")
    ax.annotate("", xy=(8.1, 1.8), xytext=(8.1, 1.3), arrowprops=dict(arrowstyle="->", color="#f57c00"))
    ax.annotate("", xy=(6.5, 3.1), xytext=(7.0, 2.5), arrowprops=dict(arrowstyle="->", color="#666"))
    ax.annotate("", xy=(3.5, 3.1), xytext=(2.7, 3.5), arrowprops=dict(arrowstyle="->", color="#666"))
    # Output
    ax.add_patch(FancyBboxPatch((3.5, 4.5), 3, 0.7, boxstyle="round,pad=0.05", fc="#4caf50", ec="white"))
    ax.text(5, 4.85, "Caption (autoregressive decode)", ha="center", va="center", fontsize=10, color="white", fontweight="bold")
    ax.annotate("", xy=(5, 4.5), xytext=(5, 4.0), arrowprops=dict(arrowstyle="->", color="#4caf50", lw=1.4))
    ax.text(5, 0.05, "OpenTSLM-Flamingo: Qwen3-4B (LLM) + Chronos-2 (TS encoder, frozen) + Flamingo cross-attn (trainable)",
            ha="center", fontsize=9, style="italic", color="#444")
    save(fig, "fig03_opentslm_arch")

# ============================================================
# Fig 4: Curriculum 训练时间线
# ============================================================
def fig4():
    fig, ax = plt.subplots(figsize=(11, 3))
    ax.set_xlim(0, 5); ax.set_ylim(-0.5, 1.5)
    stages = [
        (0, 1, "Stage 0: M4\n(univariate forecasting\npre-train)", "#bbdefb"),
        (1, 1, "Stage 1: Forecasting\n(FC, ROUGE-L)", "#90caf9"),
        (2, 1, "Stage 2: Anomaly\n(AN)", "#64b5f6"),
        (3, 1, "Stage 3: Classification\n(CLS)", "#42a5f5"),
        (4, 1, "Stage 4: Mixed\n(FC+AN+CLS,\nval_loss 0.2026)", "#1976d2"),
    ]
    for x, w, lbl, c in stages:
        ax.add_patch(FancyBboxPatch((x+0.05, 0), w-0.1, 1, boxstyle="round,pad=0.02", fc=c, ec="white"))
        ax.text(x+w/2, 0.5, lbl, ha="center", va="center", fontsize=9, color="white" if "Mixed" in lbl else "#0d3a66")
    ax.set_yticks([]); ax.set_xticks([])
    for s in ["top","right","left","bottom"]:
        ax.spines[s].set_visible(False)
    ax.text(2.5, -0.3, "Curriculum SFT order: each stage initializes from previous; vars=1 mixed is the winner used as baseline captioner",
            ha="center", fontsize=9, style="italic", color="#444")
    save(fig, "fig04_curriculum_timeline")

# ============================================================
# Fig 5: vars=1 ablation winner
# ============================================================
def fig5():
    fig, ax = plt.subplots(figsize=(8, 4))
    expts = ["Baseline\n(vars=8)", "vars=1\n(winner)", "Unfreeze2\n(2 ep)"]
    fc = [0.618, 0.653, 0.640]; an = [0.376, 0.485, 0.400]; cls = [0.312, 0.396, 0.286]
    overall = [0.492, 0.550, 0.498]
    x = np.arange(len(expts)); w = 0.2
    for i, (data, lbl, c) in enumerate([(fc,"Forecasting","#1976d2"),(an,"Anomaly","#f57c00"),(cls,"Classification","#388e3c"),(overall,"Overall","#616161")]):
        ax.bar(x + (i-1.5)*w, data, w, label=lbl, color=c, edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(expts)
    ax.set_ylabel("ROUGE-L"); ax.set_ylim(0, 0.75)
    ax.set_title("OpenTSLM ablation: vars=1 wins (Mixed val_loss 0.2026, +12% overall)")
    ax.legend(loc="upper left", ncol=4, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig05_opentslm_ablation_vars1")

# ============================================================
# Fig 6: TSShapeQA OOD 11-condition main result
# ============================================================
def fig6():
    full6 = J(ROOT / "results/tsshapeqa_v1_ood_full6/metrics.json")["gpt-5.4-mini"]
    chatts = J(ROOT / "results/tsshapeqa_v1_ood_chatts/metrics.json")["gpt-5.4-mini"]
    cot = J(ROOT / "results/tsshapeqa_v1_ood_caption_cot/metrics.json")["gpt-5.4-mini"]
    ncot = J(ROOT / "results/tsshapeqa_v1_ood_numbers_cot/metrics.json")["gpt-5.4-mini"]
    ta = J(ROOT / "results/tsshapeqa_v1_ood_tool_agent/metrics.json")
    conds = [
        ("meta_only", full6["meta_only"]["overall"]["accuracy"], "#bdbdbd"),
        ("wrong\ncaption", full6["wrong_caption"]["overall"]["accuracy"], "#9e9e9e"),
        ("OpenTSLM\ncaption", full6["caption"]["overall"]["accuracy"], "#ff7043"),
        ("caption\n+CoT", list(cot.values())[0]["overall"]["accuracy"] if "overall" in list(cot.values())[0] else cot["caption_cot"]["overall"]["accuracy"], "#bf360c"),
        ("caption\n+numbers", full6["caption_plus"]["overall"]["accuracy"], "#fb8c00"),
        ("ChatTS\ncaption", chatts["caption"]["overall"]["accuracy"], "#ffa726"),
        ("numbers", full6["numbers"]["overall"]["accuracy"], "#1e88e5"),
        ("numbers\n+CoT", list(ncot.values())[0]["overall"]["accuracy"] if "overall" in list(ncot.values())[0] else ncot["numbers_cot"]["overall"]["accuracy"], "#1565c0"),
        ("Tool-Agent\n(gpt-5.4)", ta["overall_accuracy"], "#2e7d32"),
    ]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    names = [c[0] for c in conds]; vals = [c[1] for c in conds]; cols = [c[2] for c in conds]
    bars = ax.bar(names, vals, color=cols, edgecolor="white")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.015, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_ylim(0, 1.1); ax.set_ylabel("Accuracy (gpt-5.4-mini judge)")
    ax.set_title("TSShapeQA-v1 OOD (n=800): 9-condition comparison")
    ax.axhline(0.25, color="red", linestyle=":", linewidth=0.8, alpha=0.7); ax.text(0.1, 0.27, "random=0.25", color="red", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig06_tsshapeqa_ood_main")

# ============================================================
# Fig 7: Tool-Agent remove-one heatmap (in-dist)
# ============================================================
def fig7():
    full = J(ROOT / "results/tsshapeqa_v1_indist_tool_agent/metrics.json") if (ROOT/"results/tsshapeqa_v1_indist_tool_agent/metrics.json").exists() else None
    no_trend = J(ROOT / "results/tsshapeqa_v1_indist_ta_no_trend_v2/metrics.json")
    no_extr = J(ROOT / "results/tsshapeqa_v1_indist_ta_no_extrema_v2/metrics.json")
    no_vol = J(ROOT / "results/tsshapeqa_v1_indist_ta_no_vol_v2/metrics.json")
    qatypes = ["TREND", "EXTREMA_POS", "VOLATILITY_REGION"]
    rows = ["full (3 tools)", "−trend tool", "−extrema tool", "−vol tool"]
    M = np.array([
        [1.00, 1.00, 1.00],
        [no_trend["by_qa_type"]["TREND"]["accuracy"], no_trend["by_qa_type"]["EXTREMA_POS"]["accuracy"], no_trend["by_qa_type"]["VOLATILITY_REGION"]["accuracy"]],
        [no_extr["by_qa_type"]["TREND"]["accuracy"], no_extr["by_qa_type"]["EXTREMA_POS"]["accuracy"], no_extr["by_qa_type"]["VOLATILITY_REGION"]["accuracy"]],
        [no_vol["by_qa_type"]["TREND"]["accuracy"], no_vol["by_qa_type"]["EXTREMA_POS"]["accuracy"], no_vol["by_qa_type"]["VOLATILITY_REGION"]["accuracy"]],
    ])
    fig, ax = plt.subplots(figsize=(7, 3.5))
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(3)); ax.set_xticklabels(qatypes)
    ax.set_yticks(range(4)); ax.set_yticklabels(rows)
    for i in range(4):
        for j in range(3):
            ax.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center", color="black" if M[i,j]>0.4 else "white", fontsize=11)
    ax.set_title("Tool-Agent remove-one: each tool is causally necessary for its task (TSShapeQA in-dist n=300)")
    plt.colorbar(im, ax=ax, fraction=0.04, pad=0.04, label="accuracy")
    save(fig, "fig07_toolagent_removeone")

# ============================================================
# Fig 8: dataset_a per-ability comparison
# ============================================================
def fig8():
    chatts = J(ROOT / "results/dataset_a_chatts/summary.json")["by_condition"]
    opentslm = J(ROOT / "results/dataset_a_opentslm/summary.json")["by_condition"]
    abilities = ["local", "local-inductive", "noise", "season", "trend"]
    nums = [chatts["numbers"]["by_ability_type"][a]["categorical"] for a in abilities]
    chcap = [chatts["caption"]["by_ability_type"][a]["categorical"] for a in abilities]
    otcap = [opentslm["caption"]["by_ability_type"][a]["categorical"] for a in abilities]
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(abilities)); w = 0.27
    ax.bar(x-w, nums, w, label="numbers", color="#1e88e5", edgecolor="white")
    ax.bar(x, chcap, w, label="ChatTS caption", color="#ffa726", edgecolor="white")
    ax.bar(x+w, otcap, w, label="OpenTSLM caption", color="#ff7043", edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(abilities)
    ax.set_ylabel("categorical accuracy"); ax.set_ylim(0, 1.15)
    ax.set_title("dataset_a univariate (n=117, gpt-5.4-mini judge): caption usefulness by ability")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    for i,(a,b,c) in enumerate(zip(nums, chcap, otcap)):
        for off, v in zip([-w,0,w], [a,b,c]):
            ax.text(i+off, v+0.02, f"{v:.2f}", ha="center", fontsize=7)
    save(fig, "fig08_dataset_a_per_ability")

# ============================================================
# Fig 9: TSAQA per-task heatmap (gpt-5.4 judge)
# ============================================================
def fig9():
    op = J(ROOT / "results/tsaqa_eval/metrics.json")["gpt-5.4"]
    ch = J(ROOT / "results/tsaqa_eval_chatts/metrics.json")["gpt-5.4"]
    tasks = ["classification", "anomaly_detection", "characterization", "temporal_relationship", "comparison", "data_transformation"]
    conds = [("meta_only", op["meta_only"]), ("wrong_caption", op["wrong_caption"]),
             ("OpenTSLM cap", op["caption"]), ("ChatTS cap", ch["caption"]),
             ("caption+numbers", op["caption_plus"]), ("numbers", op["numbers"])]
    M = np.array([[c[1][t]["accuracy"] for t in tasks] for c in conds])
    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(tasks))); ax.set_xticklabels(tasks, rotation=20, ha="right")
    ax.set_yticks(range(len(conds))); ax.set_yticklabels([c[0] for c in conds])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center", color="black" if M[i,j]>0.45 else "white", fontsize=9)
    ax.set_title("TSAQA per-task accuracy (n=996, gpt-5.4 judge): caption ≈ wrong on most tasks")
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    save(fig, "fig09_tsaqa_heatmap")

# ============================================================
# Fig 10: TSAQA Tool-Agent vs numbers per-task
# ============================================================
def fig10():
    op = J(ROOT / "results/tsaqa_eval/metrics.json")["gpt-5.4"]
    ch = J(ROOT / "results/tsaqa_eval_chatts/metrics.json")["gpt-5.4"]
    ta = J(ROOT / "results/tsaqa_tool_agent/metrics.json")["gpt-5.4"]["tool_agent"]
    tasks = ["classification", "anomaly_detection", "characterization", "temporal_relationship", "comparison", "data_transformation"]
    nums = [op["numbers"][t]["accuracy"] for t in tasks]
    chcap = [ch["caption"][t]["accuracy"] for t in tasks]
    taa = [ta[t]["accuracy"] for t in tasks]
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(tasks)); w = 0.27
    ax.bar(x-w, nums, w, label="numbers", color="#1e88e5", edgecolor="white")
    ax.bar(x, chcap, w, label="ChatTS caption", color="#ffa726", edgecolor="white")
    ax.bar(x+w, taa, w, label="Tool-Agent", color="#388e3c", edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(tasks, rotation=15, ha="right")
    ax.set_ylim(0, 1.0); ax.set_ylabel("accuracy")
    ax.set_title("TSAQA per-task: Tool-Agent 0.556 < numbers 0.631 (overall); temporal_relationship 0.36 reveals tool coverage gap")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    save(fig, "fig10_tsaqa_toolagent_per_task")

# ============================================================
# Fig 11: Cross-benchmark overview (4 benchmarks)
# ============================================================
def fig11():
    benchmarks = ["TSShapeQA-v1\nOOD (n=800)", "TSShapeQA-v1\nin-dist (n=300)", "dataset_a uv\n(n=117, ChatTS in-dist)", "TSAQA\n(n=996, OOD)", "TimeSeriesExam\n(n=263, OOD)"]
    methods = ["meta_only", "OpenTSLM cap", "ChatTS cap", "numbers", "Tool-Agent"]
    M = np.array([
        [0.335, 0.335, 0.529, 0.554, 1.000],   # TSShapeQA OOD
        [0.337, 0.350, 0.533, 0.597, 1.000],   # TSShapeQA in-dist
        [0.405, 0.335, 0.861, 0.651, 0.735],   # dataset_a (cat)
        [0.501, 0.449, 0.461, 0.631, 0.556],   # TSAQA gpt-5.4
        [0.392, 0.361, 0.513, 0.677, np.nan],  # TimeSeriesExam (gpt-5.4)
    ])
    fig, ax = plt.subplots(figsize=(9, 4.5))
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(methods))); ax.set_xticklabels(methods)
    ax.set_yticks(range(len(benchmarks))); ax.set_yticklabels(benchmarks)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i,j]
            if np.isnan(v):
                ax.text(j, i, "n/a", ha="center", va="center", color="#666", fontsize=10)
            else:
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", color="black" if v>0.45 else "white", fontsize=10, fontweight="bold" if v == np.nanmax(M[i]) else "normal")
    ax.set_title("Cross-benchmark overview: 4 benchmarks, 3 different paradigms win — no universal generalist")
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04, label="accuracy")
    save(fig, "fig11_cross_benchmark")

# ============================================================
# Fig 12: Conditioning ablation flip rate
# ============================================================
def fig12():
    op = J(ROOT / "data/tsshapeqa/conditioning/flip_rate.json")
    ch = J(ROOT / "data/tsshapeqa/conditioning_chatts/flip_rate.json")
    transforms = ["time_reversal\n(n=22)", "variance_injection\n(n=14)", "Overall\n(n=36)"]
    op_rates = [op["time_reversal"]["caption_flipped_correctly_rate"], op["variance_injection_second_half"]["caption_flipped_correctly_rate"], op["overall"]["caption_flipped_correctly_rate"]]
    ch_rates = [ch["time_reversal"]["caption_flipped_correctly_rate"], ch["variance_injection_second_half"]["caption_flipped_correctly_rate"], ch["overall"]["caption_flipped_correctly_rate"]]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(transforms)); w = 0.35
    ax.bar(x-w/2, op_rates, w, label="OpenTSLM-Flamingo (4B)", color="#ff7043", edgecolor="white")
    ax.bar(x+w/2, ch_rates, w, label="ChatTS-14B", color="#ffa726", edgecolor="white")
    ax.axhline(0.6, color="red", linestyle=":", lw=0.8, alpha=0.7); ax.text(0.1, 0.62, "60% threshold (paradigm sanity)", color="red", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(transforms)
    ax.set_ylim(0, 1.0); ax.set_ylabel("caption flipped correctly rate")
    ax.set_title("Cross-family conditioning ablation: ChatTS-14B partly recovers, but neither passes 60%")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    for i, (a, b) in enumerate(zip(op_rates, ch_rates)):
        ax.text(i-w/2, a+0.02, f"{a:.2%}", ha="center", fontsize=8)
        ax.text(i+w/2, b+0.02, f"{b:.2%}", ha="center", fontsize=8)
    save(fig, "fig12_conditioning_flip_rate")

# ============================================================
# Fig 13: ChatTS cap vs numbers gap across 4 benchmarks
# ============================================================
def fig13():
    benchmarks = ["TSShapeQA OOD\n(n=800)", "TSShapeQA in-dist\n(n=300)", "dataset_a (ChatTS\nin-dist, cat, n=117)", "TimeSeriesExam\n(OOD, n=263)", "TSAQA\n(OOD, n=996)"]
    chatts_cap = [0.529, 0.533, 0.861, 0.513, 0.461]
    numbers = [0.554, 0.597, 0.651, 0.677, 0.631]
    gap = [c - n for c, n in zip(chatts_cap, numbers)]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = ["#388e3c" if g >= 0 else "#d32f2f" for g in gap]
    bars = ax.bar(benchmarks, gap, color=colors, edgecolor="white")
    for b, g in zip(bars, gap):
        y = g + (0.012 if g >= 0 else -0.025)
        ax.text(b.get_x()+b.get_width()/2, y, f"{g:+.2f}", ha="center", fontsize=10, fontweight="bold")
    ax.axhline(0, color="black", lw=1)
    ax.set_ylabel("ChatTS caption acc − numbers acc (pp)")
    ax.set_ylim(-0.25, 0.25)
    ax.set_title("ChatTS caption vs numbers: format-dependent (winning only on ChatTS in-distribution data)")
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig13_caption_vs_numbers_gap")

# ============================================================
# Fig 14: T1 BoN reward distribution per qa_type
# ============================================================
def fig14():
    t1 = J(ROOT / "results/t1_bon_chatts_tsshapeqa/metrics.json")["by_temperature"]
    qatypes = ["TREND", "EXTREMA_POS", "VOLATILITY_REGION"]
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(qatypes)); w = 0.18
    for i, T in enumerate(["0.7", "1.0"]):
        per = t1[T]["per_qa_type_gap"]
        means = [per[q]["mean_reward"] for q in qatypes]
        maxs = [per[q]["max_reward"] for q in qatypes]
        off = (i - 0.5) * (2*w)
        ax.bar(x + off - w/2, means, w, label=f"mean (T={T})", color="#90caf9" if i==0 else "#42a5f5", edgecolor="white")
        ax.bar(x + off + w/2, maxs, w, label=f"max@16 (T={T})", color="#1e88e5" if i==0 else "#0d47a1", edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(qatypes)
    ax.set_ylim(0, 1.05); ax.set_ylabel("reward (acc)")
    ax.set_title("T1 within-captioner BoN: ChatTS-14B max@16 ≫ mean → exploitable RL signal (gap 0.31–0.46)")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig14_t1_bon_per_qa_type")

# ============================================================
# Fig 15: T3 reward-hackability bar
# ============================================================
def fig15():
    t3 = J(ROOT / "results/t3_reward_hackability/metrics.json")
    refs = t3["_references"]
    templates = ["T3.1\ndirect_answer", "T3.2\nsemantic_inject", "T3.3\nkeyword_salad", "T3.4\nplausible_wrong", "T3.5\nempty"]
    accs = [t3[k]["overall"]["accuracy"] for k in [
        "T3.1_direct_answer_inject","T3.2_semantic_label_inject_TREND_up","T3.3_keyword_salad","T3.4_plausible_but_wrong","T3.5_empty"]]
    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.bar(templates, accs, color="#9e9e9e", edgecolor="white")
    ax.bar(templates[3], accs[3], color="#ffa726", edgecolor="white")
    for b, v in zip(bars, accs):
        ax.text(b.get_x()+b.get_width()/2, v+0.012, f"{v:.2f}", ha="center", fontsize=9)
    ax.axhline(refs["random_guess_acc"], color="red", linestyle=":", lw=0.8); ax.text(4.2, 0.26, "random=0.25", color="red", fontsize=8)
    ax.axhline(refs["chatts_temp0_baseline_acc"], color="green", linestyle=":", lw=0.8); ax.text(4.2, 0.44, f"ChatTS baseline={refs['chatts_temp0_baseline_acc']}", color="green", fontsize=8)
    ax.axhline(refs["wrong_oracle_ref_n800"], color="blue", linestyle=":", lw=0.8); ax.text(4.2, 0.42, f"wrong_oracle={refs['wrong_oracle_ref_n800']}", color="blue", fontsize=8)
    ax.set_ylim(0, 0.65); ax.set_ylabel("downstream acc (gpt-5.4-mini judge)")
    ax.set_title("T3 reward-hackability probe (n=100): all adversarial templates ≤ random+0.20 → judge ROBUST")
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig15_t3_reward_hackability")

# ============================================================
# Fig 16: Q3 SFT before-after
# ============================================================
def fig16():
    benchmarks = ["dataset_a (cat)\nn=117", "TSShapeQA OOD\nn=800"]
    pre_sft = [0.335, 0.335]
    chatts = [0.861, 0.529]
    sft = [0.4512, 0.3438]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(benchmarks)); w = 0.25
    ax.bar(x-w, pre_sft, w, label="Pre-SFT OpenTSLM (vars=1)", color="#ff7043", edgecolor="white")
    ax.bar(x,    sft,    w, label="SFT'd OpenTSLM (Q3)", color="#fb8c00", edgecolor="white")
    ax.bar(x+w, chatts,  w, label="ChatTS-14B", color="#ffa726", edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(benchmarks)
    ax.set_ylim(0, 1.0); ax.set_ylabel("accuracy (gpt-5.4-mini judge)")
    ax.set_title("Q3 Format-SFT verdict: SCALE-DETERMINES (gap to ChatTS only narrows by 12pp, 41pp remains)")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    for i, (a,b,c) in enumerate(zip(pre_sft, sft, chatts)):
        for off, v in zip([-w,0,w], [a,b,c]):
            ax.text(i+off, v+0.015, f"{v:.3f}", ha="center", fontsize=8)
    save(fig, "fig16_q3_format_sft")

# ============================================================
# Fig 17: 3-benchmark CapRL signal comparison (T2 / T2' / Q2)
# ============================================================
def fig17():
    benchmarks = ["dataset_a\n(T2)", "TimeSeriesExam\n(Q2)", "TSAQA\n(T2')"]
    gaps = [0.014, 0.084, 0.134]
    verdicts = ["NO-GO", "MARGINAL", "GO"]
    colors = ["#d32f2f", "#ffa726", "#388e3c"]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bars = ax.bar(benchmarks, gaps, color=colors, edgecolor="white")
    for b, g, v in zip(bars, gaps, verdicts):
        ax.text(b.get_x()+b.get_width()/2, g+0.005, f"+{g*100:.1f}pp\n[{v}]", ha="center", fontsize=10, fontweight="bold")
    ax.axhline(0.10, color="green", linestyle="--", lw=0.8, alpha=0.6); ax.text(2.4, 0.105, "GO threshold (+10pp)", color="green", fontsize=8)
    ax.axhline(0.03, color="red", linestyle="--", lw=0.8, alpha=0.6); ax.text(2.4, 0.035, "NO-GO threshold (+3pp)", color="red", fontsize=8)
    ax.set_ylim(0, 0.18); ax.set_ylabel("oracle-mix gap vs max-single (pp)")
    ax.set_title("Cross-captioner oracle-mix complementarity (T2/Q2/T2'): signal exists on OOD benchmarks")
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig17_caprl_oracle_mix")

# ============================================================
# Fig 18: TimeSeriesExam 5-condition bar
# ============================================================
def fig18():
    om = J(ROOT / "results/q2_timeseriesexam/metrics.json")["conditions"]
    conds = [("meta_only", om["meta_only"]["overall"]["accuracy"], "#bdbdbd"),
             ("wrong\ncaption", om["wrong_caption"]["overall"]["accuracy"], "#9e9e9e"),
             ("OpenTSLM\ncaption", om["caption_opentslm"]["overall"]["accuracy"], "#ff7043"),
             ("ChatTS\ncaption", om["caption_chatts"]["overall"]["accuracy"], "#ffa726"),
             ("numbers", om["numbers"]["overall"]["accuracy"], "#1e88e5")]
    fig, ax = plt.subplots(figsize=(8, 4))
    names = [c[0] for c in conds]; vals = [c[1] for c in conds]; cols = [c[2] for c in conds]
    bars = ax.bar(names, vals, color=cols, edgecolor="white")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.012, f"{v:.3f}", ha="center", fontsize=9)
    ax.set_ylim(0, 0.85); ax.set_ylabel("accuracy (gpt-5.4 judge)")
    ax.set_title("TimeSeriesExam (Q2, n=263): 4th benchmark replicates the format-dependence pattern")
    ax.axhline(0.25, color="red", linestyle=":", lw=0.8, alpha=0.7); ax.text(0.05, 0.27, "random=0.25", color="red", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    save(fig, "fig18_timeseriesexam_5cond")

# ============================================================
if __name__ == "__main__":
    print("Generating figures...")
    for f in [fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9, fig10, fig11, fig12, fig13, fig14, fig15, fig16, fig17, fig18]:
        try:
            f()
        except Exception as e:
            print(f"  !! {f.__name__} failed: {e}")
            import traceback; traceback.print_exc()
    print(f"\nDone. Output: {OUT}")
