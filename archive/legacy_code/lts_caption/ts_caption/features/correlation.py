# ts_caption/features/correlation.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import pandas as pd
from .utils import z_normalize

@dataclass
class CorrelationInfo:
    var: str
    corr: float
    relation: str   # positive / negative
    lag: int
    stable: bool
    stability_note: str


def safe_corrcoef(a: np.ndarray, b: np.ndarray, min_n: int = 8, eps: float = 1e-8) -> float:
    """
    返回 Pearson 相关系数；若数据无效/方差太小/样本太少则返回 np.nan
    并且不会触发 numpy 的 divide warning。
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if int(m.sum()) < min_n:
        return np.nan
    a = a[m]; b = b[m]
    sa = float(np.std(a)); sb = float(np.std(b))
    if sa < eps or sb < eps:
        return np.nan
    # 这里用手写公式更稳，也可用 np.corrcoef，但手写不会触发那条 divide warning
    a0 = a - float(np.mean(a))
    b0 = b - float(np.mean(b))
    denom = (np.sqrt(np.sum(a0*a0)) * np.sqrt(np.sum(b0*b0)))
    if denom < eps:
        return np.nan
    return float(np.sum(a0*b0) / denom)

def _best_lag_corr(target: np.ndarray, series: np.ndarray, max_lag: int) -> Tuple[float, int]:
    best_corr = 0.0
    best_lag = 0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            t = target[lag:]
            v = series[:len(t)]
        else:
            t = target[:lag]
            v = series[-lag:]
        if len(t) < 8:
            continue
        c = safe_corrcoef(t, v, min_n=8, eps=1e-8)
        if np.isnan(c):
            continue
        if abs(c) > abs(best_corr):
            best_corr = float(c)
            best_lag = int(lag)
    return best_corr, best_lag

def compute_lagged_correlations_stable(
    df_window: pd.DataFrame,
    target_col: str,
    candidate_cols: Optional[List[str]] = None,
    top_k: int = 3,
    max_lag: int = 24,
    min_abs_corr: float = 0.3,
    lag_tol: int = 2,
) -> List[CorrelationInfo]:
    if target_col not in df_window.columns:
        return []

    cols = [c for c in (candidate_cols or df_window.columns.tolist())
            if c not in ("date", "timestamp", target_col) and c in df_window.columns]

    target = z_normalize(df_window[target_col].to_numpy(float))
    n = len(target)
    if n < 20:
        return []

    half = n // 2
    t1, t2 = target[:half], target[half:]

    results: List[CorrelationInfo] = []
    for var in cols:
        s = z_normalize(df_window[var].to_numpy(float))
        s1, s2 = s[:half], s[half:]

        corr_full, lag_full = _best_lag_corr(target, s, max_lag=max_lag)
        if abs(corr_full) < min_abs_corr:
            continue

        corr_1, lag_1 = _best_lag_corr(t1, s1, max_lag=max_lag)
        corr_2, lag_2 = _best_lag_corr(t2, s2, max_lag=max_lag)

        sign_full = np.sign(corr_full)
        stable_sign = (np.sign(corr_1) == sign_full) and (np.sign(corr_2) == sign_full)
        stable_lag = (abs(lag_1 - lag_full) <= lag_tol) and (abs(lag_2 - lag_full) <= lag_tol)
        stable = bool(stable_sign and stable_lag and (abs(corr_1) >= min_abs_corr * 0.7) and (abs(corr_2) >= min_abs_corr * 0.7))

        note = f"full(ρ={corr_full:.2f},lag={lag_full}), half1(ρ={corr_1:.2f},lag={lag_1}), half2(ρ={corr_2:.2f},lag={lag_2})"
        relation = "positive" if corr_full > 0 else "negative"
        results.append(CorrelationInfo(var=var, corr=float(corr_full), relation=relation, lag=int(lag_full), stable=stable, stability_note=note))

    results = sorted(results, key=lambda x: -abs(x.corr))
    return results[:top_k]
