# ts_cap/core/features.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import signal


# ---------------- utils ----------------
def z_normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    if x.size == 0:
        return x
    m = float(np.mean(x))
    s = float(np.std(x))
    if s < 1e-8:
        return np.zeros_like(x, dtype=float)
    return (x - m) / s


def robust_scale(x: np.ndarray, eps: float = 1e-8) -> float:
    x = np.asarray(x, float)
    if x.size == 0:
        return eps
    m = float(np.mean(x))
    s = float(np.std(x))
    return max(abs(m), s, eps)


def pct_change(a: float, b: float, scale: float) -> float:
    return (b - a) / scale * 100.0


def detrend_linear(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return x - float(np.mean(x)) if n else x
    t = np.arange(n, dtype=float)
    A = np.vstack([t, np.ones_like(t)]).T
    k, b = np.linalg.lstsq(A, x, rcond=None)[0]
    return x - (k * t + b)


# ---------------- trend ----------------
@dataclass
class TrendSegment:
    start: int
    end: int
    slope_z: float
    label: str  # up/down/flat


def segment_by_slope_fixed(
    x: np.ndarray,
    smooth_win: int = 5,
    slope_eps: float = 0.02,
    min_seg_len: int = 10,
) -> List[Dict[str, Any]]:
    """
    在 diff(z) 空间分段，再映射回 x 的 inclusive [start,end]
    """
    x = np.asarray(x, float)
    z = z_normalize(x)
    n = len(z)
    if n < 2:
        return [{"start": 0, "end": max(0, n - 1), "label": 0, "slope": 0.0}]

    d = np.diff(z)  # len n-1
    if len(d) == 0:
        return [{"start": 0, "end": n - 1, "label": 0, "slope": 0.0}]

    k = max(1, int(smooth_win))
    kernel = np.ones(k) / k
    d_pad = np.concatenate([d[:1], d, d[-1:]])
    ma = np.convolve(d_pad, kernel, mode="same")[1:-1]  # len n-1

    labels = np.zeros_like(ma, dtype=int)
    labels[ma > slope_eps] = 1
    labels[ma < -slope_eps] = -1

    segs_diff: List[Tuple[int, int, int]] = []
    cur = int(labels[0])
    s = 0
    for i in range(1, len(labels)):
        if int(labels[i]) != cur:
            segs_diff.append((s, i - 1, cur))
            s = i
            cur = int(labels[i])
    segs_diff.append((s, len(labels) - 1, cur))

    merged: List[Tuple[int, int, int]] = []
    for s_d, e_d, lab in segs_diff:
        x_s = s_d
        x_e = e_d + 1
        if merged:
            prev_s, prev_e, prev_lab = merged[-1]
            cur_len = x_e - x_s + 1
            if cur_len < min_seg_len:
                merged[-1] = (prev_s, x_e, prev_lab)
                continue
        merged.append((x_s, x_e, lab))

    segments: List[Dict[str, Any]] = []
    for x_s, x_e, lab in merged:
        x_s = int(max(0, min(x_s, n - 1)))
        x_e = int(max(0, min(x_e, n - 1)))
        if x_e <= x_s:
            continue
        xs = np.arange(x_e - x_s + 1, dtype=float)
        ys = z[x_s : x_e + 1]
        if len(xs) < 2:
            slope = 0.0
        else:
            A = np.vstack([xs, np.ones_like(xs)]).T
            slope, _ = np.linalg.lstsq(A, ys, rcond=None)[0]
        segments.append({"start": int(x_s), "end": int(x_e), "label": int(lab), "slope": float(slope)})
    if not segments:
        segments = [{"start": 0, "end": n - 1, "label": 0, "slope": 0.0}]
    return segments


def compute_trend_segments(x: np.ndarray, n_segments: int = 3) -> List[TrendSegment]:
    x = np.asarray(x, float)
    z = z_normalize(x)
    L = len(z)
    if L == 0:
        return []
    seg_len = max(L // n_segments, 1)
    out: List[TrendSegment] = []
    for i in range(n_segments):
        start = i * seg_len
        end = L if i == n_segments - 1 else (i + 1) * seg_len
        if end - start < 2:
            slope = 0.0
        else:
            t = np.arange(end - start, dtype=float)
            A = np.vstack([t, np.ones_like(t)]).T
            y = z[start:end]
            slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]
        if slope > 0.03:
            lab = "up"
        elif slope < -0.03:
            lab = "down"
        else:
            lab = "flat"
        out.append(TrendSegment(start=int(start), end=int(end - 1), slope_z=float(slope), label=lab))
    return out


def summarize_global_trend(segments: List[TrendSegment]) -> str:
    if not segments:
        return "flat"
    first, last = segments[0], segments[-1]
    if first.label == "up" and last.label == "down":
        return "up_then_down"
    if first.label == "down" and last.label == "up":
        return "down_then_up"
    avg = float(np.mean([s.slope_z for s in segments]))
    if avg > 0.03:
        return "up"
    if avg < -0.03:
        return "down"
    return "flat"


# ---------------- volatility ----------------
@dataclass
class VolatilityInfo:
    overall_std: float
    segment_stds: List[float]
    most_volatile_segment: int


def compute_volatility(x: np.ndarray, n_segments: int = 3) -> VolatilityInfo:
    x = np.asarray(x, float)
    L = len(x)
    if L < 2:
        return VolatilityInfo(0.0, [0.0] * n_segments, 0)

    xmax, xmin = float(np.max(x)), float(np.min(x))
    scale = (xmax - xmin) if xmax > xmin else 1.0
    overall_std = float(np.std(x) / scale)

    z = z_normalize(x)
    seg_len = max(L // n_segments, 1)
    seg_stds: List[float] = []
    for i in range(n_segments):
        s = i * seg_len
        e = L if i == n_segments - 1 else (i + 1) * seg_len
        seg_stds.append(float(np.std(z[s:e])) if e > s else 0.0)
    most = int(np.argmax(seg_stds)) if seg_stds else 0
    return VolatilityInfo(overall_std=overall_std, segment_stds=seg_stds, most_volatile_segment=most)


def volatility_label(x: np.ndarray) -> str:
    z = z_normalize(np.asarray(x, float))
    if len(z) < 2:
        return "low"
    diff = np.diff(z)
    metric = float(np.std(diff))
    if metric < 0.5:
        return "low"
    if metric < 1.0:
        return "medium"
    return "high"


# ---------------- peaks/valleys ----------------
@dataclass
class PeakValleyEvent:
    kind: str  # peak / valley
    index: int
    z_value: float
    delta_pct_vs_mean: float


def detect_peaks_and_valleys(
    x: np.ndarray, z_thresh: float = 1.0, min_distance: int = 5
) -> Tuple[List[PeakValleyEvent], List[PeakValleyEvent]]:
    x = np.asarray(x, float)
    z = z_normalize(x)
    L = len(z)
    if L < 3:
        return [], []

    scale = robust_scale(x)
    mean = float(np.mean(x))

    def is_local_max(i: int) -> bool:
        return 0 < i < L - 1 and z[i] > z[i - 1] and z[i] > z[i + 1]

    def is_local_min(i: int) -> bool:
        return 0 < i < L - 1 and z[i] < z[i - 1] and z[i] < z[i + 1]

    cand_p = [i for i in range(1, L - 1) if is_local_max(i) and z[i] >= z_thresh]
    cand_v = [i for i in range(1, L - 1) if is_local_min(i) and z[i] <= -z_thresh]

    def thin(cands: List[int]) -> List[int]:
        if not cands:
            return []
        kept = [cands[0]]
        for idx in cands[1:]:
            if idx - kept[-1] >= min_distance:
                kept.append(idx)
        return kept

    peaks: List[PeakValleyEvent] = []
    valleys: List[PeakValleyEvent] = []
    for idx in thin(cand_p):
        d = pct_change(mean, float(x[idx]), scale)
        peaks.append(PeakValleyEvent("peak", int(idx), float(z[idx]), float(d)))
    for idx in thin(cand_v):
        d = pct_change(mean, float(x[idx]), scale)
        valleys.append(PeakValleyEvent("valley", int(idx), float(z[idx]), float(d)))
    return peaks, valleys


# ---------------- ramps ----------------
def detect_ramps(
    x: np.ndarray,
    min_ramp_len: int = 24,
    min_ramp_z_change: float = 0.8,
    max_ramps: int = 3,
) -> List[Dict[str, Any]]:
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return []
    z = z_normalize(x)
    scale = robust_scale(x)

    segs = segment_by_slope_fixed(x)
    ramps: List[Dict[str, Any]] = []
    for seg in segs:
        s, e, lab = int(seg["start"]), int(seg["end"]), int(seg["label"])
        length = e - s + 1
        if lab == 0 or length < min_ramp_len:
            continue
        delta_z = float(z[e] - z[s])
        if abs(delta_z) < min_ramp_z_change:
            continue
        delta_pct = float(pct_change(float(x[s]), float(x[e]), scale))
        ramps.append(
            {
                "kind": "ramp_up" if lab > 0 else "ramp_down",
                "start": s,
                "end": e,
                "delta_z": delta_z,
                "delta_pct": delta_pct,
            }
        )

    ramps = sorted(ramps, key=lambda r: -abs(float(r["delta_z"])))
    selected: List[Dict[str, Any]] = []
    used = np.zeros(n, dtype=bool)
    for r in ramps:
        s, e = int(r["start"]), int(r["end"])
        if used[s : e + 1].mean() > 0.3:
            continue
        selected.append(r)
        used[s : e + 1] = True
        if len(selected) >= max_ramps:
            break
    return selected


# ---------------- seasonality ----------------
@dataclass
class SeasonalityInfo:
    has_seasonality: bool
    period: Optional[int]
    strength: float


def estimate_dominant_period_acf(
    x: np.ndarray,
    max_lag: int = 200,
    min_strength: float = 0.3,
    detrend: bool = True,
) -> SeasonalityInfo:
    x = np.asarray(x, float)
    n = len(x)
    if n < 6:
        return SeasonalityInfo(False, None, 0.0)

    y = detrend_linear(x) if detrend else x
    y = y - float(np.mean(y))
    var = float(np.var(y))
    if var < 1e-8:
        return SeasonalityInfo(False, None, 0.0)

    max_lag = min(int(max_lag), n - 2)
    acf = []
    for lag in range(1, max_lag + 1):
        num = float(np.dot(y[:-lag], y[lag:]))
        acf.append(num / ((n - lag) * var))
    acf = np.asarray(acf, float)

    best_lag = None
    best_strength = 0.0
    for i in range(1, len(acf) - 1):
        if acf[i] > acf[i - 1] and acf[i] > acf[i + 1] and acf[i] >= min_strength:
            if float(acf[i]) > best_strength:
                best_strength = float(acf[i])
                best_lag = i + 1

    if best_lag is None:
        return SeasonalityInfo(False, None, float(np.max(acf)) if len(acf) else 0.0)
    return SeasonalityInfo(True, int(best_lag), float(best_strength))


def estimate_period_fft(x: np.ndarray, fs: float = 1.0) -> Tuple[Optional[int], float]:
    """
    使用 Periodogram 检测频域主峰。
    返回: (周期, 相对强度 0~1)
    """
    x = np.asarray(x, float)
    x = x - np.mean(x)  # 去直流
    n = len(x)
    if n < 10:
        return None, 0.0

    # 1. 计算功率谱
    f, Pxx = signal.periodogram(x, fs=fs, window='hann', scaling='spectrum')
    
    # 2. 找峰值
    # 忽略接近 0 的低频 (Trend) 和极高频
    valid_mask = (f > 1.0/ (n/2)) & (f < 0.4) 
    if not np.any(valid_mask):
        return None, 0.0
    
    f_valid = f[valid_mask]
    P_valid = Pxx[valid_mask]
    
    if len(P_valid) == 0:
        return None, 0.0

    idx = np.argmax(P_valid)
    peak_freq = f_valid[idx]
    peak_power = P_valid[idx]
    
    # 3. 计算相对强度
    total_power = np.sum(P_valid)
    strength = peak_power / (total_power + 1e-9)
    
    period = int(round(1.0 / peak_freq))
    return period, float(strength)


def estimate_dominant_period_robust(
    x: np.ndarray,
    max_lag: int = 200,
) -> SeasonalityInfo:
    """
    综合 ACF 和 FFT 的结果，返回最可信的周期。
    """
    # 1. ACF 估计
    acf_info = estimate_dominant_period_acf(x, max_lag=max_lag, detrend=True)
    
    # 2. FFT 估计
    fft_period, fft_strength = estimate_period_fft(x)
    
    # 3. 决策融合
    has_acf = acf_info.has_seasonality
    has_fft = (fft_period is not None) and (fft_strength > 0.15) 
    
    final_res = acf_info 
    
    if has_acf and has_fft:
        # 两个都找到了
        p_acf = acf_info.period
        # 允许 15% 误差
        if p_acf and fft_period and abs(p_acf - fft_period) / p_acf < 0.15:
            final_res.strength = max(final_res.strength, fft_strength)
        else:
            # 不一致 -> 谁强听谁的
            # 经验阈值：ACF > 0.4 很强，FFT > 0.4 很强
            if fft_period and fft_strength > 0.4 and acf_info.strength < 0.4:
                 final_res = SeasonalityInfo(True, fft_period, fft_strength)
    elif not has_acf and has_fft:
        final_res = SeasonalityInfo(True, fft_period, fft_strength)
        
    return final_res


def seasonality_strength_label(info: SeasonalityInfo) -> Dict[str, Any]:
    if not info.has_seasonality or info.period is None:
        return {"period": None, "strength": "none"}
    s = float(info.strength)
    if s >= 0.6:
        lab = "strong"
    elif s >= 0.4:
        lab = "medium"
    elif s >= 0.25:
        lab = "weak"
    else:
        lab = "none"
    return {"period": int(info.period), "strength": lab}


# ---------------- correlation ----------------
@dataclass
class CorrelationInfo:
    var: str
    corr: float
    relation: str  # positive/negative
    lag: int
    stable: bool
    stability_note: str


def safe_corrcoef(a: np.ndarray, b: np.ndarray, min_n: int = 8, eps: float = 1e-8) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if int(m.sum()) < min_n:
        return float("nan")
    a = a[m]
    b = b[m]
    sa = float(np.std(a))
    sb = float(np.std(b))
    if sa < eps or sb < eps:
        return float("nan")
    a0 = a - float(np.mean(a))
    b0 = b - float(np.mean(b))
    denom = float(np.sqrt(np.sum(a0 * a0)) * np.sqrt(np.sum(b0 * b0)))
    if denom < eps:
        return float("nan")
    return float(np.sum(a0 * b0) / denom)


def _best_lag_corr(target: np.ndarray, series: np.ndarray, max_lag: int) -> Tuple[float, int]:
    """Helper for stability checks (single vector pair)"""
    best_corr = 0.0
    best_lag = 0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            t = target[lag:]
            v = series[: len(t)]
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
    series_map: Dict[str, np.ndarray],
    target_col: str,
    candidate_cols: Optional[List[str]] = None,
    top_k: int = 3,
    max_lag: int = 24,
    min_abs_corr: float = 0.3,
    lag_tol: int = 2,
) -> List[CorrelationInfo]:
    """
    Vectorized implementation using Matrix operations.
    """
    if target_col not in series_map:
        return []
    
    cols = [c for c in (candidate_cols or list(series_map.keys())) if c != target_col and c in series_map]
    if not cols:
        return []

    # 1. 构造矩阵 X, 向量 y
    # data dict order matters for mapping back to col names
    X_list = [series_map[c] for c in cols]
    
    # Check lengths (assume aligned by wrapper, but robust check)
    target_series = series_map[target_col]
    n = len(target_series)
    if n < 20: 
        return []
        
    # Trim to min length to be safe if unaligned (rare)
    min_len = min(n, min(len(x) for x in X_list))
    if min_len < 20: return []
    
    y = target_series[:min_len]
    X = np.stack([x[:min_len] for x in X_list], axis=1) # (T, N_cols)
    
    # Normalize (Z-score) for dot product correlation
    y_mean = y.mean()
    y_std = y.std() + 1e-9
    y_z = (y - y_mean) / y_std

    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0) + 1e-9
    X_z = (X - X_mean) / X_std

    # 2. Vectorized Search for Best Lag
    best_corrs = np.zeros(len(cols))
    best_lags = np.zeros(len(cols), dtype=int)
    
    # Loop lags, but compute all cols at once using matrix dot
    for lag in range(-max_lag, max_lag + 1):
        if lag == 0:
            feat = X_z
            target = y_z
        elif lag > 0:
            # feat 领先 target (feat[t-lag] vs target[t])
            # feat[:-lag], target[lag:]
            feat = X_z[:-lag]
            target = y_z[lag:]
        else:
            # lag < 0: feat 滞后
            feat = X_z[-lag:]
            target = y_z[:lag]
        
        if len(target) < 8: continue

        # Dot product: (C, T') . (T',) -> (C,)
        # Correlation approx = dot / length (since z-normalized)
        # Note: length varies by lag
        dot = np.dot(feat.T, target)
        
        # Rigorous norm correction for the slice
        norm_feat = np.linalg.norm(feat, axis=0)
        norm_target = np.linalg.norm(target)
        
        corrs = dot / (norm_feat * norm_target + 1e-9)
        
        # Update bests
        mask = np.abs(corrs) > np.abs(best_corrs)
        best_corrs[mask] = corrs[mask]
        best_lags[mask] = lag

    # 3. Select Top K and Verify Stability
    # Sort by absolute correlation
    indices = np.argsort(-np.abs(best_corrs))
    
    results: List[CorrelationInfo] = []
    half = n // 2
    
    # Pre-slice for stability check
    y1, y2 = target_series[:half], target_series[half:]
    
    for idx in indices:
        if len(results) >= top_k:
            break
        
        corr_full = best_corrs[idx]
        if abs(corr_full) < min_abs_corr:
            continue
            
        col_name = cols[idx]
        lag_full = best_lags[idx]
        
        # Stability Check (Slow path for Top-K only)
        # Re-use _best_lag_corr for sub-segments
        s_vec = series_map[col_name]
        s1, s2 = s_vec[:half], s_vec[half:]
        
        corr_1, lag_1 = _best_lag_corr(y1, s1, max_lag)
        corr_2, lag_2 = _best_lag_corr(y2, s2, max_lag)
        
        sign_full = np.sign(corr_full)
        stable_sign = (np.sign(corr_1) == sign_full) and (np.sign(corr_2) == sign_full)
        stable_lag = (abs(lag_1 - lag_full) <= lag_tol) and (abs(lag_2 - lag_full) <= lag_tol)
        
        stable = bool(
            stable_sign
            and stable_lag
            and (abs(corr_1) >= min_abs_corr * 0.7)
            and (abs(corr_2) >= min_abs_corr * 0.7)
        )
        
        note = f"full(ρ={corr_full:.2f},lag={lag_full}), half1(ρ={corr_1:.2f},lag={lag_1}), half2(ρ={corr_2:.2f},lag={lag_2})"
        relation = "positive" if corr_full > 0 else "negative"
        
        results.append(
            CorrelationInfo(
                var=str(col_name),
                corr=float(corr_full),
                relation=relation,
                lag=int(lag_full),
                stable=stable,
                stability_note=note,
            )
        )
        
    return results


# ---------------- summary type ----------------
@dataclass
class StructuredSummary:
    meta: Dict[str, Any]
    global_trend_label: str
    trend_segments: List[TrendSegment]
    volatility: VolatilityInfo
    peaks: List[PeakValleyEvent]
    valleys: List[PeakValleyEvent]
    seasonality: SeasonalityInfo
    correlations: List[CorrelationInfo]