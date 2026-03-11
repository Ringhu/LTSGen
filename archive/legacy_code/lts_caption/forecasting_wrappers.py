# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd

from ts_caption_core import SampleInput


# -----------------------------
# Dataset context & column semantics (forecasting)
# -----------------------------

ETT_VAR_MEANING_ZH = {
    "OT": "油温（Oil Temperature）",
    "HUFL": "高负荷有用负载",
    "HULL": "高负荷无用负载",
    "MUFL": "中负荷有用负载",
    "MULL": "中负荷无用负载",
    "LUFL": "低负荷有用负载",
    "LULL": "低负荷无用负载",
}

EXRATE_COUNTRIES_8 = [
    ("Australia", "澳大利亚"),
    ("Britain", "英国"),
    ("Canada", "加拿大"),
    ("Switzerland", "瑞士"),
    ("China", "中国"),
    ("Japan", "日本"),
    ("New Zealand", "新西兰"),
    ("Singapore", "新加坡"),
]

ILLNESS_MEANING_ZH = {
    "% WEIGHTED ILI": "加权 ILI 就诊占比（wILI）",
    "%UNWEIGHTED ILI": "未加权 ILI 就诊占比",
    "AGE 0-4": "0–4 岁 ILI 相关计数",
    "AGE 5-24": "5–24 岁 ILI 相关计数",
    "ILITOTAL": "ILI 总计数/总量",
    "NUM. OF PROVIDERS": "上报医疗机构数量",
    "OT": "目标列（有些打包版用 OT 作为 target 占位名）",
}

WEATHER_HINTS_ZH = {
    "p (mbar)": "气压（mbar）",
    "T (degC)": "气温（°C）",
    "Tpot (K)": "位温（K）",
    "Tdew (degC)": "露点温度（°C）",
    "rh (%)": "相对湿度（%）",
    "wv (m/s)": "风速（m/s）",
    "max. wv (m/s)": "最大风速（m/s）",
    "wd (deg)": "风向角（deg）",
    "OT": "目标列（打包版常用 OT 作为 target 占位名）",
}

DATASET_CONTEXT_ZH = {
    "ett": (
        "背景：电力变压器运行监测数据，用于预测油温（OT），并研究长序列预测。"
        "列含义固定：HUFL/HULL/MUFL/MULL/LUFL/LULL 为不同负载，OT 为油温。"
    ),
    "electricity": (
        "背景：多用户/多节点用电量序列（常见为由 15min 重采样到小时级）。"
        "除 date 外每一列通常对应一个客户/站点的用电量序列；若出现 OT，多为预处理后选作 target 的占位名。"
    ),
    "traffic": (
        "背景：道路网络多传感器数据（常见为小时级）。"
        "除 date 外每一列通常对应一个道路传感器的 occupancy rate（道路占有率）序列；若出现 OT，多为 target 占位名。"
    ),
    "exchange_rate": (
        "背景：8 个国家/地区的日度外汇汇率序列（多变量）。"
        "常见为 8 列数值（可能没有 date），每列对应一个国家/地区的汇率。"
    ),
    "illness": (
        "背景：ILI（Influenza-Like Illness）周频监测数据，用于预测流感样病例活动水平。"
        "列包含 wILI、分年龄段计数、总量、上报机构数等。"
    ),
    "weather": (
        "背景：德国 Jena 气象站多变量观测（常见为 10 分钟采样），用于多变量预测。"
        "列为气温/气压/湿度/风速风向等；若出现 OT，多为 target 占位名。"
    ),
}


# -----------------------------
# Common wrapper helpers
# -----------------------------

def _default_time_strings(T: int) -> List[str]:
    return [f"t{i}" for i in range(T)]


def _read_csv_strip(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _infer_date_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = set(df.columns)
    for c in candidates:
        if c in cols:
            return c
    return None


def _ensure_numeric_df(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=cols).reset_index(drop=True)
    return out


def _iter_windows_indices(n: int, window_len: Optional[int], stride: Optional[int], max_samples: Optional[int]) -> Iterator[Tuple[int, int]]:
    # window_len<=0 or None or >=n: treat whole series as one sample
    if window_len is None or window_len <= 0 or window_len >= n:
        yield 0, n
        return

    st = int(stride or window_len)
    produced = 0
    for i in range(0, n - window_len + 1, st):
        if max_samples is not None and produced >= max_samples:
            break
        yield i, i + window_len
        produced += 1


# -----------------------------
# 6 forecasting wrappers
# -----------------------------

def iter_samples_ett(
    csv_path: str,
    dataset_name: str,
    series_key: str = "series_0",
    target_col: str = "OT",
    series_cols: Optional[List[str]] = None,
    window_len: Optional[int] = 512,
    stride: Optional[int] = 256,
    max_samples: Optional[int] = None,
) -> Iterator[SampleInput]:
    df = _read_csv_strip(csv_path)
    if "date" not in df.columns:
        raise ValueError("ETT expects a 'date' column.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).reset_index(drop=True)

    if series_cols is None:
        series_cols = [c for c in df.columns if c != "date"]
    if target_col not in series_cols:
        target_col = series_cols[0]

    df = _ensure_numeric_df(df, series_cols)
    time_all = df["date"].dt.strftime("%Y-%m-%d %H:%M").astype(str).tolist()

    col_meaning = dict(ETT_VAR_MEANING_ZH)
    for c in series_cols:
        col_meaning.setdefault(c, c)

    for s, e in _iter_windows_indices(len(df), window_len, stride, max_samples):
        win = df.iloc[s:e].reset_index(drop=True)
        yield SampleInput(
            dataset="ett",
            dataset_name=dataset_name,
            task="forecasting",
            series_key=series_key,
            time=time_all[s:e],
            values=win[series_cols].to_numpy(float),
            series_cols=series_cols,
            target_col=target_col,
            label=None,
            domain_context_zh=DATASET_CONTEXT_ZH["ett"],
            col_meaning_zh=col_meaning,
        )


def iter_samples_electricity(
    csv_path: str,
    dataset_name: str,
    series_key: str = "series_0",
    target_col: Optional[str] = None,
    series_cols: Optional[List[str]] = None,
    max_cols: int = 8,
    window_len: Optional[int] = 512,
    stride: Optional[int] = 256,
    max_samples: Optional[int] = None,
) -> Iterator[SampleInput]:
    df = _read_csv_strip(csv_path)
    date_col = _infer_date_col(df, ["date", "Date", "datetime", "timestamp", "Date Time"])
    if date_col is None:
        raise ValueError("electricity expects a timestamp column like 'date'.")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).reset_index(drop=True)

    if series_cols is None:
        series_cols = [c for c in df.columns if c != date_col]
        if len(series_cols) > max_cols:
            series_cols = series_cols[:max_cols]

    df = _ensure_numeric_df(df, series_cols)
    time_all = df[date_col].dt.strftime("%Y-%m-%d %H:%M").astype(str).tolist()

    if target_col is None:
        target_col = "OT" if "OT" in series_cols else series_cols[0]

    col_meaning = {c: f"用电量序列（节点/客户：{c}）" for c in series_cols}
    if "OT" in col_meaning:
        col_meaning["OT"] = "目标列（常为预处理后选作预测目标的用电量列）"

    for s, e in _iter_windows_indices(len(df), window_len, stride, max_samples):
        win = df.iloc[s:e].reset_index(drop=True)
        yield SampleInput(
            dataset="electricity",
            dataset_name=dataset_name,
            task="forecasting",
            series_key=series_key,
            time=time_all[s:e],
            values=win[series_cols].to_numpy(float),
            series_cols=series_cols,
            target_col=target_col,
            label=None,
            domain_context_zh=DATASET_CONTEXT_ZH["electricity"],
            col_meaning_zh=col_meaning,
        )


def iter_samples_traffic(
    csv_path: str,
    dataset_name: str,
    series_key: str = "series_0",
    target_col: Optional[str] = None,
    series_cols: Optional[List[str]] = None,
    max_cols: int = 8,
    window_len: Optional[int] = 512,
    stride: Optional[int] = 256,
    max_samples: Optional[int] = None,
) -> Iterator[SampleInput]:
    df = _read_csv_strip(csv_path)
    date_col = _infer_date_col(df, ["date", "Date", "datetime", "timestamp", "Date Time"])
    if date_col is None:
        raise ValueError("traffic expects a timestamp column like 'date'.")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).reset_index(drop=True)

    if series_cols is None:
        series_cols = [c for c in df.columns if c != date_col]
        if len(series_cols) > max_cols:
            series_cols = series_cols[:max_cols]

    df = _ensure_numeric_df(df, series_cols)
    time_all = df[date_col].dt.strftime("%Y-%m-%d %H:%M").astype(str).tolist()

    if target_col is None:
        target_col = "OT" if "OT" in series_cols else series_cols[0]

    col_meaning = {c: f"道路占有率序列（传感器：{c}）" for c in series_cols}
    if "OT" in col_meaning:
        col_meaning["OT"] = "目标列（常为预处理后选作预测目标的传感器占有率列）"

    for s, e in _iter_windows_indices(len(df), window_len, stride, max_samples):
        win = df.iloc[s:e].reset_index(drop=True)
        yield SampleInput(
            dataset="traffic",
            dataset_name=dataset_name,
            task="forecasting",
            series_key=series_key,
            time=time_all[s:e],
            values=win[series_cols].to_numpy(float),
            series_cols=series_cols,
            target_col=target_col,
            label=None,
            domain_context_zh=DATASET_CONTEXT_ZH["traffic"],
            col_meaning_zh=col_meaning,
        )


def iter_samples_exchange_rate(
    csv_path: str,
    dataset_name: str,
    series_key: str = "series_0",
    target_col: Optional[str] = None,
    series_cols: Optional[List[str]] = None,
    window_len: Optional[int] = 512,
    stride: Optional[int] = 256,
    max_samples: Optional[int] = None,
) -> Iterator[SampleInput]:
    df = _read_csv_strip(csv_path)

    date_col = _infer_date_col(df, ["date", "Date", "datetime", "timestamp", "Date Time"])
    if date_col is not None:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col]).reset_index(drop=True)
        time_all = df[date_col].dt.strftime("%Y-%m-%d").astype(str).tolist()
        num_cols = [c for c in df.columns if c != date_col]
    else:
        num_cols = df.columns.tolist()
        time_all = _default_time_strings(len(df))

    if series_cols is None:
        series_cols = num_cols

    df = _ensure_numeric_df(df, series_cols)

    if target_col is None:
        target_col = "OT" if "OT" in series_cols else series_cols[0]

    col_meaning: Dict[str, str] = {}
    if len(series_cols) == 8:
        for c, (_, zh) in zip(series_cols, EXRATE_COUNTRIES_8):
            col_meaning[c] = f"外汇汇率（{zh}）"
    else:
        for c in series_cols:
            col_meaning[c] = f"外汇汇率序列（{c}）"
    if "OT" in col_meaning:
        col_meaning["OT"] = "目标列（常为预处理后选作预测目标的汇率列）"

    for s, e in _iter_windows_indices(len(df), window_len, stride, max_samples):
        win = df.iloc[s:e].reset_index(drop=True)
        yield SampleInput(
            dataset="exchange_rate",
            dataset_name=dataset_name,
            task="forecasting",
            series_key=series_key,
            time=time_all[s:e],
            values=win[series_cols].to_numpy(float),
            series_cols=series_cols,
            target_col=target_col,
            label=None,
            domain_context_zh=DATASET_CONTEXT_ZH["exchange_rate"],
            col_meaning_zh=col_meaning,
        )


def iter_samples_illness(
    csv_path: str,
    dataset_name: str,
    series_key: str = "series_0",
    target_col: Optional[str] = None,
    series_cols: Optional[List[str]] = None,
    window_len: Optional[int] = 104,
    stride: Optional[int] = 52,
    max_samples: Optional[int] = None,
) -> Iterator[SampleInput]:
    df = _read_csv_strip(csv_path)
    if "date" not in df.columns:
        raise ValueError("illness expects a 'date' column.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).reset_index(drop=True)

    if series_cols is None:
        series_cols = [c for c in df.columns if c != "date"]

    df = _ensure_numeric_df(df, series_cols)
    time_all = df["date"].dt.strftime("%Y-%m-%d").astype(str).tolist()

    if target_col is None:
        target_col = "OT" if "OT" in series_cols else series_cols[0]

    col_meaning = {c: ILLNESS_MEANING_ZH.get(c, c) for c in series_cols}

    for s, e in _iter_windows_indices(len(df), window_len, stride, max_samples):
        win = df.iloc[s:e].reset_index(drop=True)
        yield SampleInput(
            dataset="illness",
            dataset_name=dataset_name,
            task="forecasting",
            series_key=series_key,
            time=time_all[s:e],
            values=win[series_cols].to_numpy(float),
            series_cols=series_cols,
            target_col=target_col,
            label=None,
            domain_context_zh=DATASET_CONTEXT_ZH["illness"],
            col_meaning_zh=col_meaning,
        )


def iter_samples_weather(
    csv_path: str,
    dataset_name: str,
    series_key: str = "series_0",
    target_col: Optional[str] = None,
    series_cols: Optional[List[str]] = None,
    window_len: Optional[int] = 1024,
    stride: Optional[int] = 512,
    max_samples: Optional[int] = None,
) -> Iterator[SampleInput]:
    df = _read_csv_strip(csv_path)
    date_col = _infer_date_col(df, ["date", "Date Time", "datetime", "timestamp", "Date"])
    if date_col is None:
        raise ValueError("weather expects a timestamp column like 'date' or 'Date Time'.")

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).reset_index(drop=True)

    if series_cols is None:
        series_cols = [c for c in df.columns if c != date_col]

    df = _ensure_numeric_df(df, series_cols)
    time_all = df[date_col].dt.strftime("%Y-%m-%d %H:%M").astype(str).tolist()

    if target_col is None:
        if "T (degC)" in series_cols:
            target_col = "T (degC)"
        elif "OT" in series_cols:
            target_col = "OT"
        else:
            target_col = series_cols[0]

    col_meaning = {c: WEATHER_HINTS_ZH.get(c, c) for c in series_cols}

    for s, e in _iter_windows_indices(len(df), window_len, stride, max_samples):
        win = df.iloc[s:e].reset_index(drop=True)
        yield SampleInput(
            dataset="weather",
            dataset_name=dataset_name,
            task="forecasting",
            series_key=series_key,
            time=time_all[s:e],
            values=win[series_cols].to_numpy(float),
            series_cols=series_cols,
            target_col=target_col,
            label=None,
            domain_context_zh=DATASET_CONTEXT_ZH["weather"],
            col_meaning_zh=col_meaning,
        )


WRAPPER_REGISTRY = {
    "ett": iter_samples_ett,
    "electricity": iter_samples_electricity,
    "traffic": iter_samples_traffic,
    "exchange_rate": iter_samples_exchange_rate,
    "illness": iter_samples_illness,
    "weather": iter_samples_weather,
}
