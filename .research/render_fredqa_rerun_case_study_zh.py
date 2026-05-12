#!/usr/bin/env python3
"""Render the Chinese FREDQA rerun statistics and case-study report.

The script reads existing local artifacts only. It does not rerun caption
models or QA evaluation. Translation is cached per case.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".research" / "fredqa-rerun-20260511"
OUT_DIR = ROOT / "docs" / "case-studies" / "20260512-fredqa-rerun-zh"
FIG_DIR = OUT_DIR / "figures"
REPORT = OUT_DIR / "fredqa_rerun_case_study_zh.md"
NOTION_REPORT = OUT_DIR / "fredqa_rerun_case_study_zh_notion.md"
MANIFEST = OUT_DIR / "manifest.json"
TRANSLATION_CACHE = BASE / "report_translation_cache_20260512.json"

GITHUB_BRANCH = os.environ.get("LTSGEN_REPORT_BRANCH", "fredqa-rerun-zh-20260512")
GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/Ringhu/LTSGen/"
    f"{GITHUB_BRANCH}/docs/case-studies/{OUT_DIR.name}/figures"
)
TRANSLATION_MODEL = os.environ.get("LTSGEN_TRANSLATE_MODEL", "gpt-5.4-mini")
TRANSLATION_VERSION = "fredqa-rerun-zh-v2"

CONDITIONS = [
    "meta_only",
    "numbers",
    "opentslm_caption",
    "opentslm_caption_plus",
    "chatts_caption",
    "chatts_caption_plus",
]

CONDITION_ZH = {
    "meta_only": "只给题目和选项",
    "numbers": "题目 + 原始数值序列",
    "opentslm_caption": "题目 + OpenTSLM caption",
    "opentslm_caption_plus": "题目 + OpenTSLM caption + 数值",
    "chatts_caption": "题目 + ChatTS caption",
    "chatts_caption_plus": "题目 + ChatTS caption + 数值",
}

ATTRIBUTE_ZH = {
    "Abductive Reasoning": "溯因推理",
    "Analogical Reasoning": "类比推理",
    "Causal Reasoning - Associational": "因果推理：关联型",
    "Causal Reasoning - Counterfactual": "因果推理：反事实型",
    "Causal Reasoning - Interventional": "因果推理：干预型",
    "Deductive Reasoning": "演绎推理",
    "Inductive Reasoning": "归纳推理",
}

CASE_DEFS = [
    {
        "idx": "1079",
        "tag": "OpenTSLM 错、ChatTS 对",
        "focus": "家庭资产/负债变化率在通胀冲击前后的比值变化",
        "why": "OpenTSLM 把两条序列都写成稳定上升，弱化了 2022 年资产变化相对负债变化下降这一局部比值证据；ChatTS 至少保留了资产先升后降、负债峰值位置等局部形态，因此 caption-only 能答对。",
    },
    {
        "idx": "1145",
        "tag": "OpenTSLM 错、ChatTS 对，但 caption+numbers 不稳",
        "focus": "疫情后不同年龄组劳动参与率缺口比较",
        "why": "题目要求比较 2022 年 12 月相对 2020 年 1 月的缺口。ChatTS 的单独 caption 捕捉了年轻组和年长组不同恢复形态，OpenTSLM 的通用趋势描述不足；但加入数值后 ChatTS+numbers 又答错，说明下游模型融合 caption 与数值时并不单调。",
    },
    {
        "idx": "325",
        "tag": "OpenTSLM 对、ChatTS 错",
        "focus": "3 月移动平均与 12 月移动平均的工资增长动量",
        "why": "这是反例：ChatTS 把两个移动平均都概括成 increasing，并把全局最大值放在末尾，容易诱导模型选择持续加速；OpenTSLM 虽然也有噪声，但保留了下降/回落的动量信号。",
    },
    {
        "idx": "1141",
        "tag": "OpenTSLM/数值对、ChatTS 错",
        "focus": "疫情冲击前后 sticky CPI 与 core CPI 的差距变化",
        "why": "正确答案依赖两个指定月份的绝对差。OpenTSLM+numbers 都能支持这个差值计算，ChatTS 把三个价格指标主要概括成 increasing/mixed，不能稳定表达指定月份之间的对齐程度。",
    },
    {
        "idx": "1028",
        "tag": "两个 caption 都错，numbers 对",
        "focus": "报纸与烟草工业贡献的两条因果 claim 同时验证",
        "why": "题目要求按指定年份计算百分比变化。两个 caption 都给出大量趋势、季节性、峰谷摘要，但没有可靠保留 1995/2005 与 1990/2000 的精确变化，因此 caption-only 错；直接数值能答对。",
    },
    {
        "idx": "1087",
        "tag": "两个 caption 都错，numbers 对",
        "focus": "GDP price index、gross domestic purchases、PCE price index 的平均通胀排序",
        "why": "这类问题需要对指定窗口求平均并排序。caption 的全局趋势描述会遮蔽 Q2 2021 到 Q2 2022 的局部均值关系，说明 FREDQA 中很多“领域解释题”首先还是数值抽取题。",
    },
    {
        "idx": "884",
        "tag": "六种条件全错",
        "focus": "IRA 余额的疫情反事实外推",
        "why": "题目需要用 2018-07 到 2019-07 的半年度平均增长率外推到 2021-01。caption 的全局 upward trend 和 last-third maximum 信息不足以执行反事实公式，数值条件也没有让 QA 模型稳定完成多步计算。",
    },
    {
        "idx": "560",
        "tag": "六种条件全错",
        "focus": "FDIC 机构倒闭峰值与监管解释",
        "why": "模型全部选择了表面上合理但并非标准答案的选项，说明该题不是单纯读峰值，还要求把 1980s S&L crisis 与之后更严格资本充足率规则联系起来；caption 没有编码制度性解释。",
    },
    {
        "idx": "850",
        "tag": "meta-only 对，数值和多数 caption 反而错",
        "focus": "住房相关 CPI 加权指数在能源价格反事实下的四年增长差",
        "why": "题目选项与权重公式本身已经强烈约束答案，meta-only 能直接答对；加入数值或通用 caption 后模型被局部价格走势干扰，只有 ChatTS+numbers 恢复正确。这类样本说明高 meta-only 准确率不能等价为时序理解成功。",
    },
    {
        "idx": "481",
        "tag": "meta-only 错，数值/caption 全部救回",
        "focus": "油价、公交客流、车辆里程在 2015 年 3 月的替代效应解释",
        "why": "没有时序证据时模型选错背景因素；加入数值或 caption 后都能定位春夏出行需求这一解释。这是少数 caption 真正提供有效证据的正例。",
    },
    {
        "idx": "1209",
        "tag": "meta-only 错，数值/caption 全部救回",
        "focus": "圣路易斯 premature death crude rate 与 age-adjusted rate 的衰退前后变化",
        "why": "题目需要比较两个阶段的平均年变化，并理解 age-adjustment 的含义。时序证据能把 meta-only 从错误方向拉回，说明部分干预型 FREDQA 确实受益于数据证据。",
    },
    {
        "idx": "811",
        "tag": "caption-only 对，caption+numbers 反而错",
        "focus": "美墨净迁移镜像关系的反事实计算",
        "why": "OpenTSLM 和 ChatTS caption-only 都能答对，但加上数值后又失败，说明下游模型面对长题干、反事实增长率和原始数值时会出现证据整合不稳定；caption 有时像筛选后的线索，numbers 则增加了干扰。",
    },
]

PATTERN_ZH = {
    "opentslm_wrong_chatts_right": (
        "OpenTSLM caption 错、ChatTS caption 对",
        "两个 caption 模型不是同一种失败；ChatTS 在部分局部形态或相对关系上保留了更可用的证据。",
    ),
    "opentslm_right_chatts_wrong": (
        "OpenTSLM caption 对、ChatTS caption 错",
        "OpenTSLM 也有少量优势 case，因此问题不能简化成某一个 caption 模型总是更好。",
    ),
    "both_caption_wrong_numbers_right": (
        "两个 caption 都错，但 numbers 对",
        "自然语言摘要丢失了指定日期、指定窗口或公式所需的精确信息；这是真正的 caption bottleneck。",
    ),
    "caption_and_numbers_wrong_meta_right": (
        "caption 与 numbers 错，但 meta-only 对",
        "题干/选项先验足够强，加入时序证据反而可能引入干扰；这会抬高不依赖时序理解的表观能力。",
    ),
    "meta_numbers_captions_all_wrong": (
        "meta、numbers、两个 caption 全错",
        "失败不只是输入形式问题，还包括公式执行、反事实设定、领域制度知识与长题干推理。",
    ),
    "numbers_rescue_meta_wrong": (
        "meta-only 错，但 numbers 对",
        "原始数值确实能提供额外证据；这类样本可用于验证模型是否真的读数据。",
    ),
    "chatts_rescue_meta_wrong": (
        "meta-only 错，但 ChatTS caption 对",
        "ChatTS 有时能把关键形态压缩成可用线索，是 caption 成功的正例。",
    ),
    "opentslm_rescue_meta_wrong": (
        "meta-only 错，但 OpenTSLM caption 对",
        "OpenTSLM 也能在部分样本中提供有用证据，但总体增益不稳定。",
    ),
}


def setup_matplotlib() -> None:
    for path in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf",
    ]:
        p = Path(path)
        if p.exists():
            font_manager.fontManager.addfont(str(p))
            prop = font_manager.FontProperties(fname=str(p))
            plt.rcParams["font.family"] = prop.get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_translation_client():
    if os.environ.get("LTSGEN_SKIP_TRANSLATION") == "1":
        return None
    sys.path.insert(0, str(Path.home() / "Research" / "gptapi"))
    try:
        from llm_client import chat  # type: ignore

        return chat
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"[warn] translation client unavailable: {exc}", file=sys.stderr)
        return None


def load_cache() -> dict[str, Any]:
    if TRANSLATION_CACHE.exists():
        return load_json(TRANSLATION_CACHE)
    return {}


def cache_key(payload: Any) -> str:
    blob = json.dumps(
        {"version": TRANSLATION_VERSION, "model": TRANSLATION_MODEL, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_json_object(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def translate_case(payload: dict[str, Any], cache: dict[str, Any], chat_fn) -> dict[str, Any]:
    key = cache_key(payload)
    if key in cache:
        return cache[key]
    if chat_fn is None:
        return fallback_translation(payload)

    prompt = (
        "请将下面 JSON 中所有英文字符串翻译成中文，用于科研组会汇报。要求：\n"
        "1. 保留 JSON 结构、键名、选项字母、模型名、变量编号、公式、数值、日期、单位。\n"
        "2. 不要省略、不要截断、不要总结，不要新增原文没有的信息。\n"
        "3. 如果字符串已经是中文或是空字符串，保持原样。\n"
        "4. 只输出合法 JSON，不要输出 markdown 代码块。\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            try:
                text = chat_fn(
                    prompt,
                    model=TRANSLATION_MODEL,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
            except TypeError:
                text = chat_fn(prompt, model=TRANSLATION_MODEL, temperature=0)
            translated = parse_json_object(text)
            cache[key] = translated
            write_json(TRANSLATION_CACHE, cache)
            return translated
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            time.sleep(2 + attempt)
    print(f"[warn] translation failed for {payload.get('idx')}: {last_error}", file=sys.stderr)
    return fallback_translation(payload)


def fallback_translation(payload: dict[str, Any]) -> dict[str, Any]:
    def mark(x: Any) -> Any:
        if isinstance(x, str):
            if not x:
                return ""
            return "（自动翻译未生成，保留原文用于核对）" + x
        if isinstance(x, list):
            return [mark(v) for v in x]
        if isinstance(x, dict):
            return {k: mark(v) for k, v in x.items()}
        return x

    return mark(payload)


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def pp(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.2f} pp"


def md_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def table_cell(value: Any) -> str:
    text = md_text(value).replace("\n", "<br>")
    return text.replace("|", "\\|")


def quote_block(value: Any) -> str:
    text = md_text(value).strip()
    if not text:
        return "> （源 artifact 未提供该字段。）"
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def short_label(text: str, limit: int = 62) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def trend_summary(series: list[float]) -> dict[str, Any]:
    arr = np.asarray(series, dtype=float)
    x = np.arange(len(arr), dtype=float)
    slope = float(np.polyfit(x, arr, 1)[0]) if len(arr) > 1 else 0.0
    return {
        "n": int(len(arr)),
        "start": float(arr[0]),
        "end": float(arr[-1]),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "argmin": int(np.argmin(arr)),
        "argmax": int(np.argmax(arr)),
        "slope": slope,
    }


def result_mark(correct: bool) -> str:
    return "正确" if correct else "错误"


def result_icon(correct: bool) -> str:
    return "✓" if correct else "✗"


def build_maps() -> dict[str, Any]:
    qa_rows = read_jsonl(BASE / "fredqa_qa_items.jsonl")
    per_var_rows = read_jsonl(BASE / "fredqa_per_variable.jsonl")
    op_rows = read_jsonl(BASE / "opentslm_fredqa_var_captions.jsonl")
    ch_rows = read_jsonl(BASE / "chatts_fredqa_var_captions.jsonl")
    pred_rows = read_jsonl(BASE / "gpt_eval_full_gpt54" / "predictions.jsonl")
    metrics = load_json(BASE / "gpt_eval_full_gpt54" / "metrics.json")
    summary = load_json(BASE / "fredqa_eval_summary.json")

    pred: dict[str, dict[str, dict[str, Any]]] = {}
    for row in pred_rows:
        pred.setdefault(str(row["idx"]), {})[str(row["condition"])] = row

    per_by_qa: dict[str, list[dict[str, Any]]] = {}
    for row in per_var_rows:
        per_by_qa.setdefault(str(row["qa_idx"]), []).append(row)
    for rows in per_by_qa.values():
        rows.sort(key=lambda r: int(r["var_index"]))

    return {
        "qa": {str(r["idx"]): r for r in qa_rows},
        "qa_rows": qa_rows,
        "per_by_qa": per_by_qa,
        "op": {str(r["id"]): str(r["caption"]) for r in op_rows},
        "ch": {str(r["id"]): str(r["caption"]) for r in ch_rows},
        "pred": pred,
        "metrics": metrics,
        "summary": summary,
        "counts": {
            "qa": len(qa_rows),
            "per_var": len(per_var_rows),
            "op": len(op_rows),
            "chatts": len(ch_rows),
            "pred": len(pred_rows),
        },
    }


def plot_case(case_def: dict[str, str], maps: dict[str, Any]) -> str:
    idx = case_def["idx"]
    rows = maps["per_by_qa"][idx]
    nvars = len(rows)
    fname = f"fredqa_{idx}.png"
    path = FIG_DIR / fname
    if path.exists():
        return fname

    setup_matplotlib()
    if nvars == 1:
        fig, axes = plt.subplots(1, 1, figsize=(12, 3.5))
        axes_list = [axes]
        offset = 0
    else:
        fig, axes = plt.subplots(nvars + 1, 1, figsize=(12, 2.25 * (nvars + 1)))
        axes_list = list(np.ravel(axes))
        offset = 1
        ax = axes_list[0]
        for row in rows:
            arr = np.asarray(row["series"], dtype=float)
            std = float(np.std(arr))
            norm = (arr - float(np.mean(arr))) / std if std > 0 else arr - float(np.mean(arr))
            ax.plot(np.arange(len(arr)), norm, linewidth=1.4, label=f"变量 {row['var_index'] + 1}")
        ax.axhline(0, color="#777777", linewidth=0.7, alpha=0.7)
        ax.set_title(f"FREDQA {idx}：归一化叠加图（用于比较跨变量相对变化）")
        ax.set_ylabel("z-score")
        ax.legend(loc="best", ncols=min(nvars, 4), fontsize=8)
        ax.grid(alpha=0.25)

    for i, row in enumerate(rows):
        ax = axes_list[i + offset]
        arr = np.asarray(row["series"], dtype=float)
        x = np.arange(len(arr))
        ax.plot(x, arr, color=f"C{i}", linewidth=1.3)
        amin, amax = int(np.argmin(arr)), int(np.argmax(arr))
        ax.scatter([amin], [arr[amin]], color="#1f77b4", s=24, zorder=3, label=f"min@{amin}")
        ax.scatter([amax], [arr[amax]], color="#d62728", s=24, zorder=3, label=f"max@{amax}")
        stats = trend_summary(row["series"])
        ax.set_title(
            f"变量 {row['var_index'] + 1}: {short_label(row['target_col'], 84)} | "
            f"n={stats['n']}, start={stats['start']:.3g}, end={stats['end']:.3g}"
        )
        ax.set_ylabel("value")
        ax.legend(loc="best", fontsize=8)
        ax.grid(alpha=0.25)
    axes_list[-1].set_xlabel("time index")
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return fname


def plot_overall(maps: dict[str, Any]) -> str:
    setup_matplotlib()
    metrics = maps["summary"]["accuracy"]
    labels = [CONDITION_ZH[c] for c in CONDITIONS]
    vals = [metrics[c]["accuracy"] * 100 for c in CONDITIONS]
    fname = "fredqa_overall_accuracy.png"
    path = FIG_DIR / fname
    fig, ax = plt.subplots(figsize=(11, 4.2))
    bars = ax.bar(range(len(vals)), vals, color=["#4c78a8", "#59a14f", "#f28e2b", "#e15759", "#76b7b2", "#b07aa1"])
    ax.set_ylim(60, 88)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("FREDQA 本轮重跑：六种输入条件总体准确率")
    ax.set_xticks(range(len(vals)), labels, rotation=18, ha="right")
    ax.grid(axis="y", alpha=0.25)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.45, f"{v:.2f}%", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return fname


def plot_heatmap(data: dict[str, Any], rows: list[str], title: str, fname: str) -> str:
    setup_matplotlib()
    vals = np.asarray([[data[r][c]["accuracy"] * 100 for c in CONDITIONS] for r in rows], dtype=float)
    fig, ax = plt.subplots(figsize=(12, max(3.8, 0.55 * len(rows) + 2.2)))
    im = ax.imshow(vals, cmap="YlGnBu", vmin=60, vmax=95, aspect="auto")
    ax.set_xticks(range(len(CONDITIONS)), [CONDITION_ZH[c] for c in CONDITIONS], rotation=20, ha="right")
    row_labels = [ATTRIBUTE_ZH.get(r, f"{r} 变量") for r in rows]
    ax.set_yticks(range(len(rows)), row_labels)
    ax.set_title(title)
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            color = "white" if vals[i, j] > 83 else "#222222"
            ax.text(j, i, f"{vals[i, j]:.1f}", ha="center", va="center", fontsize=8, color=color)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Accuracy (%)")
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / fname, bbox_inches="tight")
    plt.close(fig)
    return fname


def build_translation_payload(case_def: dict[str, str], maps: dict[str, Any]) -> dict[str, Any]:
    idx = case_def["idx"]
    qa = maps["qa"][idx]
    rows = maps["per_by_qa"][idx]
    captions = {"opentslm": {}, "chatts": {}}
    for row in rows:
        vid = str(row["id"])
        vkey = f"var{row['var_index'] + 1}"
        captions["opentslm"][vkey] = maps["op"].get(vid, "")
        captions["chatts"][vkey] = maps["ch"].get(vid, "")
    return {
        "idx": idx,
        "question": qa.get("question", ""),
        "options": qa.get("options", {}),
        "explanation": qa.get("explanation", ""),
        "captions": captions,
    }


def render_accuracy_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| 输入条件 | 正确/总数 | Accuracy | 相对 meta_only | 相对 numbers | 统计含义 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    meta = summary["accuracy"]["meta_only"]["accuracy"]
    numbers = summary["accuracy"]["numbers"]["accuracy"]
    meanings = {
        "meta_only": "只考察题干、选项和领域先验，不应被解释为模型读懂时序。",
        "numbers": "直接给数值后的上限参照；边际增益小，说明长数值输入并没有被稳定利用。",
        "opentslm_caption": "OpenTSLM caption 单独作为证据时低于 meta-only，说明摘要会丢失或扭曲关键信息。",
        "opentslm_caption_plus": "本轮最高，但只比 meta-only 高 1.32 pp，更像轻微辅助而不是可靠证据链。",
        "chatts_caption": "高于 OpenTSLM caption，说明 ChatTS 的简洁形态摘要在部分题上更可用。",
        "chatts_caption_plus": "低于 ChatTS caption-only，说明加入数值并不保证单调提升。",
    }
    for cond in CONDITIONS:
        row = summary["accuracy"][cond]
        lines.append(
            "| "
            + " | ".join(
                [
                    table_cell(CONDITION_ZH[cond]),
                    f"{row['correct']}/{row['n']}",
                    pct(row["accuracy"]),
                    pp(row["accuracy"] - meta),
                    pp(row["accuracy"] - numbers),
                    table_cell(meanings[cond]),
                ]
            )
            + " |"
        )
    return lines


def render_pattern_table(summary: dict[str, Any]) -> list[str]:
    total = summary["n_qa"]
    lines = [
        "| 模式 | 数量 | 占 QA 比例 | 背后含义 | 可能结论 |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    order = [
        "opentslm_wrong_chatts_right",
        "opentslm_right_chatts_wrong",
        "both_caption_wrong_numbers_right",
        "caption_and_numbers_wrong_meta_right",
        "meta_numbers_captions_all_wrong",
        "numbers_rescue_meta_wrong",
        "chatts_rescue_meta_wrong",
        "opentslm_rescue_meta_wrong",
    ]
    implications = {
        "opentslm_wrong_chatts_right": "需要单独分析 caption 生成质量，而不是只看最终 QA accuracy。",
        "opentslm_right_chatts_wrong": "失败不是单向的，训练/评估要保留模型差异。",
        "both_caption_wrong_numbers_right": "当前 caption 训练目标没有对齐 QA 所需的数值抽取。",
        "caption_and_numbers_wrong_meta_right": "FREDQA 中存在语言先验可绕过时序的样本。",
        "meta_numbers_captions_all_wrong": "需要工具计算、公式化中间变量或领域知识增强。",
        "numbers_rescue_meta_wrong": "有一小部分问题确实依赖时序证据，适合做正向 case。",
        "chatts_rescue_meta_wrong": "ChatTS 可作为较强 caption baseline，但仍不稳定。",
        "opentslm_rescue_meta_wrong": "OpenTSLM 的成功 case 数量较少，需要定位其可迁移模式。",
    }
    for key in order:
        title, meaning = PATTERN_ZH[key]
        count = summary["patterns"][key]
        lines.append(
            "| "
            + " | ".join(
                [
                    table_cell(title),
                    str(count),
                    pct(count / total),
                    table_cell(meaning),
                    table_cell(implications[key]),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("注：上述模式不是互斥集合，不能把数量直接相加；例如同一个样本可以同时属于 `numbers_rescue_meta_wrong` 和 `opentslm_wrong_chatts_right`。")
    return lines


def render_nvars_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| 变量数 | 样本数 | meta-only | numbers | OpenTSLM cap | OpenTSLM cap+num | ChatTS cap | ChatTS cap+num | 说明 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    notes = {
        "1": "单变量题 meta-only 最高，说明很多题可由题干和选项先验解决。",
        "2": "ChatTS caption 最高，说明二变量相对关系上简洁 caption 有优势。",
        "3": "所有条件下降，三变量关系开始显著增加证据整合难度。",
        "4": "numbers 明显高于 caption，说明多变量精确计算不适合压缩成通用 caption。",
        "5": "样本少，所有条件一致，暂不做强结论。",
    }
    for nvars in sorted(summary["by_nvars"], key=lambda x: int(x)):
        rows = summary["by_nvars"][nvars]
        sample_n = rows["meta_only"]["n"]
        lines.append(
            "| "
            + " | ".join(
                [
                    nvars,
                    str(sample_n),
                    pct(rows["meta_only"]["accuracy"]),
                    pct(rows["numbers"]["accuracy"]),
                    pct(rows["opentslm_caption"]["accuracy"]),
                    pct(rows["opentslm_caption_plus"]["accuracy"]),
                    pct(rows["chatts_caption"]["accuracy"]),
                    pct(rows["chatts_caption_plus"]["accuracy"]),
                    table_cell(notes.get(nvars, "")),
                ]
            )
            + " |"
        )
    return lines


def render_attribute_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| 问题类型 | 样本数 | meta-only | numbers | OpenTSLM cap | OpenTSLM cap+num | ChatTS cap | ChatTS cap+num | 统计解读 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    notes = {
        "Abductive Reasoning": "整体较高，很多问题可由背景语义和选项排除完成。",
        "Analogical Reasoning": "numbers/caption 都低于 meta-only，说明类比题容易被额外证据干扰。",
        "Causal Reasoning - Associational": "OpenTSLM cap+num 最高，关联型问题更容易从趋势/共变信息获益。",
        "Causal Reasoning - Counterfactual": "全表最难；ChatTS caption-only 最高但 cap+num 下降，反事实计算与证据融合不稳定。",
        "Causal Reasoning - Interventional": "numbers 提升最大，说明干预型题常依赖指定事件前后的精确数值。",
        "Deductive Reasoning": "ChatTS caption 略高，但整体仍受规则执行限制。",
        "Inductive Reasoning": "caption+numbers 略优，归纳型题对形态摘要有一定收益。",
    }
    order = sorted(summary["top_attributes"], key=lambda a: summary["top_attributes"][a]["meta_only"]["n"], reverse=True)
    for attr in order:
        rows = summary["top_attributes"][attr]
        sample_n = rows["meta_only"]["n"]
        lines.append(
            "| "
            + " | ".join(
                [
                    table_cell(f"{ATTRIBUTE_ZH.get(attr, attr)} (`{attr}`)"),
                    str(sample_n),
                    pct(rows["meta_only"]["accuracy"]),
                    pct(rows["numbers"]["accuracy"]),
                    pct(rows["opentslm_caption"]["accuracy"]),
                    pct(rows["opentslm_caption_plus"]["accuracy"]),
                    pct(rows["chatts_caption"]["accuracy"]),
                    pct(rows["chatts_caption_plus"]["accuracy"]),
                    table_cell(notes.get(attr, "")),
                ]
            )
            + " |"
        )
    return lines


def render_case(case_no: int, case_def: dict[str, str], maps: dict[str, Any], translation: dict[str, Any], fig_name: str) -> list[str]:
    idx = case_def["idx"]
    qa = maps["qa"][idx]
    rows = maps["per_by_qa"][idx]
    pred = maps["pred"][idx]
    gold = qa["answer"]
    lengths = [len(r["series"]) for r in rows]
    attrs = qa.get("attributes") or []

    lines: list[str] = []
    lines.append(f"<details>")
    lines.append(f"<summary>📈 Case {case_no:02d}：FREDQA `{idx}` | {md_text(case_def['tag'])}</summary>")
    lines.append("")
    lines.append("### 基本信息")
    lines.append("")
    lines.append("| 字段 | 内容 |")
    lines.append("| --- | --- |")
    lines.append(f"| 数据集 | `FREDQA` |")
    lines.append(f"| Case ID | `fredqa::{idx}` |")
    lines.append(f"| FREDQA 原始 idx | `{idx}` |")
    lines.append(f"| 变量数 / 序列长度 | `{len(rows)}` / `{lengths}` |")
    lines.append(f"| 问题类型 | {table_cell(', '.join(f'`{a}`' for a in attrs))} |")
    lines.append(f"| 正确答案 | `{gold}` |")
    lines.append(f"| 失败/对比模式 | {table_cell(case_def['tag'])} |")
    lines.append(f"| 本 case 关注点 | {table_cell(case_def['focus'])} |")
    lines.append("")
    lines.append("变量摘要：")
    lines.append("")
    lines.append("| 变量 | 指标名 | n | start | end | min@idx | max@idx | slope |")
    lines.append("| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |")
    for row in rows:
        stats = trend_summary(row["series"])
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["var_index"] + 1),
                    table_cell(row["target_col"]),
                    str(stats["n"]),
                    f"{stats['start']:.6g}",
                    f"{stats['end']:.6g}",
                    f"{stats['min']:.6g}@{stats['argmin']}",
                    f"{stats['max']:.6g}@{stats['argmax']}",
                    f"{stats['slope']:.6g}",
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append("<details>")
    lines.append("<summary>🖼 时序图</summary>")
    lines.append("")
    lines.append(f"![FREDQA {idx}]({GITHUB_RAW_BASE}/{fig_name})")
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary>❓ QA 问题与中文翻译</summary>")
    lines.append("")
    lines.append("**题干原文**")
    lines.append("")
    lines.append(quote_block(qa.get("question", "")))
    lines.append("")
    lines.append("**题干中文翻译**")
    lines.append("")
    lines.append(quote_block(translation.get("question", "")))
    lines.append("")
    lines.append("**选项**")
    lines.append("")
    lines.append("| 选项 | 原文 | 中文翻译 |")
    lines.append("| --- | --- | --- |")
    opt_zh = translation.get("options", {}) if isinstance(translation.get("options"), dict) else {}
    for letter in sorted(qa.get("options", {})):
        lines.append(
            f"| `{letter}` | {table_cell(qa['options'][letter])} | {table_cell(opt_zh.get(letter, ''))} |"
        )
    lines.append("")
    lines.append(f"**正确答案**：`{gold}`")
    lines.append("")
    lines.append("**标准解释原文**")
    lines.append("")
    lines.append(quote_block(qa.get("explanation", "")))
    lines.append("")
    lines.append("**标准解释中文翻译**")
    lines.append("")
    lines.append(quote_block(translation.get("explanation", "")))
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary>📝 生成的 caption 与中文翻译</summary>")
    lines.append("")
    captions_zh = translation.get("captions", {}) if isinstance(translation.get("captions"), dict) else {}
    op_zh = captions_zh.get("opentslm", {}) if isinstance(captions_zh.get("opentslm"), dict) else {}
    ch_zh = captions_zh.get("chatts", {}) if isinstance(captions_zh.get("chatts"), dict) else {}
    for row in rows:
        vid = str(row["id"])
        vkey = f"var{row['var_index'] + 1}"
        lines.append(f"#### 变量 {row['var_index'] + 1}：{md_text(row['target_col'])}")
        lines.append("")
        lines.append("**OpenTSLM caption 原文**")
        lines.append("")
        lines.append(quote_block(maps["op"].get(vid, "")))
        lines.append("")
        lines.append("**OpenTSLM caption 中文翻译**")
        lines.append("")
        lines.append(quote_block(op_zh.get(vkey, "")))
        lines.append("")
        lines.append("**ChatTS caption 原文**")
        lines.append("")
        lines.append(quote_block(maps["ch"].get(vid, "")))
        lines.append("")
        lines.append("**ChatTS caption 中文翻译**")
        lines.append("")
        lines.append(quote_block(ch_zh.get(vkey, "")))
        lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary>🧪 下游 QA 模型答案 / 评分</summary>")
    lines.append("")
    lines.append("表中所有预测都是同一个辅助 QA 模型 `gpt-5.4` 的输出；六行只改变输入证据形式。")
    lines.append("")
    lines.append("| 输入条件 | 预测答案 | Gold | 是否正确 | 模型原始输出 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for cond in CONDITIONS:
        row = pred[cond]
        lines.append(
            "| "
            + " | ".join(
                [
                    table_cell(f"{CONDITION_ZH[cond]} (`{cond}`)"),
                    f"`{row.get('pred', '')}`",
                    f"`{row.get('gold', '')}`",
                    f"{result_icon(bool(row.get('correct')))} {result_mark(bool(row.get('correct')))}",
                    table_cell(row.get("raw", "")),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("</details>")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary>🔎 Case 分析</summary>")
    lines.append("")
    cond_result = ", ".join(
        f"{cond}={pred[cond]['pred']}{result_icon(bool(pred[cond]['correct']))}" for cond in CONDITIONS
    )
    lines.append(f"- **答案格局**：`{cond_result}`。")
    lines.append(f"- **关键问题**：{md_text(case_def['why'])}")
    lines.append("- **对训练失败的含义**：这类 case 显示，当前 caption 训练更像是在学习通用趋势/峰谷/波动模板，而不是学习“下游 QA 所需的证据提取”。FREDQA 的正确答案经常依赖指定日期、指定窗口、比值、差值、反事实外推或领域机制；这些信息如果没有被 caption 明确保留，下游 GPT 即使很强也只能依赖题干先验或被错误摘要带偏。")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return lines


def render_report(maps: dict[str, Any], translations: dict[str, Any], figure_names: dict[str, str], stats_figs: dict[str, str]) -> str:
    summary = maps["summary"]
    counts = maps["counts"]
    lines: list[str] = []
    lines.append("# FREDQA 重跑统计与 Case Study 中文报告")
    lines.append("")
    lines.append("本报告基于当前这一轮 FREDQA 重跑结果生成，正文为中文；原始 QA、OpenTSLM caption、ChatTS caption 和辅助 QA 模型输出保留英文原文，并提供中文翻译用于组会/导师讨论。")
    lines.append("")
    lines.append("## 实验范围与读取方式")
    lines.append("")
    lines.append(f"- QA 样本数：`{counts['qa']}`。")
    lines.append(f"- 变量级 caption 样本数：`{counts['per_var']}`；OpenTSLM caption `{counts['op']}` 条，ChatTS caption `{counts['chatts']}` 条。")
    lines.append(f"- GPT QA 预测数：`{counts['pred']}`，对应 `604 × 6` 个条件。")
    lines.append("- 下游 QA 辅助模型是 `gpt-5.4`；`meta_only`、`numbers`、`opentslm_caption`、`chatts_caption` 等只是输入证据不同，不是不同 QA 模型。")
    lines.append("- 本轮完整重跑覆盖的是 `FREDQA`；之前的多数据集 case study 仍在 `docs/case-studies/20260511-balanced-zh/`，本报告不把其他数据集旧 artifact 混入本轮统计。")
    lines.append("- 关键统计模式不是互斥集合，因此模式计数用于定位现象，不能直接相加成总失败数。")
    lines.append("")

    lines.append("## 统计图")
    lines.append("")
    lines.append(f"![总体准确率]({GITHUB_RAW_BASE}/{stats_figs['overall']})")
    lines.append("")
    lines.append(f"![按问题类型准确率]({GITHUB_RAW_BASE}/{stats_figs['attribute']})")
    lines.append("")
    lines.append(f"![按变量数准确率]({GITHUB_RAW_BASE}/{stats_figs['nvars']})")
    lines.append("")

    lines.append("## 总体准确率")
    lines.append("")
    lines.extend(render_accuracy_table(summary))
    lines.append("")
    lines.append("**直接结论**：最高条件是 `opentslm_caption_plus`，准确率 82.28%，但只比 `meta_only` 高 1.32 个百分点。`opentslm_caption` 单独低于 `meta_only`，说明当前 OpenTSLM caption 作为下游 QA 证据并不可靠；`ChatTS caption` 更高，但加入数值后也会下降，说明 evidence fusion 本身不稳定。")
    lines.append("")

    lines.append("## 关键错误模式")
    lines.append("")
    lines.extend(render_pattern_table(summary))
    lines.append("")

    lines.append("## 按变量数分类")
    lines.append("")
    lines.extend(render_nvars_table(summary))
    lines.append("")

    lines.append("## 按问题类型分类")
    lines.append("")
    lines.extend(render_attribute_table(summary))
    lines.append("")

    lines.append("## Case Study")
    lines.append("")
    lines.append("下面每个 case 都包含时序图、原始 QA 与中文翻译、OpenTSLM/ChatTS 生成 caption 与中文翻译、六种输入条件下的 `gpt-5.4` 回答，以及对应分析。")
    lines.append("")
    for i, case_def in enumerate(CASE_DEFS, 1):
        lines.extend(render_case(i, case_def, maps, translations[case_def["idx"]], figure_names[case_def["idx"]]))

    lines.append("## 全局 Case Study 分析")
    lines.append("")
    lines.append("1. **FREDQA 的高 `meta_only` 准确率说明它并不纯粹是时序读取任务。** `meta_only` 已经达到 80.96%，很多样本可以由题干、选项和领域常识先验直接排除。这意味着只看总体 QA accuracy 会高估模型从时间序列中提取证据的能力。")
    lines.append("")
    lines.append("2. **当前 caption 训练失败的核心不是“语言不够流畅”，而是“证据不够任务化”。** OpenTSLM 和 ChatTS 大多能生成趋势、峰谷、波动、季节性等描述，但 FREDQA 经常需要指定月份/年份、窗口均值、比值、差值、反事实外推、干预前后比较，以及制度/宏观机制解释。通用 caption 没有保证这些证据被保留。")
    lines.append("")
    lines.append("3. **OpenTSLM caption 的模板化问题更明显。** 多个 case 中 OpenTSLM 会重复生成 “steady upward trend / low volatility / strong seasonal pattern” 一类描述，即使问题真正需要局部日期计算。这会把 QA 模型从正确的局部证据带向全局形态概括。")
    lines.append("")
    lines.append("4. **ChatTS 更简洁，但不是稳定上限。** ChatTS caption 在 `opentslm_wrong_chatts_right` 和 counterfactual 类型中有一些优势，但 `chatts_caption_plus` 低于 `chatts_caption`，说明一旦同时给数值，QA 模型可能重新加权证据并被干扰。")
    lines.append("")
    lines.append("5. **`numbers` 不是可靠 oracle。** `numbers` 只比 `meta_only` 高 1.16 个百分点，而且仍有大量反事实/公式化样本答错。这说明长数值输入本身并不会自动转化为正确计算；后续如果目标是可靠 QA，可能需要显式工具或结构化中间变量。")
    lines.append("")
    lines.append("6. **对导师讨论最重要的结论**：目前训练路线没有失败在“caption 不能描述时序”，而是失败在“caption 没有按下游问题需要组织证据”。下一步应把 caption 目标从通用描述改成 task-aware evidence extraction，例如保留指定日期值、窗口统计、跨变量差/比值、反事实公式中间量，或让工具先计算这些中间量再交给 LLM 解释。")
    lines.append("")
    lines.append("## 建议下一步")
    lines.append("")
    lines.append("- 建一个 FREDQA evidence schema：每条 caption 不只写趋势，还必须写出题目中出现的日期/窗口/变量对应的数值、差值、比值和排序。")
    lines.append("- 对 `both_caption_wrong_numbers_right` 的 13 个样本做 targeted caption 改写实验，验证只补充局部证据是否能救回 QA。")
    lines.append("- 对 `meta_numbers_captions_all_wrong` 的 79 个样本拆分错误来源：公式执行失败、领域知识缺失、长题干定位失败、选项干扰。")
    lines.append("- 增加一个 tool-assisted baseline：先从题目抽取需要计算的日期/窗口，再用 Python 计算中间量，最后让 LLM 只做解释和选项匹配。")
    lines.append("")
    return "\n".join(lines) + "\n"


def to_notion_markdown(report: str) -> str:
    """Convert GitHub details blocks to a flat Notion-friendly heading layout."""
    out: list[str] = []
    for line in report.splitlines():
        stripped = line.strip()
        if stripped == "<details>" or stripped == "</details>":
            continue
        match = re.fullmatch(r"<summary>(.*)</summary>", stripped)
        if match:
            title = match.group(1).strip()
            if title.startswith("📈 Case"):
                out.append(f"## {title}")
            elif title.startswith(("🖼", "❓", "📝", "🧪", "🔎")):
                out.append(f"### {title}")
            else:
                out.append(f"### {title}")
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def main() -> None:
    setup_matplotlib()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    maps = build_maps()

    missing = [c["idx"] for c in CASE_DEFS if c["idx"] not in maps["qa"]]
    if missing:
        raise RuntimeError(f"selected cases missing from QA rows: {missing}")

    stats_figs = {
        "overall": plot_overall(maps),
        "attribute": plot_heatmap(
            maps["summary"]["top_attributes"],
            sorted(
                maps["summary"]["top_attributes"],
                key=lambda a: maps["summary"]["top_attributes"][a]["meta_only"]["n"],
                reverse=True,
            ),
            "FREDQA 本轮重跑：按问题类型的准确率",
            "fredqa_by_attribute_accuracy.png",
        ),
        "nvars": plot_heatmap(
            maps["summary"]["by_nvars"],
            sorted(maps["summary"]["by_nvars"], key=lambda x: int(x)),
            "FREDQA 本轮重跑：按变量数的准确率",
            "fredqa_by_nvars_accuracy.png",
        ),
    }
    figure_names = {case["idx"]: plot_case(case, maps) for case in CASE_DEFS}

    chat_fn = load_translation_client()
    cache = load_cache()
    translations: dict[str, Any] = {}
    for case in CASE_DEFS:
        payload = build_translation_payload(case, maps)
        translations[case["idx"]] = translate_case(payload, cache, chat_fn)
        print(f"[ok] translation ready for FREDQA {case['idx']}")

    report = render_report(maps, translations, figure_names, stats_figs)
    REPORT.write_text(report, encoding="utf-8")
    NOTION_REPORT.write_text(to_notion_markdown(report), encoding="utf-8")
    write_json(
        MANIFEST,
        {
            "source_dir": str(BASE),
            "report": str(REPORT),
            "notion_report": str(NOTION_REPORT),
            "github_branch": GITHUB_BRANCH,
            "github_raw_base": GITHUB_RAW_BASE,
            "selected_cases": CASE_DEFS,
            "figures": {**stats_figs, **figure_names},
            "counts": maps["counts"],
            "summary_accuracy": maps["summary"]["accuracy"],
            "summary_patterns": maps["summary"]["patterns"],
        },
    )
    print(f"[done] wrote {REPORT}")
    print(f"[done] wrote {NOTION_REPORT}")
    print(f"[done] wrote {MANIFEST}")


if __name__ == "__main__":
    main()
