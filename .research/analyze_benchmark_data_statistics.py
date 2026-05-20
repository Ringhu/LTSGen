#!/usr/bin/env python3
"""Generate data-structure statistics for the current LTSGen QA benchmarks.

The script intentionally reads local artifacts only.  It does not rerun models,
download data, or call external APIs.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT.parent / "LTSGEN-ext-a"
OUT = ROOT / "docs" / "case-studies" / "20260512-benchmark-data-statistics-zh"
TABLE_DIR = OUT / "tables"
FIG_DIR = OUT / "figures"


TSAQA_EVAL_TASKS = [
    "classification",
    "anomaly_detection",
    "characterization",
    "temporal_relationship",
    "comparison",
    "data_transformation",
]

TSAQA_ORIGINAL_BASES = {
    "anomaly_detection": 200,
    "characterization": 400,
    "temporal_relationship": 600,
}

BENCHMARK_META = {
    "TSShapeQA-OOD": {
        "origin_type": "self_built_from_existing_time_series",
        "origin_zh": "本项目自建诊断 benchmark；底层时间序列来自 Time-MMD、exchange_rate、illness 等现有真实数据，问题由本地规则特征和 GPT 生成/校验。",
        "source_reference": "local: LTSGEN-ext-a/scripts/generate/build_tsshapeqa.py",
        "local_artifact": "LTSGEN-ext-a/data/tsshapeqa/tsshapeqa_v1.jsonl",
        "benchmark_scale_note": "当前 OOD 评测集 800 题。",
        "external_scale_note": "无独立外部论文规模；这是当前项目构造的诊断集。",
    },
    "TSAQA": {
        "origin_type": "existing_paper_benchmark",
        "origin_zh": "现有论文/公开数据集 benchmark；当前使用本地 996 条评测子集，每个任务 166 条。",
        "source_reference": "https://huggingface.co/datasets/TSAQA/TSAQA-Benchmark ; https://arxiv.org/abs/2601.23204",
        "local_artifact": "LTSGEN-ext-a/results/phase_a_rft/*_items.jsonl + results/tsaqa_eval/predictions.jsonl",
        "benchmark_scale_note": "当前评测子集 996 题；6 个任务各 166 题。",
        "external_scale_note": "TSAQA 数据卡说明其覆盖约 210k samples、13 个领域；Hugging Face 标注规模为 100K<n<1M。",
    },
    "TimeSeriesExam": {
        "origin_type": "existing_paper_benchmark",
        "origin_zh": "现有论文 benchmark；当前使用本地抽样的 263 条题目。",
        "source_reference": "https://arxiv.org/abs/2410.14752",
        "local_artifact": "LTSGEN-ext-a/results/q2_timeseriesexam/items_n500.jsonl",
        "benchmark_scale_note": "当前本地评测子集 263 题。",
        "external_scale_note": "原 TimeSeriesExam 论文报告超过 700 道程序生成的多选题，来自 104 个模板。",
    },
    "dataset_a": {
        "origin_type": "existing_paper_dataset_subset",
        "origin_zh": "ChatTS 论文/代码中的 dataset-A；当前 full-eval 使用 117 条单变量子集。",
        "source_reference": "https://www.vldb.org/pvldb/vol18/p2385-xie.pdf ; https://explore.openaire.eu/search/result?pid=10.5281%2Fzenodo.14349206",
        "local_artifact": "LTSGEN-ext-a/data/chatts_bench/dataset_a_uv.json",
        "benchmark_scale_note": "当前已评测单变量子集 117 题。",
        "external_scale_note": "本地 raw dataset_a 为 159 题，其中 117 条单变量、42 条多变量。",
    },
    "dataset_a_raw_multivar": {
        "origin_type": "existing_paper_dataset_subset",
        "origin_zh": "ChatTS dataset-A 原始多变量部分；当前作为多变量补充分析口径单列。",
        "source_reference": "https://www.vldb.org/pvldb/vol18/p2385-xie.pdf ; https://explore.openaire.eu/search/result?pid=10.5281%2Fzenodo.14349206",
        "local_artifact": "LTSGEN-ext-a/data/chatts_bench/dataset/dataset_a.json",
        "benchmark_scale_note": "当前多变量子集 42 题。",
        "external_scale_note": "本地 raw dataset_a 为 159 题，其中 42 条多变量。",
    },
    "FREDQA": {
        "origin_type": "self_built_from_fred_blog",
        "origin_zh": "本项目整理/构造的宏观经济领域 QA；底层来自 FRED/FRED blog 风格经济序列，本地未发现独立公开 benchmark 论文元信息。",
        "source_reference": "local: dataset/fred_blog.jsonl ; gen_tst_dataset/fred/archive/merge_fred_qa_with_captions.jsonl",
        "local_artifact": ".research/fredqa-rerun-20260511/fredqa_qa_items.jsonl",
        "benchmark_scale_note": "当前本地 QA/eval 集 604 题。",
        "external_scale_note": "本地构造口径；无外部论文总规模可引用。",
    },
}


def configure_fonts() -> None:
    """Prefer a CJK-capable font so Chinese plot text renders on Ubuntu."""
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
    ]
    for path in candidates:
        p = Path(path)
        if not p.exists():
            continue
        font_manager.fontManager.addfont(str(p))
        name = font_manager.FontProperties(fname=str(p)).get_name()
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
        break
    plt.rcParams["axes.unicode_minus"] = False


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path, required: bool = True) -> list[dict[str, Any]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def short(text: Any, limit: int = 180) -> str:
    s = "" if text is None else str(text)
    s = re.sub(r"\s+", " ", s.replace("\n", " ")).strip()
    return s if len(s) <= limit else s[: limit - 3].rstrip() + "..."


def safe_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def numeric_lengths_from_series(series: Any, *, orientation: str = "auto") -> list[int]:
    """Return per-variable lengths.

    Supported layouts:
    - flat: [T]
    - vars_by_time: [[T], [T], ...]
    - time_by_vars: [[V], [V], ...]
    """
    if not isinstance(series, list) or not series:
        return []
    if not isinstance(series[0], list):
        return [len(series)]

    if orientation == "time_by_vars":
        n_vars = len(series[0]) if isinstance(series[0], list) else 0
        return [len(series)] * n_vars
    if orientation == "vars_by_time":
        return [len(x) for x in series if isinstance(x, list)]

    inner_lens = [len(x) for x in series if isinstance(x, list)]
    if not inner_lens:
        return []
    # Heuristic: if the outer dimension is small and inner sequences are long,
    # this is almost certainly [V][T].  If all inner rows are short and the outer
    # dimension is long, it is [T][V].
    if len(series) <= 64 and median(inner_lens) > 8:
        return inner_lens
    if median(inner_lens) <= 64 and len(series) > median(inner_lens):
        return [len(series)] * int(inner_lens[0])
    return inner_lens


def row_from_item(
    *,
    benchmark: str,
    sample_id: str,
    source_sample_id: Any,
    eval_row_idx: Any,
    series: Any,
    task: Any = "",
    subtask: Any = "",
    domain: Any = "",
    question_type: Any = "",
    question: Any = "",
    answer: Any = "",
    atomic_attributes: list[Any] | None = None,
    artifact_path: str = "",
    orientation: str = "auto",
    notes: str = "",
) -> dict[str, Any]:
    lengths = numeric_lengths_from_series(series, orientation=orientation)
    n_vars = len(lengths)
    meta = BENCHMARK_META[benchmark]
    return {
        "benchmark": benchmark,
        "sample_id": sample_id,
        "source_sample_id": source_sample_id,
        "eval_row_idx": eval_row_idx,
        "n_variables": n_vars,
        "min_length": min(lengths) if lengths else "",
        "max_length": max(lengths) if lengths else "",
        "mean_length": round(mean(lengths), 3) if lengths else "",
        "length_consistent": int(len(set(lengths)) <= 1) if lengths else "",
        "sequence_lengths": safe_json(lengths),
        "total_values": sum(lengths) if lengths else "",
        "task": task,
        "atomic_attributes": safe_json(atomic_attributes if atomic_attributes is not None else ([task] if task else [])),
        "subtask": subtask,
        "domain": domain,
        "question_type": question_type,
        "question_excerpt": short(question),
        "answer_excerpt": short(answer, 120),
        "origin_type": meta["origin_type"],
        "origin_zh": meta["origin_zh"],
        "source_reference": meta["source_reference"],
        "local_artifact": artifact_path or meta["local_artifact"],
        "notes": notes,
    }


def load_tsaqa_full_items() -> dict[int, dict[str, Any]]:
    """Map the 996-row TSAQA eval order to local item rows with series."""
    paths = [
        EXT / "results/phase_a_rft/tsaqa_nondesc_items.jsonl",
        EXT / "results/phase_a_rft/train_items.jsonl",
        EXT / "results/phase_a_rft/heldout_items.jsonl",
    ]
    by_eval_idx: dict[int, dict[str, Any]] = {}
    for path in paths:
        for item in read_jsonl(path, required=False):
            task = str(item.get("task") or "")
            if task not in TSAQA_EVAL_TASKS:
                continue
            try:
                trailing_id = int(str(item.get("id") or "").rsplit(":", 1)[1])
            except (ValueError, IndexError):
                trailing_id = -1
            if task in TSAQA_ORIGINAL_BASES:
                raw_idx = item.get("tsaqa_index", trailing_id)
                try:
                    local_i = int(raw_idx) - TSAQA_ORIGINAL_BASES[task]
                except (TypeError, ValueError):
                    continue
            else:
                local_i = trailing_id
            if not 0 <= local_i < 166:
                continue
            eval_i = TSAQA_EVAL_TASKS.index(task) * 166 + local_i
            by_eval_idx[eval_i] = item
    return by_eval_idx


def build_sample_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    tsshape_path = EXT / "data/tsshapeqa/tsshapeqa_v1.jsonl"
    for i, item in enumerate(read_jsonl(tsshape_path)):
        rows.append(
            row_from_item(
                benchmark="TSShapeQA-OOD",
                sample_id=str(item.get("id") or f"tsshapeqa::{i:04d}"),
                source_sample_id=i,
                eval_row_idx=i,
                series=item.get("series"),
                task=item.get("qa_type", ""),
                atomic_attributes=[item.get("qa_type", "")],
                subtask=item.get("dataset", ""),
                domain=item.get("domain", ""),
                question_type="multiple_choice",
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                artifact_path=str(tsshape_path),
            )
        )

    tsaqa_items = load_tsaqa_full_items()
    for eval_i in range(996):
        item = tsaqa_items.get(eval_i, {})
        task = str(item.get("task") or TSAQA_EVAL_TASKS[eval_i // 166])
        rows.append(
            row_from_item(
                benchmark="TSAQA",
                sample_id=f"tsaqa::{eval_i:04d}",
                source_sample_id=item.get("tsaqa_index") or item.get("id") or eval_i,
                eval_row_idx=eval_i,
                series=item.get("series", []),
                task=task,
                atomic_attributes=[task],
                subtask=item.get("question_type", ""),
                domain=item.get("domain", ""),
                question_type=item.get("question_type", ""),
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                artifact_path="LTSGEN-ext-a/results/phase_a_rft/*_items.jsonl",
                notes="TSAQA eval order reconstructed from local phase_a_rft items.",
            )
        )

    tse_path = EXT / "results/q2_timeseriesexam/items_n500.jsonl"
    for i, item in enumerate(read_jsonl(tse_path)):
        rows.append(
            row_from_item(
                benchmark="TimeSeriesExam",
                sample_id=str(item.get("id") or f"timeseriesexam::{i:04d}"),
                source_sample_id=item.get("tid", ""),
                eval_row_idx=i,
                series=item.get("series"),
                task=item.get("category", ""),
                atomic_attributes=[item.get("category", "")],
                subtask=item.get("subcategory", ""),
                domain="synthetic_time_series_concepts",
                question_type=item.get("question_type", ""),
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                artifact_path=str(tse_path),
            )
        )

    dataset_a_uv_path = EXT / "data/chatts_bench/dataset_a_uv.json"
    for i, item in enumerate(read_json(dataset_a_uv_path)):
        abilities = item.get("ability_types", [])
        rows.append(
            row_from_item(
                benchmark="dataset_a",
                sample_id=f"dataset_a::{i:04d}",
                source_sample_id=i,
                eval_row_idx=i,
                series=item.get("timeseries"),
                task=";".join(str(x) for x in abilities),
                atomic_attributes=abilities,
                subtask="dataset_a_univariate",
                domain=infer_dataset_a_domain(item.get("question", "")),
                question_type="open_ended_multi_part",
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                artifact_path=str(dataset_a_uv_path),
                orientation="vars_by_time",
            )
        )

    dataset_a_raw_path = EXT / "data/chatts_bench/dataset/dataset_a.json"
    for i, item in enumerate(read_json(dataset_a_raw_path)):
        lengths = numeric_lengths_from_series(item.get("timeseries"), orientation="vars_by_time")
        if len(lengths) <= 1:
            continue
        abilities = item.get("ability_types", [])
        rows.append(
            row_from_item(
                benchmark="dataset_a_raw_multivar",
                sample_id=f"dataset_a_raw::{i:04d}",
                source_sample_id=i,
                eval_row_idx="",
                series=item.get("timeseries"),
                task=";".join(str(x) for x in abilities),
                atomic_attributes=abilities,
                subtask="dataset_a_raw_multivariate",
                domain=infer_dataset_a_domain(item.get("question", "")),
                question_type="open_ended_multi_part",
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                artifact_path=str(dataset_a_raw_path),
                orientation="vars_by_time",
            )
        )

    fred_path = ROOT / ".research/fredqa-rerun-20260511/fredqa_qa_items.jsonl"
    for source_i, item in enumerate(read_jsonl(fred_path)):
        rows.append(
            row_from_item(
                benchmark="FREDQA",
                sample_id=f"fredqa::{item.get('idx', source_i)}",
                source_sample_id=item.get("idx", source_i),
                eval_row_idx=source_i,
                series=item.get("timeseries"),
                task=";".join(str(x) for x in item.get("attributes", [])),
                atomic_attributes=item.get("attributes", []),
                subtask="fredqa",
                domain="macroeconomics",
                question_type="multiple_choice",
                question=item.get("question", ""),
                answer=item.get("answer", ""),
                artifact_path=str(fred_path),
                orientation="vars_by_time",
            )
        )

    return rows


def infer_dataset_a_domain(question: str) -> str:
    m = re.search(r" from ([^.\n]+?) with length", question)
    if m:
        return m.group(1).strip().strip('"')
    m = re.search(r"monitoring system of ([^,.\n]+)", question, flags=re.I)
    if m:
        return m.group(1).strip()
    return "unknown"


def percentile(vals: list[float], q: float) -> float:
    if not vals:
        return math.nan
    vals = sorted(vals)
    pos = (len(vals) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - pos) + vals[hi] * (pos - lo)


def top_counts(values: list[Any], k: int = 8) -> str:
    c = Counter(str(v) for v in values if str(v) != "")
    return "; ".join(f"{name}:{n}" for name, n in c.most_common(k))


def atomic_values(row: dict[str, Any]) -> list[str]:
    raw = row.get("atomic_attributes", "[]")
    try:
        vals = json.loads(str(raw))
    except json.JSONDecodeError:
        vals = []
    out = []
    for val in vals:
        text = str(val).strip()
        if text:
            out.append(text)
    return out


def build_summaries(rows: list[dict[str, Any]]) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    by_bench: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_bench[row["benchmark"]].append(row)

    summary_rows: list[dict[str, Any]] = []
    nvar_rows: list[dict[str, Any]] = []
    length_bin_rows: list[dict[str, Any]] = []
    task_rows: list[dict[str, Any]] = []
    atomic_rows: list[dict[str, Any]] = []

    for benchmark in BENCHMARK_META:
        group = by_bench.get(benchmark, [])
        if not group:
            continue
        nvars = [int(r["n_variables"]) for r in group if r["n_variables"] != ""]
        lengths = [int(r["max_length"]) for r in group if r["max_length"] != ""]
        meta = BENCHMARK_META[benchmark]
        summary_rows.append(
            {
                "benchmark": benchmark,
                "n_samples_local_scope": len(group),
                "n_with_direct_series": len(lengths),
                "direct_series_coverage": round(len(lengths) / len(group), 4) if group else "",
                "n_univariate": sum(1 for x in nvars if x == 1),
                "n_multivariate": sum(1 for x in nvars if x > 1),
                "multivariate_pct": round(sum(1 for x in nvars if x > 1) / len(nvars), 4) if nvars else "",
                "n_variables_min": min(nvars) if nvars else "",
                "n_variables_median": median(nvars) if nvars else "",
                "n_variables_mean": round(mean(nvars), 3) if nvars else "",
                "n_variables_max": max(nvars) if nvars else "",
                "length_min": min(lengths) if lengths else "",
                "length_p25": round(percentile(lengths, 0.25), 3) if lengths else "",
                "length_median": median(lengths) if lengths else "",
                "length_mean": round(mean(lengths), 3) if lengths else "",
                "length_p75": round(percentile(lengths, 0.75), 3) if lengths else "",
                "length_p90": round(percentile(lengths, 0.90), 3) if lengths else "",
                "length_max": max(lengths) if lengths else "",
                "unique_lengths_top": top_counts(lengths),
                "task_top": top_counts([r.get("task", "") for r in group], 10),
                "origin_type": meta["origin_type"],
                "origin_zh": meta["origin_zh"],
                "benchmark_scale_note": meta["benchmark_scale_note"],
                "external_scale_note": meta["external_scale_note"],
                "source_reference": meta["source_reference"],
                "local_artifact": meta["local_artifact"],
            }
        )
        for nvar, count in sorted(Counter(nvars).items()):
            nvar_rows.append(
                {
                    "benchmark": benchmark,
                    "n_variables": nvar,
                    "n_samples": count,
                    "pct": round(count / len(group), 4),
                }
            )
        for label, pred in LENGTH_BINS:
            count = sum(1 for x in lengths if pred(x))
            if count:
                length_bin_rows.append(
                    {
                        "benchmark": benchmark,
                        "length_bin": label,
                        "n_samples": count,
                        "pct": round(count / len(lengths), 4) if lengths else "",
                    }
                )
        for task, count in Counter(str(r.get("task", "")) for r in group).most_common():
            task_rows.append(
                {
                    "benchmark": benchmark,
                    "task": task,
                    "n_samples": count,
                    "pct": round(count / len(group), 4),
                }
            )
        atomic_counter: Counter[str] = Counter()
        for row in group:
            atomic_counter.update(atomic_values(row))
        denom = len(group)
        for attr, count in atomic_counter.most_common():
            atomic_rows.append(
                {
                    "benchmark": benchmark,
                    "atomic_attribute": attr,
                    "n_samples_with_attribute": count,
                    "pct_of_samples": round(count / denom, 4) if denom else "",
                }
            )
    return summary_rows, nvar_rows, length_bin_rows, task_rows, atomic_rows


LENGTH_BINS = [
    ("<=32", lambda x: x <= 32),
    ("33-64", lambda x: 33 <= x <= 64),
    ("65-128", lambda x: 65 <= x <= 128),
    ("129-256", lambda x: 129 <= x <= 256),
    ("257-512", lambda x: 257 <= x <= 512),
    (">512", lambda x: x > 512),
]


def plot_scale(summary_rows: list[dict[str, Any]]) -> str:
    labels = [r["benchmark"] for r in summary_rows]
    uni = [int(r["n_univariate"]) for r in summary_rows]
    multi = [int(r["n_multivariate"]) for r in summary_rows]
    fig, ax = plt.subplots(figsize=(10.8, 5.6))
    x = range(len(labels))
    ax.bar(x, uni, label="单变量样本", color="#4C78A8")
    ax.bar(x, multi, bottom=uni, label="多变量样本", color="#F58518")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("样本数")
    ax.set_title("当前 benchmark 本地统计规模：单变量/多变量样本数")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    for i, r in enumerate(summary_rows):
        total = int(r["n_samples_local_scope"])
        ax.text(i, total + max(5, total * 0.015), str(total), ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fname = "benchmark_scale_univar_multivar.png"
    fig.savefig(FIG_DIR / fname, dpi=180)
    plt.close(fig)
    return fname


def plot_nvars(summary_rows: list[dict[str, Any]]) -> str:
    labels = [r["benchmark"] for r in summary_rows]
    mean_vars = [float(r["n_variables_mean"]) for r in summary_rows]
    max_vars = [float(r["n_variables_max"]) for r in summary_rows]
    fig, ax = plt.subplots(figsize=(10.8, 5.2))
    x = list(range(len(labels)))
    width = 0.36
    ax.bar([i - width / 2 for i in x], mean_vars, width=width, label="平均变量数", color="#54A24B")
    ax.bar([i + width / 2 for i in x], max_vars, width=width, label="最大变量数", color="#E45756")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("变量数")
    ax.set_title("每个样本的变量数分布概览")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fname = "benchmark_nvars_mean_max.png"
    fig.savefig(FIG_DIR / fname, dpi=180)
    plt.close(fig)
    return fname


def plot_lengths(rows: list[dict[str, Any]]) -> str:
    labels = []
    data = []
    for benchmark in BENCHMARK_META:
        vals = [int(r["max_length"]) for r in rows if r["benchmark"] == benchmark and r["max_length"] != ""]
        if vals:
            labels.append(benchmark)
            data.append(vals)
    fig, ax = plt.subplots(figsize=(11.2, 5.8))
    ax.boxplot(data, tick_labels=labels, showfliers=False)
    ax.set_yscale("log")
    ax.set_ylabel("每变量序列长度（log scale）")
    ax.set_title("每个 benchmark 的时序长度分布")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fname = "benchmark_length_boxplot.png"
    fig.savefig(FIG_DIR / fname, dpi=180)
    plt.close(fig)
    return fname


def plot_origin(summary_rows: list[dict[str, Any]]) -> str:
    counts = Counter(r["origin_type"] for r in summary_rows for _ in range(int(r["n_samples_local_scope"])))
    labels = list(counts.keys())
    values = [counts[k] for k in labels]
    color_map = {
        "existing_paper_benchmark": "#72B7B2",
        "existing_paper_dataset_subset": "#B279A2",
        "self_built_from_existing_time_series": "#4C78A8",
        "self_built_from_fred_blog": "#F58518",
    }
    colors = [color_map.get(k, "#9D755D") for k in labels]
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    ax.barh(labels, values, color=colors)
    ax.set_xlabel("样本数")
    ax.set_title("样本来源类型分布")
    ax.grid(axis="x", alpha=0.25)
    for i, v in enumerate(values):
        ax.text(v + max(4, max(values) * 0.01), i, str(v), va="center", fontsize=9)
    fig.tight_layout()
    fname = "benchmark_origin_distribution.png"
    fig.savefig(FIG_DIR / fname, dpi=180)
    plt.close(fig)
    return fname


def md_table(rows: list[dict[str, Any]], columns: list[str], headers: list[str] | None = None) -> list[str]:
    headers = headers or columns
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        vals = [str(row.get(c, "")).replace("|", "\\|") for c in columns]
        out.append("| " + " | ".join(vals) + " |")
    return out


def render_report(
    summary_rows: list[dict[str, Any]],
    nvar_rows: list[dict[str, Any]],
    length_bin_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    atomic_rows: list[dict[str, Any]],
    fig_names: list[str],
) -> None:
    total = sum(int(r["n_samples_local_scope"]) for r in summary_rows)
    total_multi = sum(int(r["n_multivariate"]) for r in summary_rows)
    total_existing = sum(
        int(r["n_samples_local_scope"])
        for r in summary_rows
        if str(r["origin_type"]).startswith("existing")
    )
    lines: list[str] = []
    lines.append("# 当前 Benchmark 数据结构统计报告")
    lines.append("")
    lines.append("本报告只统计当前 LTSGen case study / full-eval 实际使用或单列分析的 benchmark 口径：`TSShapeQA-OOD`、`TSAQA`、`TimeSeriesExam`、`dataset_a`、`dataset_a_raw_multivar`、`FREDQA`。")
    lines.append("")
    lines.append("## 口径说明")
    lines.append("")
    lines.append("- `变量数`：一个 QA 样本输入给模型的时间序列通道数。")
    lines.append("- `时序长度`：每个变量的时间步数；若同一样本多变量长度不同，明细表同时记录 `min_length` 和 `max_length`。")
    lines.append("- `benchmark 规模`：这里优先报告当前本地评测/分析实际覆盖的规模，同时在来源列说明外部公开 benchmark 的总规模。")
    lines.append("- `dataset_a` 和 `dataset_a_raw_multivar` 分开统计：前者是当前 117 条单变量评测集，后者是原始 dataset-A 中 42 条多变量问题。")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 当前统计覆盖 `{total}` 个本地样本口径。")
    lines.append(f"- 多变量样本 `{total_multi}` 个，占 `{total_multi / total:.1%}`。")
    lines.append(f"- 来自现有论文/公开 benchmark 或其数据子集的样本 `{total_existing}` 个，占 `{total_existing / total:.1%}`；其余为本项目自建诊断/领域 QA。")
    lines.append("")
    for fig in fig_names:
        lines.append(f"![{fig}](figures/{fig})")
        lines.append("")
    lines.append("### Benchmark 级汇总")
    lines.extend(
        md_table(
            summary_rows,
            [
                "benchmark",
                "n_samples_local_scope",
                "n_univariate",
                "n_multivariate",
                "n_variables_median",
                "n_variables_max",
                "length_median",
                "length_min",
                "length_max",
                "origin_type",
            ],
            [
                "Benchmark",
                "本地规模",
                "单变量",
                "多变量",
                "变量数中位数",
                "最大变量数",
                "长度中位数",
                "最短",
                "最长",
                "来源类型",
            ],
        )
    )
    lines.append("")
    lines.append("### 来源与规模说明")
    lines.extend(
        md_table(
            summary_rows,
            [
                "benchmark",
                "origin_zh",
                "benchmark_scale_note",
                "external_scale_note",
                "local_artifact",
            ],
            ["Benchmark", "来源判断", "当前本地规模", "外部/原始规模", "本地数据源"],
        )
    )
    lines.append("")
    lines.append("## 变量数分布")
    lines.append("")
    lines.extend(md_table(nvar_rows, ["benchmark", "n_variables", "n_samples", "pct"], ["Benchmark", "变量数", "样本数", "占比"]))
    lines.append("")
    lines.append("## 时序长度分布")
    lines.append("")
    lines.extend(md_table(length_bin_rows, ["benchmark", "length_bin", "n_samples", "pct"], ["Benchmark", "长度区间", "样本数", "占比"]))
    lines.append("")
    lines.append("## 任务/题型分布")
    lines.append("")
    # Keep report readable: task table can be long for dataset_a/FRED attributes.
    compact_task_rows = []
    for benchmark in BENCHMARK_META:
        bench_rows = [r for r in task_rows if r["benchmark"] == benchmark]
        compact_task_rows.extend(bench_rows[:12])
    lines.extend(md_table(compact_task_rows, ["benchmark", "task", "n_samples", "pct"], ["Benchmark", "任务/属性", "样本数", "占比"]))
    lines.append("")
    lines.append("完整逐样本明细在 `tables/benchmark_sample_statistics.csv`；完整任务分布在 `tables/benchmark_task_distribution.csv`。")
    lines.append("")
    lines.append("## 原子能力/属性分布")
    lines.append("")
    lines.append("这个表把 Dataset-A 和 FREDQA 中的组合能力标签拆开统计。同一个样本可能同时计入多个原子属性，因此占比相加可以超过 100%。")
    lines.append("")
    compact_atomic_rows = []
    for benchmark in BENCHMARK_META:
        bench_rows = [r for r in atomic_rows if r["benchmark"] == benchmark]
        compact_atomic_rows.extend(bench_rows[:12])
    lines.extend(
        md_table(
            compact_atomic_rows,
            ["benchmark", "atomic_attribute", "n_samples_with_attribute", "pct_of_samples"],
            ["Benchmark", "原子能力/属性", "含该属性样本数", "占该 benchmark 样本比例"],
        )
    )
    lines.append("")
    lines.append("完整原子属性分布在 `tables/benchmark_atomic_attribute_distribution.csv`。")
    lines.append("")
    lines.append("## 关键观察")
    lines.append("")
    lines.append("1. **TSShapeQA-OOD 是自建、单变量、固定窗口诊断集。** 它的变量数恒为 1，长度集中在 256/384/512，适合诊断趋势、极值位置和波动半区等纯形态能力。")
    lines.append("2. **TSAQA 是现有公开 benchmark，本地评测子集规模最大。** 当前 996 条覆盖 6 个任务，每类 166 条；其中 comparison 任务带来主要多变量输入。")
    lines.append("3. **TimeSeriesExam 是现有论文 benchmark 的本地子集。** 当前 263 条均为单变量，但长度跨度较大，适合观察 LLM 对通用时序概念的理解，而不是领域知识。")
    lines.append("4. **dataset_a 的两个口径不能混用。** 当前 full-eval 的 `dataset_a` 是 117 条单变量问题；原始 `dataset_a_raw_multivar` 有 42 条多变量问题，变量数可到 33，任务性质更接近领域/因果/聚类/相关性分析。")
    lines.append("5. **FREDQA 是当前最重要的自建领域 QA。** 它覆盖 604 条宏观经济问题，变量数 1-5、长度跨度很大；很多问题需要领域机制或指定窗口数值证据，因此不能只和纯形态 benchmark 混在一起解释。")
    lines.append("")
    lines.append("## 输出文件")
    lines.append("")
    lines.append("- `tables/benchmark_sample_statistics.csv`：逐样本变量数、长度、任务、来源。")
    lines.append("- `tables/benchmark_summary.csv`：每个 benchmark 的规模、变量数/长度统计、来源说明。")
    lines.append("- `tables/benchmark_nvars_distribution.csv`：每个 benchmark 的变量数分布。")
    lines.append("- `tables/benchmark_length_bins.csv`：每个 benchmark 的长度区间分布。")
    lines.append("- `tables/benchmark_task_distribution.csv`：任务/属性分布。")
    lines.append("- `tables/benchmark_atomic_attribute_distribution.csv`：拆分后的原子能力/属性分布。")
    lines.append("")
    lines.append("## 外部参考")
    lines.append("")
    lines.append("- TSAQA Hugging Face dataset card: https://huggingface.co/datasets/TSAQA/TSAQA-Benchmark")
    lines.append("- TSAQA arXiv: https://arxiv.org/abs/2601.23204")
    lines.append("- TimeSeriesExam arXiv: https://arxiv.org/abs/2410.14752")
    lines.append("- ChatTS PVLDB paper: https://www.vldb.org/pvldb/vol18/p2385-xie.pdf")
    lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    (OUT / "benchmark_data_statistics_report_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    configure_fonts()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_sample_rows()
    summary_rows, nvar_rows, length_bin_rows, task_rows, atomic_rows = build_summaries(rows)

    sample_fields = [
        "benchmark",
        "sample_id",
        "source_sample_id",
        "eval_row_idx",
        "n_variables",
        "min_length",
        "max_length",
        "mean_length",
        "length_consistent",
        "sequence_lengths",
        "total_values",
        "task",
        "atomic_attributes",
        "subtask",
        "domain",
        "question_type",
        "question_excerpt",
        "answer_excerpt",
        "origin_type",
        "origin_zh",
        "source_reference",
        "local_artifact",
        "notes",
    ]
    summary_fields = [
        "benchmark",
        "n_samples_local_scope",
        "n_with_direct_series",
        "direct_series_coverage",
        "n_univariate",
        "n_multivariate",
        "multivariate_pct",
        "n_variables_min",
        "n_variables_median",
        "n_variables_mean",
        "n_variables_max",
        "length_min",
        "length_p25",
        "length_median",
        "length_mean",
        "length_p75",
        "length_p90",
        "length_max",
        "unique_lengths_top",
        "task_top",
        "origin_type",
        "origin_zh",
        "benchmark_scale_note",
        "external_scale_note",
        "source_reference",
        "local_artifact",
    ]
    write_csv(TABLE_DIR / "benchmark_sample_statistics.csv", rows, sample_fields)
    write_csv(TABLE_DIR / "benchmark_summary.csv", summary_rows, summary_fields)
    write_csv(TABLE_DIR / "benchmark_nvars_distribution.csv", nvar_rows, ["benchmark", "n_variables", "n_samples", "pct"])
    write_csv(TABLE_DIR / "benchmark_length_bins.csv", length_bin_rows, ["benchmark", "length_bin", "n_samples", "pct"])
    write_csv(TABLE_DIR / "benchmark_task_distribution.csv", task_rows, ["benchmark", "task", "n_samples", "pct"])
    write_csv(
        TABLE_DIR / "benchmark_atomic_attribute_distribution.csv",
        atomic_rows,
        ["benchmark", "atomic_attribute", "n_samples_with_attribute", "pct_of_samples"],
    )

    fig_names = [
        plot_scale(summary_rows),
        plot_nvars(summary_rows),
        plot_lengths(rows),
        plot_origin(summary_rows),
    ]

    def rel(path: Path) -> str:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    manifest = {
        "report": rel(OUT / "benchmark_data_statistics_report_zh.md"),
        "tables": {
            "sample_statistics": rel(TABLE_DIR / "benchmark_sample_statistics.csv"),
            "summary": rel(TABLE_DIR / "benchmark_summary.csv"),
            "nvars_distribution": rel(TABLE_DIR / "benchmark_nvars_distribution.csv"),
            "length_bins": rel(TABLE_DIR / "benchmark_length_bins.csv"),
            "task_distribution": rel(TABLE_DIR / "benchmark_task_distribution.csv"),
            "atomic_attribute_distribution": rel(TABLE_DIR / "benchmark_atomic_attribute_distribution.csv"),
        },
        "figures": [rel(FIG_DIR / name) for name in fig_names],
        "benchmarks": list(BENCHMARK_META.keys()),
        "n_rows": len(rows),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    render_report(summary_rows, nvar_rows, length_bin_rows, task_rows, atomic_rows, fig_names)
    print(json.dumps({"out": str(OUT), "n_rows": len(rows), "figures": fig_names}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
