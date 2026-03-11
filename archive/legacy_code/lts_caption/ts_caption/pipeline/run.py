# ts_caption/pipeline/run.py
from __future__ import annotations
import json
from typing import List, Optional, Iterator, Tuple, Any
import numpy as np
import pandas as pd

from ts_caption.datasets.base import DatasetAdapter
from ts_caption.pipeline.windowing import generate_windows
from ts_caption.pipeline.analyze import analyze_window, build_features
from ts_caption.claims.builder import build_claims
from ts_caption.claims.validator import validate_claims
from ts_caption.claims.policy import apply_claim_policy
from ts_caption.claims.consistency import apply_consistency_rules
# from ts_caption.claims.budget import apply_budget_policy
from ts_caption.claims.renderer_zh import render_caption_zh, stable_seed


# ---------- helpers: multi-series compatible ----------
def _iter_series_compat(adapter: DatasetAdapter, csv_path: str) -> Iterator[Tuple[str, pd.DataFrame]]:
    """
    兼容两类 iter_series 返回：
      1) yield (series_key, df)
      2) yield obj with .series_key and .df
    若没有 iter_series，则把 csv_path 当作单文件。
    """
    if hasattr(adapter, "iter_series"):
        it = adapter.iter_series(csv_path)
        for item in it:
            if isinstance(item, tuple) and len(item) == 2:
                yield str(item[0]), item[1]
            else:
                key = getattr(item, "series_key", "series_0")
                df = getattr(item, "df", None)
                if df is None:
                    raise ValueError("iter_series returned an object without .df")
                yield str(key), df
        return

    # fallback: single series
    df = adapter.load_dataframe(csv_path)
    yield "series_0", df


def build_variable_meta(
    series_cols: List[str],
    target_col: str,
    var_info_map,
    series_meaning_zh: Optional[str] = None,
) -> List[dict]:
    out = []
    for idx, col in enumerate(series_cols):
        info = var_info_map.get(col)
        meaning = getattr(info, "meaning_zh", col) if info else col
        unit = getattr(info, "unit", None) if info else None

        # ✅ NAB 常见：单变量 value 的语义随文件变化，可在这里覆盖
        if series_meaning_zh and len(series_cols) == 1 and col == target_col:
            meaning = series_meaning_zh

        out.append({
            "name": col,
            "index": idx,
            "role": "target" if col == target_col else "feature",
            "meaning_zh": meaning,
            "unit": unit,
        })
    return out


def build_intro(series_cols: List[str], target_col: str, var_info_map, series_desc: Optional[str] = None) -> str:
    items = []
    for col in series_cols:
        info = var_info_map.get(col)
        meaning = getattr(info, "meaning_zh", col) if info else col
        items.append(f"{col}（{meaning}）")
    vars_str = ", ".join(items)

    # ✅ 单变量时不写“其它 0 个变量”
    if len(series_cols) == 1:
        base = f"本序列为单变量时间序列：{vars_str}。以下描述该指标的整体走势、阶段变化与关键波动。"
    else:
        base = f"本窗口包含变量：{vars_str}。以下主要描述 {target_col} 的模式与关联。"

    if series_desc:
        return f"{series_desc} {base}"
    return base


def run_pipeline(
    adapter: DatasetAdapter,
    csv_path: str,                # 对 NAB：可以是目录（data 或子目录）或单文件
    output_jsonl: str,
    dataset_name: str,
    task: str,
    window_len: int,
    stride: int,
    target_col: str,
    series_cols: List[str],
    max_windows: Optional[int],
    label_col: Optional[str],
    label_mode: str,
    constant_class: Optional[str],
    enforce_claims: bool = True,
    caption_style: str = "human",
):
    time_col = adapter.time_col()
    var_info = adapter.get_variable_info()

    with open(output_jsonl, "w", encoding="utf-8") as f:
        # ✅ 遍历每个 csv（每个文件是一条序列）
        for series_key, df in _iter_series_compat(adapter, csv_path):
            # --- 列检查 ---
            for c in [time_col] + series_cols:
                if c not in df.columns:
                    raise ValueError(f"[{series_key}] Column '{c}' not found in series data.")

            df = df[[time_col] + series_cols + ([label_col] if label_col and label_col in df.columns else [])].copy()

            # ✅ 目标：每个文件只生成 1 个 caption
            wl = window_len
            if wl <= 0 or wl > len(df):
                wl = len(df)

            # --- NAB: series 语义（可选） ---
            series_desc_txt = None
            series_meaning_zh = None
            if hasattr(adapter, "describe_series"):
                try:
                    sd = adapter.describe_series(series_key)
                    series_desc_txt = f"该序列来自 {dataset_name}：{getattr(sd, 'key', series_key)}，语义为“{getattr(sd, 'meaning_zh', '')}”。"
                    series_meaning_zh = getattr(sd, "meaning_zh", None)
                except Exception:
                    pass

            # ✅ 窗口循环：必须在 series 循环内部
            for meta, win_df in generate_windows(
                df,
                time_col=time_col,
                window_len=wl,
                stride=stride,
                max_windows=max_windows,
            ):
                x_target = win_df[target_col].to_numpy(float)
                time_list = win_df[time_col].dt.strftime("%Y-%m-%d %H:%M").tolist()

                summary = analyze_window(meta, win_df, time_col=time_col, target_col=target_col, series_cols=series_cols)
                features = build_features(summary, x_target, target_col=target_col)

                vol_lab = features["volatility"]
                claims = build_claims(summary, target_col, x_target, time_list, vol_lab)

                check_before = validate_claims(
                    claims,
                    win_df[[time_col] + series_cols].copy(),
                    time_col=time_col
                )

                # validate_claims() 内部已经 apply_consistency_rules 过了，这里不要重复
                claims = apply_claim_policy(claims, enforce=enforce_claims)

                # ✅ 再对“最终保留下来的 claims”做一次 check，便于后续评测一致
                check_after = validate_claims(
                    claims,
                    win_df[[time_col] + series_cols].copy(),
                    time_col=time_col
                )

                # 同步趋势回 features
                trend_claim = next((c for c in claims if c.type == "global_trend_label"), None)
                if trend_claim is not None:
                    features["trend"] = (trend_claim.data or {}).get("label_final") or (trend_claim.data or {}).get("label") or features["trend"]

                # ✅ caption（每样本 1 条；跨样本多样化：seed 混入 series_key）
                variables_meta = build_variable_meta(series_cols, target_col, var_info, series_meaning_zh=series_meaning_zh)
                intro = build_intro(series_cols, target_col, var_info, series_desc=series_desc_txt)

                seed = stable_seed(
                    dataset_name,
                    series_key,
                    meta.global_start_idx,
                    meta.global_end_idx,
                    target_col,
                )

                caption_body = render_caption_zh(
                    claims=claims,
                    variables=variables_meta,
                    target_col=target_col,
                    seed=seed,
                    include_vars_intro=False,      # 如果你的 render_caption_zh 支持
                )
                caption = intro + " " + caption_body

                timeseries = win_df[series_cols].to_numpy(float).tolist()

                # ✅ label：对 NAB 最好传 series_key；兼容旧签名
                try:
                    label = adapter.build_label(
                        win_df,
                        label_col=label_col,
                        label_mode=label_mode,
                        constant_class=constant_class,
                        series_key=series_key,
                    )
                except TypeError:
                    label = adapter.build_label(
                        win_df,
                        label_col=label_col,
                        label_mode=label_mode,
                        constant_class=constant_class,
                    )

                record = {
                    "dataset": dataset_name,
                    "task": task,
                    "series_key": series_key,  # ✅ NAB 强烈建议保留，后续对齐真值/回溯文件都靠它
                    "window_length": meta.length,
                    "indices": [meta.global_start_idx, meta.global_end_idx],
                    "time": time_list,
                    "timeseries": timeseries,
                    "variables": variables_meta,
                    "label": label,
                    "features": features,
                    "descriptions": [caption],   # 仍然只 1 条
                    "claims": [c.to_dict() for c in claims],
                    "claim_check": check_after
                    ,
                }

                f.write(json.dumps(record, ensure_ascii=False) + "\n")

                # wl=len(df) 时理论上只会产一个窗口；保险：如果你还担心可 break
                if wl == len(df):
                    break
