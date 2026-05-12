#!/usr/bin/env python3
"""Generate visualization figures for the integrated case-study report."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "tables"
FIG_DIR = ROOT / "figures"


COLORS = {
    "meta_only": "#8c8c8c",
    "numbers": "#1f77b4",
    "opentslm_caption": "#d62728",
    "opentslm_caption_plus": "#ff9896",
    "chatts_caption": "#2ca02c",
    "chatts_caption_plus": "#98df8a",
    "tool_agent": "#9467bd",
    "help": "#2ca02c",
    "harm": "#d62728",
    "neutral": "#7f7f7f",
}


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 220,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.6,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for suffix in ("png", "svg"):
        out = FIG_DIR / f"{name}.{suffix}"
        fig.savefig(out, bbox_inches="tight")
        if suffix == "svg":
            out.write_text("\n".join(line.rstrip() for line in out.read_text().splitlines()) + "\n")
    plt.close(fig)


def percent_label(value: float) -> str:
    if pd.isna(value):
        return ""
    return f"{value * 100:.1f}"


def write_support_tables() -> None:
    help_harm = pd.DataFrame(
        [
            ["TSShapeQA-OOD", "OpenTSLM cap+num", 60, 133, 800, -0.091],
            ["TSShapeQA-OOD", "ChatTS cap+num", 181, 184, 800, -0.004],
            ["TSAQA", "OpenTSLM cap+num", 63, 113, 996, -0.050],
            ["TSAQA", "ChatTS cap+num", 82, 109, 996, -0.027],
            ["dataset_a", "OpenTSLM cap+num", 8, 7, 115, 0.009],
            ["dataset_a", "ChatTS cap+num", 40, 3, 115, 0.322],
            ["FREDQA", "OpenTSLM cap+num", 12, 11, 604, 0.0017],
            ["FREDQA", "ChatTS cap+num", 10, 15, 604, -0.0083],
        ],
        columns=["dataset", "condition", "help", "harm", "n", "net_effect"],
    )
    help_harm["help_rate"] = help_harm["help"] / help_harm["n"]
    help_harm["harm_rate"] = help_harm["harm"] / help_harm["n"]
    help_harm.to_csv(TABLE_DIR / "caption_help_harm_summary.csv", index=False)

    fredqa = pd.DataFrame(
        [
            ["overall", 604, "numbers", 0.8212],
            ["overall", 604, "opentslm_caption", 0.8063],
            ["overall", 604, "opentslm_caption_plus", 0.8228],
            ["overall", 604, "chatts_caption", 0.8195],
            ["overall", 604, "chatts_caption_plus", 0.8129],
            ["meta_only_wrong_hard_subset", 115, "numbers", 0.2348],
            ["meta_only_wrong_hard_subset", 115, "opentslm_caption", 0.1391],
            ["meta_only_wrong_hard_subset", 115, "opentslm_caption_plus", 0.2174],
            ["meta_only_wrong_hard_subset", 115, "chatts_caption", 0.2087],
            ["meta_only_wrong_hard_subset", 115, "chatts_caption_plus", 0.1913],
        ],
        columns=["subset", "n", "condition", "score"],
    )
    fredqa.to_csv(TABLE_DIR / "fredqa_overall_vs_hard_subset.csv", index=False)

    benchmark_structure = pd.DataFrame(
        [
            ["multivariate_input", 666, 0.236],
            ["requires_multivar_reasoning", 600, 0.213],
            ["domain_knowledge_required", 688, 0.244],
            ["domain_context_needed", 404, 0.143],
            ["domain_shell", 1467, 0.520],
            ["generic_ts", 263, 0.093],
        ],
        columns=["category", "n", "pct"],
    )
    benchmark_structure.to_csv(TABLE_DIR / "benchmark_structure_summary.csv", index=False)


def plot_condition_heatmap() -> None:
    df = pd.read_csv(TABLE_DIR / "overall_condition_deltas.csv")
    cols = [
        "meta_only",
        "numbers",
        "opentslm_caption",
        "opentslm_caption_plus",
        "chatts_caption",
        "chatts_caption_plus",
        "tool_agent",
    ]
    labels = ["Meta", "Numbers", "Open cap", "Open cap+num", "ChatTS cap", "ChatTS cap+num", "Tool"]
    data = df.set_index("benchmark")[cols]
    arr = data.to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(10.8, 4.6))
    cmap = plt.cm.YlGnBu.copy()
    cmap.set_bad("#f2f2f2")
    im = ax.imshow(np.ma.masked_invalid(arr), aspect="auto", vmin=0.25, vmax=1.0, cmap=cmap)
    ax.set_xticks(np.arange(len(cols)), labels=labels, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(data.index)), labels=list(data.index))
    ax.set_title("Input condition performance across benchmarks")
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            if np.isfinite(arr[i, j]):
                color = "white" if arr[i, j] > 0.72 else "black"
                ax.text(j, i, percent_label(arr[i, j]), ha="center", va="center", color=color, fontsize=8)
            else:
                ax.text(j, i, "NA", ha="center", va="center", color="#777777", fontsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Accuracy / open score")
    save(fig, "fig_condition_performance_heatmap")


def plot_caption_delta_vs_numbers() -> None:
    df = pd.read_csv(TABLE_DIR / "overall_condition_deltas.csv")
    deltas = [
        ("Open cap", "opentslm_caption_minus_numbers", COLORS["opentslm_caption"]),
        ("Open cap+num", "opentslm_caption_plus_minus_numbers", COLORS["opentslm_caption_plus"]),
        ("ChatTS cap", "chatts_caption_minus_numbers", COLORS["chatts_caption"]),
        ("ChatTS cap+num", "chatts_caption_plus_minus_numbers", COLORS["chatts_caption_plus"]),
    ]
    x = np.arange(len(df))
    width = 0.18
    fig, ax = plt.subplots(figsize=(11.2, 4.8))
    for k, (label, col, color) in enumerate(deltas):
        vals = df[col].to_numpy(dtype=float) * 100
        offset = (k - 1.5) * width
        ax.bar(x + offset, vals, width, label=label, color=color)
    ax.axhline(0, color="#333333", linewidth=0.9)
    ax.set_xticks(x, labels=df["benchmark"], rotation=25, ha="right")
    ax.set_ylabel("Delta vs numbers (pp)")
    ax.set_title("Caption conditions usually trail the raw-number baseline")
    ax.legend(ncol=4, frameon=False, loc="upper left", bbox_to_anchor=(0, 1.16))
    save(fig, "fig_caption_delta_vs_numbers")


def plot_help_harm() -> None:
    df = pd.read_csv(TABLE_DIR / "caption_help_harm_summary.csv")
    labels = [f"{r.dataset}\n{r.condition}" for r in df.itertuples()]
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(10.8, 6.4))
    help_rate = df["help_rate"] * 100
    harm_rate = df["harm_rate"] * 100
    ax.barh(y, help_rate, color=COLORS["help"], label="Help: fixes numbers-wrong")
    ax.barh(y, -harm_rate, color=COLORS["harm"], label="Harm: breaks numbers-correct")
    ax.axvline(0, color="#333333", linewidth=0.9)
    for yi, net in zip(y, df["net_effect"] * 100):
        x = 1.0 if net >= 0 else -1.0
        ha = "left" if net >= 0 else "right"
        ax.text(x, yi, f"net {net:+.1f} pp", va="center", ha=ha, fontsize=8)
    ax.set_yticks(y, labels=labels)
    ax.set_xlabel("Case rate (%)")
    ax.set_title("Caption+numbers help and harm often cancel out")
    ax.legend(frameon=False, loc="lower right")
    lim = max(help_rate.max(), harm_rate.max()) + 7
    ax.set_xlim(-lim, lim)
    ax.invert_yaxis()
    save(fig, "fig_caption_help_harm")


def plot_fredqa_hard_subset() -> None:
    df = pd.read_csv(TABLE_DIR / "fredqa_overall_vs_hard_subset.csv")
    order = ["numbers", "opentslm_caption", "opentslm_caption_plus", "chatts_caption", "chatts_caption_plus"]
    labels = ["Numbers", "Open cap", "Open cap+num", "ChatTS cap", "ChatTS cap+num"]
    colors = [
        COLORS["numbers"],
        COLORS["opentslm_caption"],
        COLORS["opentslm_caption_plus"],
        COLORS["chatts_caption"],
        COLORS["chatts_caption_plus"],
    ]
    x = np.arange(len(order))
    width = 0.36
    pivot = df.pivot(index="condition", columns="subset", values="score").loc[order]
    fig, ax = plt.subplots(figsize=(9.8, 4.6))
    ax.bar(x - width / 2, pivot["overall"] * 100, width, color=colors, alpha=0.95, label="All FREDQA (n=604)")
    ax.bar(
        x + width / 2,
        pivot["meta_only_wrong_hard_subset"] * 100,
        width,
        color=colors,
        alpha=0.45,
        hatch="//",
        label="Meta-only wrong subset (n=115)",
    )
    ax.set_xticks(x, labels=labels, rotation=20, ha="right")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("FREDQA looks easy overall, but hard subset collapses")
    ax.legend(frameon=False)
    for xpos, vals in [(x - width / 2, pivot["overall"] * 100), (x + width / 2, pivot["meta_only_wrong_hard_subset"] * 100)]:
        for xx, val in zip(xpos, vals):
            ax.text(xx, val + 1.2, f"{val:.1f}", ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0, 95)
    save(fig, "fig_fredqa_overall_vs_hard_subset")


def plot_benchmark_structure() -> None:
    df = pd.read_csv(TABLE_DIR / "benchmark_structure_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={"width_ratios": [1, 1.15]})

    mv = df[df["category"].isin(["multivariate_input", "requires_multivar_reasoning"])].copy()
    axes[0].barh(mv["category"], mv["pct"] * 100, color=["#6baed6", "#2171b5"])
    axes[0].set_xlim(0, 60)
    axes[0].set_xlabel("Share of all questions (%)")
    axes[0].set_title("Multivariate load")
    for yi, row in enumerate(mv.itertuples()):
        axes[0].text(row.pct * 100 + 1, yi, f"{row.n} ({row.pct*100:.1f}%)", va="center")

    domain = df[df["category"].isin(["domain_knowledge_required", "domain_context_needed", "domain_shell", "generic_ts"])].copy()
    domain = domain.set_index("category").loc[
        ["domain_shell", "domain_knowledge_required", "domain_context_needed", "generic_ts"]
    ].reset_index()
    axes[1].barh(domain["category"], domain["pct"] * 100, color=["#bdbdbd", "#fb6a4a", "#fdae6b", "#9ecae1"])
    axes[1].set_xlim(0, 60)
    axes[1].set_xlabel("Share of all questions (%)")
    axes[1].set_title("Domain labels are not equal")
    for yi, row in enumerate(domain.itertuples()):
        axes[1].text(row.pct * 100 + 1, yi, f"{row.n} ({row.pct*100:.1f}%)", va="center")
    save(fig, "fig_benchmark_structure")


def plot_domain_multivar_delta() -> None:
    domain = pd.read_csv(TABLE_DIR / "domain_condition_deltas.csv")
    multivar = pd.read_csv(TABLE_DIR / "multivar_condition_deltas.csv")
    domain_sel = domain[
        (domain["domain_level"] == "domain_knowledge_required")
        & (domain["benchmark"].isin(["FREDQA", "dataset_a", "dataset_a_raw_multivar"]))
    ].copy()
    domain_sel["label"] = domain_sel["benchmark"] + "\ntrue-domain"
    mv_sel = multivar[
        (
            (multivar["benchmark"] == "FREDQA")
            & (multivar["multivar_reasoning_type"].isin(
                ["cross_variable_comparison_or_relation", "cross_variable_causal_reasoning_candidate"]
            ))
        )
        | (
            (multivar["benchmark"] == "TSAQA")
            & (multivar["multivar_reasoning_type"] == "cross_series_comparison_or_relation")
        )
        | (multivar["benchmark"] == "dataset_a_raw_multivar")
    ].copy()
    short = {
        "cross_variable_comparison_or_relation": "cross-var relation",
        "cross_variable_causal_reasoning_candidate": "cross-var causal",
        "cross_series_comparison_or_relation": "cross-series relation",
        "cluster_or_cross_series_relation": "cluster/cross-series",
    }
    mv_sel["label"] = mv_sel["benchmark"] + "\n" + mv_sel["multivar_reasoning_type"].map(short)

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0), sharey=False)
    for ax, data, title in [
        (axes[0], domain_sel, "True-domain subsets"),
        (axes[1], mv_sel, "Multivariate-reasoning subsets"),
    ]:
        x = np.arange(len(data))
        ax.bar(x - 0.18, data["numbers_minus_meta_only"] * 100, 0.36, color=COLORS["numbers"], label="Numbers - meta")
        ax.bar(
            x + 0.18,
            data["best_caption_plus_minus_numbers"] * 100,
            0.36,
            color="#ff7f0e",
            label="Best cap+num - numbers",
        )
        ax.axhline(0, color="#333333", linewidth=0.9)
        ax.set_xticks(x, labels=data["label"], rotation=28, ha="right")
        ax.set_ylabel("Delta (pp)")
        ax.set_title(title)
    axes[0].legend(frameon=False, loc="upper left")
    save(fig, "fig_domain_multivar_deltas")


def main() -> None:
    setup_style()
    write_support_tables()
    plot_condition_heatmap()
    plot_caption_delta_vs_numbers()
    plot_help_harm()
    plot_fredqa_hard_subset()
    plot_benchmark_structure()
    plot_domain_multivar_delta()


if __name__ == "__main__":
    main()
