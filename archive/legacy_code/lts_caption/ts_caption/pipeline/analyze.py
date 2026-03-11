# ts_caption/pipeline/analyze.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd

from ts_caption.features.trend import compute_trend_segments, summarize_global_trend, TrendSegment
from ts_caption.features.volatility import compute_volatility, VolatilityInfo, volatility_label
from ts_caption.features.peaks import detect_peaks_and_valleys, PeakValleyEvent
from ts_caption.features.seasonality import estimate_dominant_period_acf, SeasonalityInfo, seasonality_strength_label
from ts_caption.features.correlation import compute_lagged_correlations_stable, CorrelationInfo

@dataclass
class StructuredSummary:
    meta: object
    global_trend_label: str
    trend_segments: List[TrendSegment]
    volatility: VolatilityInfo
    peaks: List[PeakValleyEvent]
    valleys: List[PeakValleyEvent]
    seasonality: SeasonalityInfo
    correlations: List[CorrelationInfo]

def analyze_window(meta, win_df: pd.DataFrame, time_col: str, target_col: str, series_cols: List[str]) -> StructuredSummary:
    x = win_df[target_col].to_numpy(float)

    trend_segments = compute_trend_segments(x, n_segments=3)
    global_trend_label = summarize_global_trend(trend_segments)
    vol = compute_volatility(x, n_segments=3)
    peaks, valleys = detect_peaks_and_valleys(x, z_thresh=1.0, min_distance=5)
    seas = estimate_dominant_period_acf(x, max_lag=min(200, len(x)//2), detrend=True)

    # correlations：只有多变量且列存在才算
    corr = []
    if len(series_cols) > 1:
        df_corr = win_df[[time_col] + series_cols].copy()
        corr = compute_lagged_correlations_stable(df_corr, target_col=target_col, candidate_cols=series_cols, top_k=3, max_lag=24, min_abs_corr=0.3)

    return StructuredSummary(
        meta=meta,
        global_trend_label=global_trend_label,
        trend_segments=trend_segments,
        volatility=vol,
        peaks=peaks,
        valleys=valleys,
        seasonality=seas,
        correlations=corr,
    )

def build_features(summary: StructuredSummary, x_target: np.ndarray, target_col: str) -> dict:
    vol_lab = volatility_label(x_target)
    seas_lab = seasonality_strength_label(summary.seasonality)

    corr_feature = [{
        "pair": [ci.var, target_col],   # ✅ 不要用 "target"
        "rho": ci.corr,
        "lag": ci.lag,
        "stable": ci.stable,
    } for ci in summary.correlations]

    return {
        "trend": summary.global_trend_label,
        "seasonality": seas_lab,
        "volatility": vol_lab,
        "correlations": corr_feature,
    }
