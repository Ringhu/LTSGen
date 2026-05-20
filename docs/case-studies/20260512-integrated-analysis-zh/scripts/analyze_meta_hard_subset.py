#!/usr/bin/env python3
"""Evaluate condition performance after removing meta-only-correct cases."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPORT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = REPORT_ROOT.parents[2]
TABLE_DIR = REPORT_ROOT / "tables"
FIG_DIR = REPORT_ROOT / "figures"

UNIFIED = REPO_ROOT / ".research/full-eval-statistics-20260511/unified_sample_outcomes.csv"
FREDQA = REPO_ROOT / ".research/fredqa-rerun-20260511/gpt_eval_full_gpt54/predictions.jsonl"
DATASET_A_RAW = (
    REPO_ROOT / ".research/dataset-a-raw-multivar-20260511/gpt_eval_full_gpt54/predictions.jsonl"
)

CONDITION_ORDER = [
    "meta_only",
    "numbers",
    "numbers_cot",
    "opentslm_caption",
    "opentslm_caption_plus",
    "chatts_caption",
    "chatts_caption_plus",
    "tool_agent",
]

PLOT_CONDITION_ORDER = [
    "numbers",
    "numbers_cot",
    "opentslm_caption",
    "opentslm_caption_plus",
    "chatts_caption",
    "chatts_caption_plus",
    "tool_agent",
]

CONDITION_LABELS = {
    "meta_only": "Meta",
    "numbers": "Numbers",
    "numbers_cot": "Numbers CoT",
    "opentslm_caption": "Open cap",
    "opentslm_caption_plus": "Open cap+num",
    "chatts_caption": "ChatTS cap",
    "chatts_caption_plus": "ChatTS cap+num",
    "tool_agent": "Tool",
}

BENCHMARK_ORDER = [
    "FREDQA",
    "TSAQA",
    "TSShapeQA-OOD",
    "TimeSeriesExam",
    "dataset_a",
    "dataset_a_raw_multivar",
]


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
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def primary_value(metric_kind: str, accuracy: float | None, mean_score: float | None) -> float:
    if metric_kind == "open_score":
        return np.nan if mean_score is None else mean_score
    return np.nan if accuracy is None else accuracy


def summarize_condition(
    *,
    benchmark: str,
    metric_kind: str,
    condition: str,
    meta_total_n: int,
    meta_correct_n: int,
    hard_n: int,
    correct: pd.Series | None,
    score: pd.Series | None,
    hard_mask: pd.Series,
) -> dict[str, object]:
    overall_acc = None
    hard_acc = None
    overall_correct_n = None
    hard_correct_n = None
    overall_metric_n = 0
    hard_metric_n = 0

    if correct is not None:
        correct = correct.dropna()
        overall_metric_n = int(correct.shape[0])
        overall_correct_n = int(correct.sum())
        overall_acc = float(correct.mean()) if overall_metric_n else np.nan

        hard_correct = correct[hard_mask.reindex(correct.index).fillna(False)]
        hard_metric_n = int(hard_correct.shape[0])
        hard_correct_n = int(hard_correct.sum())
        hard_acc = float(hard_correct.mean()) if hard_metric_n else np.nan

    overall_score = None
    hard_score = None
    if score is not None:
        score = score.dropna()
        if correct is None:
            overall_metric_n = int(score.shape[0])
        overall_score = float(score.mean()) if score.shape[0] else np.nan

        hard_score_values = score[hard_mask.reindex(score.index).fillna(False)]
        if correct is None:
            hard_metric_n = int(hard_score_values.shape[0])
        hard_score = float(hard_score_values.mean()) if hard_score_values.shape[0] else np.nan

    overall_value = primary_value(metric_kind, overall_acc, overall_score)
    hard_value = primary_value(metric_kind, hard_acc, hard_score)

    return {
        "benchmark": benchmark,
        "metric_kind": metric_kind,
        "condition": condition,
        "meta_total_n": meta_total_n,
        "meta_correct_n": meta_correct_n,
        "meta_correct_rate": meta_correct_n / meta_total_n if meta_total_n else np.nan,
        "hard_n": hard_n,
        "hard_fraction": hard_n / meta_total_n if meta_total_n else np.nan,
        "overall_metric_n": overall_metric_n,
        "hard_metric_n": hard_metric_n,
        "overall_correct_n": overall_correct_n,
        "hard_correct_n": hard_correct_n,
        "overall_accuracy": overall_acc,
        "hard_accuracy": hard_acc,
        "overall_mean_score": overall_score,
        "hard_mean_score": hard_score,
        "overall_value": overall_value,
        "hard_value": hard_value,
        "delta_hard_minus_overall": hard_value - overall_value,
    }


def collect_unified_rows() -> list[dict[str, object]]:
    df = pd.read_csv(UNIFIED)
    rows: list[dict[str, object]] = []
    metric_kind_by_dataset = {
        "TSAQA": "accuracy",
        "TSShapeQA-OOD": "accuracy",
        "TimeSeriesExam": "accuracy",
        "dataset_a": "open_score",
    }

    for benchmark, metric_kind in metric_kind_by_dataset.items():
        g = df[df["dataset"] == benchmark].copy()
        valid_meta = g["meta_only_correct"].dropna()
        meta_total_n = int(valid_meta.shape[0])
        meta_correct_n = int(valid_meta.sum())
        hard_mask = g["meta_only_correct"] == 0
        hard_n = int(hard_mask.sum())

        for condition in CONDITION_ORDER:
            correct_col = f"{condition}_correct"
            score_col = f"{condition}_score"
            if correct_col not in g.columns and score_col not in g.columns:
                continue
            correct = g[correct_col] if correct_col in g.columns and g[correct_col].notna().any() else None
            score = g[score_col] if score_col in g.columns and g[score_col].notna().any() else None
            if correct is None and score is None:
                continue
            rows.append(
                summarize_condition(
                    benchmark=benchmark,
                    metric_kind=metric_kind,
                    condition=condition,
                    meta_total_n=meta_total_n,
                    meta_correct_n=meta_correct_n,
                    hard_n=hard_n,
                    correct=correct,
                    score=score,
                    hard_mask=hard_mask,
                )
            )
    return rows


def collect_fredqa_rows() -> list[dict[str, object]]:
    df = pd.read_json(FREDQA, lines=True)
    correct = df.pivot(index="idx", columns="condition", values="correct")
    meta_total_n = int(correct["meta_only"].notna().sum())
    meta_correct_n = int(correct["meta_only"].sum())
    hard_mask = correct["meta_only"] == False  # noqa: E712
    hard_n = int(hard_mask.sum())

    rows: list[dict[str, object]] = []
    for condition in [c for c in CONDITION_ORDER if c in correct.columns]:
        rows.append(
            summarize_condition(
                benchmark="FREDQA",
                metric_kind="accuracy",
                condition=condition,
                meta_total_n=meta_total_n,
                meta_correct_n=meta_correct_n,
                hard_n=hard_n,
                correct=correct[condition].astype(float),
                score=None,
                hard_mask=hard_mask,
            )
        )
    return rows


def collect_dataset_a_raw_rows() -> list[dict[str, object]]:
    df = pd.read_json(DATASET_A_RAW, lines=True)
    correct = df.pivot(index="id", columns="condition", values="correct_at_0_8")
    score = df.pivot(index="id", columns="condition", values="score")
    meta_total_n = int(correct["meta_only"].notna().sum())
    meta_correct_n = int(correct["meta_only"].sum())
    hard_mask = correct["meta_only"] == False  # noqa: E712
    hard_n = int(hard_mask.sum())

    rows: list[dict[str, object]] = []
    for condition in [c for c in CONDITION_ORDER if c in correct.columns or c in score.columns]:
        rows.append(
            summarize_condition(
                benchmark="dataset_a_raw_multivar",
                metric_kind="open_score",
                condition=condition,
                meta_total_n=meta_total_n,
                meta_correct_n=meta_correct_n,
                hard_n=hard_n,
                correct=correct[condition].astype(float) if condition in correct.columns else None,
                score=score[condition] if condition in score.columns else None,
                hard_mask=hard_mask,
            )
        )
    return rows


def write_tables(rows: list[dict[str, object]]) -> pd.DataFrame:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(rows)
    out["benchmark"] = pd.Categorical(out["benchmark"], BENCHMARK_ORDER, ordered=True)
    out["condition"] = pd.Categorical(out["condition"], CONDITION_ORDER, ordered=True)
    out = out.sort_values(["benchmark", "condition"]).reset_index(drop=True)
    out.to_csv(TABLE_DIR / "meta_hard_subset_condition_deltas.csv", index=False)

    wide_base = (
        out[["benchmark", "metric_kind", "meta_total_n", "meta_correct_n", "meta_correct_rate", "hard_n", "hard_fraction"]]
        .drop_duplicates()
        .copy()
    )
    value_wide = out.pivot(index="benchmark", columns="condition", values=["overall_value", "hard_value", "delta_hard_minus_overall"])
    value_wide.columns = [f"{condition}_{kind}" for kind, condition in value_wide.columns]
    count_wide = out.pivot(index="benchmark", columns="condition", values="hard_correct_n")
    count_wide.columns = [f"{condition}_hard_correct_n" for condition in count_wide.columns]
    wide = wide_base.set_index("benchmark").join(value_wide).join(count_wide).reset_index()
    wide["benchmark"] = pd.Categorical(wide["benchmark"], BENCHMARK_ORDER, ordered=True)
    wide = wide.sort_values("benchmark")
    wide.to_csv(TABLE_DIR / "meta_hard_subset_summary_wide.csv", index=False)
    return out


def plot_hard_subset_change(df: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plot_df = df[df["condition"].isin(PLOT_CONDITION_ORDER)].copy()
    hard = plot_df.pivot(index="benchmark", columns="condition", values="hard_value").reindex(
        BENCHMARK_ORDER
    )[PLOT_CONDITION_ORDER]
    delta = plot_df.pivot(index="benchmark", columns="condition", values="delta_hard_minus_overall").reindex(
        BENCHMARK_ORDER
    )[PLOT_CONDITION_ORDER]

    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.8), gridspec_kw={"width_ratios": [1, 1]})

    hard_arr = hard.to_numpy(dtype=float)
    cmap_hard = plt.cm.YlGnBu.copy()
    cmap_hard.set_bad("#f2f2f2")
    im0 = axes[0].imshow(np.ma.masked_invalid(hard_arr), aspect="auto", vmin=0, vmax=1, cmap=cmap_hard)
    axes[0].set_title("Performance on meta-only-wrong subset")
    axes[0].set_xticks(np.arange(len(PLOT_CONDITION_ORDER)), [CONDITION_LABELS[c] for c in PLOT_CONDITION_ORDER], rotation=35, ha="right")
    axes[0].set_yticks(np.arange(len(BENCHMARK_ORDER)), BENCHMARK_ORDER)
    for i in range(hard_arr.shape[0]):
        for j in range(hard_arr.shape[1]):
            val = hard_arr[i, j]
            if np.isfinite(val):
                color = "white" if val > 0.67 else "black"
                axes[0].text(j, i, f"{val * 100:.1f}", ha="center", va="center", color=color, fontsize=8)
            else:
                axes[0].text(j, i, "NA", ha="center", va="center", color="#777777", fontsize=8)
    cbar0 = fig.colorbar(im0, ax=axes[0], fraction=0.035, pad=0.02)
    cbar0.set_label("Accuracy / open score")

    delta_arr = delta.to_numpy(dtype=float) * 100
    max_abs = max(5, float(np.nanmax(np.abs(delta_arr))))
    cmap_delta = plt.cm.RdBu.copy()
    cmap_delta.set_bad("#f2f2f2")
    im1 = axes[1].imshow(
        np.ma.masked_invalid(delta_arr),
        aspect="auto",
        vmin=-max_abs,
        vmax=max_abs,
        cmap=cmap_delta,
    )
    axes[1].set_title("Change from overall to hard subset")
    axes[1].set_xticks(np.arange(len(PLOT_CONDITION_ORDER)), [CONDITION_LABELS[c] for c in PLOT_CONDITION_ORDER], rotation=35, ha="right")
    axes[1].set_yticks(np.arange(len(BENCHMARK_ORDER)), BENCHMARK_ORDER)
    for i in range(delta_arr.shape[0]):
        for j in range(delta_arr.shape[1]):
            val = delta_arr[i, j]
            if np.isfinite(val):
                axes[1].text(j, i, f"{val:+.1f}", ha="center", va="center", color="black", fontsize=8)
            else:
                axes[1].text(j, i, "NA", ha="center", va="center", color="#777777", fontsize=8)
    cbar1 = fig.colorbar(im1, ax=axes[1], fraction=0.035, pad=0.02)
    cbar1.set_label("Delta (pp / score points)")

    fig.suptitle("Removing meta-only-correct questions exposes shortcut sensitivity", y=1.02)
    fig.tight_layout()
    for suffix in ("png", "svg"):
        out = FIG_DIR / f"fig_meta_hard_subset_condition_change.{suffix}"
        fig.savefig(out, bbox_inches="tight")
        if suffix == "svg":
            out.write_text("\n".join(line.rstrip() for line in out.read_text().splitlines()) + "\n")
    plt.close(fig)


def main() -> None:
    setup_style()
    rows = []
    rows.extend(collect_fredqa_rows())
    rows.extend(collect_unified_rows())
    rows.extend(collect_dataset_a_raw_rows())
    df = write_tables(rows)
    plot_hard_subset_change(df)
    print(f"Wrote {TABLE_DIR / 'meta_hard_subset_condition_deltas.csv'}")
    print(f"Wrote {TABLE_DIR / 'meta_hard_subset_summary_wide.csv'}")
    print(f"Wrote {FIG_DIR / 'fig_meta_hard_subset_condition_change.png'}")


if __name__ == "__main__":
    main()
