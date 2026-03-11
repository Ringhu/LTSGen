import argparse
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd

#python gen_ett_caption.py 
# --csv_path /cluster/home/user1/hulining/TSDataset/LTSGen/dataset/ETT-small/ETTh1.csv 
# --dataset_name ETTh1 
# --output /cluster/home/user1/hulining/TSDataset/LTSGen/gen_tst_dataset/etth1_desc.jsonl 
# --target_col OT 
# --series_cols OT,HUFL,MUFL


# ============ 变量语义信息（根据 ETT 官方描述） ============
# HUFL/HULL/MUFL/MULL/LUFL/LULL: 各种负荷 (High/Middle/Low x UseFul/UseLess Load)
# OT: Oil Temperature
VAR_INFO_ETT = {
    "OT":   {"meaning_zh": "油温",           "unit": None},
    "HUFL": {"meaning_zh": "高负荷有用负载", "unit": None},
    "HULL": {"meaning_zh": "高负荷无用负载", "unit": None},
    "MUFL": {"meaning_zh": "中负荷有用负载", "unit": None},
    "MULL": {"meaning_zh": "中负荷无用负载", "unit": None},
    "LUFL": {"meaning_zh": "低负荷有用负载", "unit": None},
    "LULL": {"meaning_zh": "低负荷无用负载", "unit": None},
}


# =========================
# Dataclasses for structure
# =========================

@dataclass
class TrendSegment:
    start: int
    end: int
    slope_z: float
    label: str  # "up", "down", "flat"


@dataclass
class VolatilityInfo:
    overall_std: float
    segment_stds: List[float]
    most_volatile_segment: int


@dataclass
class PeakValleyEvent:
    kind: str  # "peak" or "valley"
    index: int
    z_value: float
    rel_change: float  # 相对均值变化比例, e.g. 0.2 = +20%


@dataclass
class SeasonalityInfo:
    has_seasonality: bool
    period: Optional[int]
    strength: float  # 自相关强度


@dataclass
class CorrelationInfo:
    var: str
    corr: float
    relation: str  # "positive" or "negative"
    lag: int       # 相关性最强时的滞后步数 (var 相对 target 的滞后)


@dataclass
class WindowMeta:
    series_id: int
    global_start_idx: int
    global_end_idx: int
    start_time: str
    end_time: str
    length: int


@dataclass
class StructuredSummary:
    meta: WindowMeta
    global_trend_label: str
    trend_segments: List[TrendSegment]
    volatility: VolatilityInfo
    peaks: List[PeakValleyEvent]
    valleys: List[PeakValleyEvent]
    seasonality: SeasonalityInfo
    correlations: List[CorrelationInfo]


# =========================
# Core analysis helpers
# =========================

import numpy as np

def z_normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    m = float(np.mean(x))
    s = float(np.std(x))
    if s < 1e-8:
        return np.zeros_like(x)
    return (x - m) / s


def segment_by_slope(
    x: np.ndarray,
    win: int = 5,
    slope_eps: float = 0.02,
    min_seg_len: int = 10,
):
    """
    按斜率符号（上升 / 下降 / 近似平）把序列切成若干段。
    返回列表，每个元素是 dict:
      {"start": int, "end": int, "label": -1/0/1, "slope": float}
    label: -1=下降段, 0=基本平, 1=上升段
    """
    x = np.asarray(x, float)
    z = z_normalize(x)
    n = len(z)
    if n < 2:
        return [{"start": 0, "end": n - 1, "label": 0, "slope": 0.0}]

    # 一阶差分 + 滑动平均，得到平滑斜率
    d = np.diff(z)
    k = win
    kernel = np.ones(k) / k
    d_pad = np.concatenate([d[:1], d, d[-1:]])   # 简单首尾 padding
    ma = np.convolve(d_pad, kernel, mode="same")[1:-1]  # 对齐到原 d 长度

    labels = np.zeros_like(ma, dtype=int)
    labels[ma > slope_eps] = 1
    labels[ma < -slope_eps] = -1

    # 把相同 label 的连续区间合并成 segment（在 diff 空间）
    raw_segs = []
    cur_label = labels[0]
    start = 0
    for i in range(1, len(labels)):
        if labels[i] != cur_label:
            raw_segs.append((start, i, cur_label))
            start = i
            cur_label = labels[i]
    raw_segs.append((start, len(labels), cur_label))

    # 把太短的 segment 合并到前一段，避免碎片
    merged = []
    for s, e, lab in raw_segs:
        # diff 索引 s..e 映射到 x 的 s..e
        if merged and (e - s + 1) < min_seg_len:
            ps, pe, plab = merged[-1]
            merged[-1] = (ps, e, plab)  # 长度太短，合并到前一段
        else:
            merged.append((s, e, lab))

    # 计算每一段的线性拟合斜率（在 z 空间）
    segments = []
    for s, e, lab in merged:
        xs = np.arange(e - s + 1)
        ys = z[s:e + 1]
        if len(xs) < 2:
            slope = 0.0
        else:
            A = np.vstack([xs, np.ones_like(xs)]).T
            slope, _ = np.linalg.lstsq(A, ys, rcond=None)[0]
        segments.append(
            {"start": int(s), "end": int(e), "label": int(lab), "slope": float(slope)}
        )
    return segments

def build_global_summary_sentence(
    x_target: np.ndarray,
    target_col: str,
    global_trend_label: str,
    time_index: Optional[List[str]] = None,
) -> str:
    """
    用具体数值总结全局走势，而不是“整体平稳”。
    如果提供 time_index，则在描述中使用真实时间（字符串）而不是“第 X 个时间步”。
    """
    x = np.asarray(x_target, float)
    if len(x) == 0:
        return ""

    start_v = float(x[0])
    end_v = float(x[-1])
    mean_v = float(np.mean(x))
    min_v = float(np.min(x))
    max_v = float(np.max(x))
    min_idx = int(np.argmin(x))
    max_idx = int(np.argmax(x))

    if abs(mean_v) > 1e-8:
        total_delta_rel = (end_v - start_v) / abs(mean_v)
        range_rel = (max_v - min_v) / abs(mean_v)
    else:
        total_delta_rel = 0.0
        range_rel = 0.0

    total_delta_pct = total_delta_rel * 100.0
    range_pct = range_rel * 100.0

    def idx_time_phrase(idx: int) -> str:
        """在某个时间步附近，用真实时间或“第 X 个时间步附近”描述。"""
        if time_index is not None and 0 <= idx < len(time_index):
            return f"在 {time_index[idx]} 附近"
        else:
            return f"在第 {idx} 个时间步附近"

    def extreme_loc_str(idx: int) -> str:
        """极值位置，用真实时间或“第 X 个时间步”描述。"""
        if time_index is not None and 0 <= idx < len(time_index):
            return f"（大约出现在 {time_index[idx]}）"
        else:
            return f"（第 {idx} 个时间步）"

    # 不同 global_trend_label 下的模版
    if global_trend_label == "up":
        sent = (
            f"整体呈上升趋势，{target_col} 从窗口起点约 {start_v:.3f} "
            f"升至终点约 {end_v:.3f}，净变化约 +{total_delta_pct:.1f}%。"
        )
    elif global_trend_label == "down":
        sent = (
            f"整体呈下降趋势，{target_col} 从窗口起点约 {start_v:.3f} "
            f"降至终点约 {end_v:.3f}，净变化约 {total_delta_pct:.1f}%。"
        )
    elif global_trend_label == "up_then_down":
        peak_loc = idx_time_phrase(max_idx)
        sent = (
            f"整体呈先升后降的走势，{target_col} {peak_loc}达到约 "
            f"{max_v:.3f} 的峰值（相对窗口均值约 +{((max_v-mean_v)/abs(mean_v+1e-12))*100:.1f}%），"
            f"随后回落到终点约 {end_v:.3f}。"
        )
    elif global_trend_label == "down_then_up":
        valley_loc = idx_time_phrase(min_idx)
        sent = (
            f"整体呈先降后升的走势，{target_col} {valley_loc}降至约 "
            f"{min_v:.3f} 的低谷（相对窗口均值约 {((min_v-mean_v)/abs(mean_v+1e-12))*100:.1f}%），"
            f"随后回升到终点约 {end_v:.3f}。"
        )
    else:
        # “flat” 情况也给足信息：均值、极值、整体变化
        max_loc_str = extreme_loc_str(max_idx)
        min_loc_str = extreme_loc_str(min_idx)
        sent = (
            f"整体无明显单调上升或下降，{target_col} 围绕均值约 {mean_v:.3f} 波动，"
            f"起点约 {start_v:.3f}，终点约 {end_v:.3f}（净变化约 {total_delta_pct:.1f}%），"
            f"全程最高值约 {max_v:.3f}{max_loc_str}，"
            f"最低值约 {min_v:.3f}{min_loc_str}，"
            f"最大振幅约 {range_pct:.1f}%。"
        )

    return sent


def detect_ramps(
    x: np.ndarray,
    min_ramp_len: int = 24,
    min_ramp_z_change: float = 0.8,
    max_ramps: int = 3,
):
    """
    从斜率 segment 中筛选出“长而幅度大的上升/下降坡”。
    返回若干 ramp 事件，每个事件是 dict:
      {
        "kind": "ramp_up" / "ramp_down",
        "start": int,
        "end": int,
        "delta_z": float,
        "delta_rel": float,   # 相对窗口均值的变化百分比 (例如 0.25 = +25%)
      }
    """
    x = np.asarray(x, float)
    z = z_normalize(x)
    segs = segment_by_slope(x)

    if len(x) < 2:
        return []

    mean_val = float(np.mean(x))
    ramps = []
    for seg in segs:
        s, e, lab = seg["start"], seg["end"], seg["label"]
        length = e - s + 1
        if lab == 0 or length < min_ramp_len:
            continue
        delta_z = float(z[e] - z[s])
        if abs(delta_z) < min_ramp_z_change:
            continue

        if abs(mean_val) > 1e-8:
            delta_rel = float((x[e] - x[s]) / abs(mean_val))
        else:
            delta_rel = 0.0

        kind = "ramp_up" if lab > 0 else "ramp_down"
        ramps.append(
            {
                "kind": kind,
                "start": s,
                "end": e,
                "delta_z": delta_z,
                "delta_rel": delta_rel,
            }
        )

    # 按幅度排序，取前 max_ramps 个且尽量不重叠
    ramps = sorted(ramps, key=lambda r: -abs(r["delta_z"]))
    selected = []
    used = np.zeros(len(x), dtype=bool)

    for r in ramps:
        s, e = r["start"], r["end"]
        # 如果和已选 ramp 重叠太多，就跳过
        if used[s:e + 1].mean() > 0.3:
            continue
        selected.append(r)
        used[s:e + 1] = True
        if len(selected) >= max_ramps:
            break

    return selected



def compute_trend_segments(x: np.ndarray, n_segments: int = 3) -> List[TrendSegment]:
    """
    简单的分段线性趋势：在 z-score 空间里均匀切成 n 段，各段做线性拟合。
    """
    L = len(x)
    z = z_normalize(x)
    seg_len = max(L // n_segments, 1)
    segments: List[TrendSegment] = []
    for s in range(n_segments):
        start = s * seg_len
        end = L if s == n_segments - 1 else (s + 1) * seg_len
        if end - start < 2:
            slope = 0.0
        else:
            t = np.arange(end - start)
            A = np.vstack([t, np.ones_like(t)]).T
            y = z[start:end]
            slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]
        if slope > 0.03:
            label = "up"
        elif slope < -0.03:
            label = "down"
        else:
            label = "flat"
        segments.append(TrendSegment(start=start, end=end, slope_z=float(slope), label=label))
    return segments


def summarize_global_trend(segments: List[TrendSegment]) -> str:
    """
    输出一个粗粒度的全局趋势标签：
    up / down / flat / up_then_down / down_then_up
    """
    if not segments:
        return "flat"
    first, last = segments[0], segments[-1]
    if first.label == "up" and last.label == "down":
        return "up_then_down"
    if first.label == "down" and last.label == "up":
        return "down_then_up"
    avg_slope = float(np.mean([s.slope_z for s in segments]))
    if avg_slope > 0.03:
        return "up"
    if avg_slope < -0.03:
        return "down"
    return "flat"


def compute_volatility(x: np.ndarray, n_segments: int = 3) -> VolatilityInfo:
    """
    用原始值的整体 std 与分段 std（在 z 空间）描述波动结构。
    """
    x = np.asarray(x, dtype=float)
    L = len(x)
    if L < 2:
        return VolatilityInfo(overall_std=0.0, segment_stds=[0.0] * n_segments, most_volatile_segment=0)

    xmax, xmin = np.max(x), np.min(x)
    scale = float(xmax - xmin) if xmax > xmin else 1.0
    overall_std = float(np.std(x) / scale)

    z = z_normalize(x)
    seg_len = max(L // n_segments, 1)
    seg_stds: List[float] = []
    for s in range(n_segments):
        start = s * seg_len
        end = L if s == n_segments - 1 else (s + 1) * seg_len
        seg_stds.append(float(np.std(z[start:end])) if end > start else 0.0)
    most_volatile = int(np.argmax(seg_stds)) if seg_stds else 0
    return VolatilityInfo(
        overall_std=overall_std, segment_stds=seg_stds, most_volatile_segment=most_volatile
    )


def detect_peaks_and_valleys(x: np.ndarray, z_thresh: float = 1.0, min_distance: int = 5):
    """
    在 z-score 序列上用局部极大/极小点检测峰值和谷值。
    """
    z = z_normalize(x)
    mean = float(np.mean(x))
    peaks: List[PeakValleyEvent] = []
    valleys: List[PeakValleyEvent] = []
    L = len(z)

    def is_local_max(i: int) -> bool:
        if i <= 0 or i >= L - 1:
            return False
        return z[i] > z[i - 1] and z[i] > z[i + 1]

    def is_local_min(i: int) -> bool:
        if i <= 0 or i >= L - 1:
            return False
        return z[i] < z[i - 1] and z[i] < z[i + 1]

    candidate_peaks = [i for i in range(1, L - 1) if is_local_max(i) and z[i] >= z_thresh]
    candidate_valleys = [i for i in range(1, L - 1) if is_local_min(i) and z[i] <= -z_thresh]

    def thin_candidates(cands: List[int]) -> List[int]:
        if not cands:
            return []
        kept = [cands[0]]
        for idx in cands[1:]:
            if idx - kept[-1] >= min_distance:
                kept.append(idx)
        return kept

    peak_idxs = thin_candidates(candidate_peaks)
    valley_idxs = thin_candidates(candidate_valleys)

    for idx in peak_idxs:
        rel_change = (x[idx] - mean) / abs(mean) if abs(mean) > 1e-8 else 0.0
        peaks.append(
            PeakValleyEvent(
                kind="peak",
                index=int(idx),
                z_value=float(z[idx]),
                rel_change=float(rel_change),
            )
        )
    for idx in valley_idxs:
        rel_change = (x[idx] - mean) / abs(mean) if abs(mean) > 1e-8 else 0.0
        valleys.append(
            PeakValleyEvent(
                kind="valley",
                index=int(idx),
                z_value=float(z[idx]),
                rel_change=float(rel_change),
            )
        )
    return peaks, valleys


def estimate_dominant_period(x: np.ndarray, max_lag: int = 200, min_strength: float = 0.3) -> SeasonalityInfo:
    """
    用自相关粗略估计主周期。
    """
    x = np.asarray(x)
    n = len(x)
    if n < 4:
        return SeasonalityInfo(False, None, 0.0)
    x_centered = x - np.mean(x)
    var = float(np.var(x_centered))
    if var < 1e-8:
        return SeasonalityInfo(False, None, 0.0)
    max_lag = min(max_lag, n - 2)
    acf = []
    for lag in range(1, max_lag + 1):
        num = np.dot(x_centered[:-lag], x_centered[lag:])
        acf.append(num / ((n - lag) * var))
    acf = np.asarray(acf)
    best_lag = None
    best_strength = 0.0
    for lag in range(1, len(acf) - 1):
        if acf[lag] > acf[lag - 1] and acf[lag] > acf[lag + 1] and acf[lag] >= min_strength:
            if acf[lag] > best_strength:
                best_strength = float(acf[lag])
                best_lag = lag + 1  # acf[0] 对应 lag=1
    if best_lag is None:
        return SeasonalityInfo(False, None, float(np.max(acf) if len(acf) else 0.0))
    return SeasonalityInfo(True, int(best_lag), best_strength)


def compute_lagged_correlations(
    df_window: pd.DataFrame,
    target_col: str = "OT",
    candidate_cols: Optional[List[str]] = None,
    top_k: int = 3,
    max_lag: int = 24,
    min_abs_corr: float = 0.3
) -> List[CorrelationInfo]:
    """
    只在 candidate_cols 范围内算 target_col 与其他变量的滞后相关。
    lag>0 表示 target 相对 var 滞后 lag 步（var 先动），lag<0 相反。
    """
    if target_col not in df_window.columns:
        return []

    if candidate_cols is None:
        cols = [c for c in df_window.columns if c not in ["date", target_col]]
    else:
        cols = [c for c in candidate_cols if c != target_col and c in df_window.columns]

    target = z_normalize(df_window[target_col].to_numpy(dtype=float))
    L = len(target)
    results: List[CorrelationInfo] = []

    for var in cols:
        series = z_normalize(df_window[var].to_numpy(dtype=float))
        best_corr = 0.0
        best_lag = 0
        for lag in range(-max_lag, max_lag + 1):
            if lag >= 0:
                t = target[lag:]
                v = series[:len(t)]
            else:
                t = target[:lag]
                v = series[-lag:]
            if len(t) < 5:
                continue
            c = np.corrcoef(t, v)[0, 1]
            if np.isnan(c):
                continue
            if abs(c) > abs(best_corr):
                best_corr = float(c)
                best_lag = int(lag)
        if abs(best_corr) >= min_abs_corr:
            relation = "positive" if best_corr > 0 else "negative"
            results.append(
                CorrelationInfo(
                    var=var,
                    corr=best_corr,
                    relation=relation,
                    lag=best_lag
                )
            )

    results = sorted(results, key=lambda ci: -abs(ci.corr))
    return results[:top_k]


# =========================
# Feature-level labels
# =========================

def trend_feature_label(summary: StructuredSummary) -> str:
    """
    把趋势转成类似 upward_strong / downward_weak / flat 这样的 feature label。
    """
    segs = summary.trend_segments
    if not segs:
        return "flat"

    avg_slope = float(np.mean([s.slope_z for s in segs]))
    direction = "flat"
    if avg_slope > 0.01:
        direction = "upward"
    elif avg_slope < -0.01:
        direction = "downward"

    mag = abs(avg_slope)
    if direction == "flat" or mag < 0.015:
        strength = "weak"
    elif mag < 0.06:
        strength = "moderate"
    else:
        strength = "strong"

    if direction == "flat":
        return "flat"
    return f"{direction}_{strength}"


def seasonality_feature_label(seas: SeasonalityInfo) -> Dict[str, Any]:
    """
    返回:
      {"period": 24 or null, "strength": "strong"/"medium"/"weak"/"none"}
    阈值和 caption 用词对齐：
      strength >= 0.6 -> strong
      >= 0.4          -> medium
      >= 0.25         -> weak
      else            -> none
    """
    if not seas.has_seasonality or seas.period is None:
        return {"period": None, "strength": "none"}
    s = seas.strength
    if s >= 0.6:
        strength = "strong"
    elif s >= 0.4:
        strength = "medium"
    elif s >= 0.25:
        strength = "weak"
    else:
        strength = "none"
    return {"period": seas.period, "strength": strength}


def volatility_feature_label(x: np.ndarray) -> str:
    """
    用 z-normalize 后的一阶差分 std 划分高/中/低波动。
    这个 label 同时用于 features.volatility 与 caption 文案。
    """
    z = z_normalize(x)
    if len(z) < 2:
        return "low"
    diff = np.diff(z)
    metric = float(np.std(diff))
    # 这些阈值可以按需要微调
    if metric < 0.5:
        return "low"
    elif metric < 1.0:
        return "medium"
    else:
        return "high"


def anomaly_segments_from_events(
    peaks: List[PeakValleyEvent],
    valleys: List[PeakValleyEvent],
    z_threshold: float = 2.0,
    segment_half_width: int = 3
) -> List[Dict[str, Any]]:
    """
    从极端峰谷构造“统计意义上的异常片段”，仅作为 pattern feature，
    不作为真实异常标签。
    """
    segments = []
    for e in peaks + valleys:
        if abs(e.z_value) < z_threshold:
            continue
        start = max(0, e.index - segment_half_width)
        end = e.index + segment_half_width
        kind = "spike" if e.kind == "peak" else "drop"
        segments.append(
            {
                "start": start,
                "end": end,
                "kind": kind,
                "z_value": e.z_value,
                "rel_change": e.rel_change,
            }
        )
    return segments


# =========================
# Caption generation
# =========================

def build_variable_intro(series_cols: List[str], target_col: str) -> str:
    """
    根据 variables 列表自动生成“变量导语”段落。
    """
    parts = []
    for idx, col in enumerate(series_cols):
        info = VAR_INFO_ETT.get(col, {})
        meaning = info.get("meaning_zh", col)
        unit = info.get("unit")
        role = "预测目标" if col == target_col else "协变量"
        unit_str = f"，单位 {unit}" if unit else ""
        parts.append(f"第 {idx} 列为 {col}（{meaning}{unit_str}，作为{role}）")
    intro = f"本样本的 timeseries 包含 {len(series_cols)} 个变量：" + "；".join(parts)
    intro += f"。以下描述主要针对 {target_col}，并描述其与其它变量的关系。"
    return intro


def structured_to_caption(
    summary,
    target_col: str,
    volatility_label: str,
    x_target: np.ndarray,
    time_index: Optional[List[str]] = None,
) -> str:
    """
    新版 caption：
      - 全局描述用具体数值 + 真实时间（如果提供 time_index）；
      - ramp 段保留（用真实时间范围）；
      - 峰谷事件使用真实时间；
      - 其他部分（波动 / 周期 / 相关性）沿用原逻辑。
    """
    length = summary.meta.length

    # ---------- 1. 全局走势（数值化 + 真实时间） ----------
    global_sent = build_global_summary_sentence(
        x_target=x_target,
        target_col=target_col,
        global_trend_label=summary.global_trend_label,
        time_index=time_index,
    )

    def idx_time(idx: int) -> str:
        """单个索引对应的时间字符串（或退回到“第 X 个时间步”）。"""
        if time_index is not None and 0 <= idx < len(time_index):
            return time_index[idx]
        else:
            return f"第 {idx} 个时间步"

    # ---------- 2. 重要上升 / 下降坡 (ramps) ----------
    ramps = detect_ramps(x_target, min_ramp_len=24, min_ramp_z_change=0.8, max_ramps=3)
    ramps_sents = []
    x = np.asarray(x_target, float)
    mean_v = float(np.mean(x)) if len(x) > 0 else 0.0

    for r in ramps:
        s, e = r["start"], r["end"]
        delta_rel = r["delta_rel"] * 100.0
        v_start = float(x[s])
        v_end = float(x[e])

        if time_index is not None and 0 <= s < len(time_index) and 0 <= e < len(time_index):
            range_desc = f"在 {time_index[s]} 至 {time_index[e]} 之间"
        else:
            range_desc = f"在第 {s}–{e} 个时间步之间"

        if r["kind"] == "ramp_up":
            ramps_sents.append(
                f"{range_desc}，{target_col} 由约 {v_start:.3f} "
                f"逐步上升到约 {v_end:.3f}，净变化约 +{delta_rel:.1f}%。"
            )
        else:
            ramps_sents.append(
                f"{range_desc}，{target_col} 由约 {v_start:.3f} "
                f"持续下降到约 {v_end:.3f}，净变化约 {delta_rel:.1f}%。"
            )
    ramps_sent = " ".join(ramps_sents)

    # ---------- 3. 波动结构 ----------
    vol = summary.volatility
    seg_std = vol.segment_stds
    n_seg = len(seg_std)
    vol_sent = ""
    if seg_std:
        max_std = max(seg_std)
        min_std = min(seg_std)
        ratio = (max_std / min_std) if min_std > 1e-6 else float("inf")
        most_idx = vol.most_volatile_segment
        if most_idx == 0:
            loc = "前段"
        elif most_idx == n_seg - 1:
            loc = "后段"
        else:
            loc = "中段"

        if volatility_label == "low":
            if ratio >= 1.5:
                vol_sent = f"整体围绕均值小幅波动，其中 {loc} 的波动略高于其它阶段（标准差约为 {max_std:.2f}）。"
            else:
                vol_sent = "整体围绕均值小幅波动，各阶段波动水平差异不大。"
        elif volatility_label == "medium":
            if ratio >= 1.5:
                vol_sent = f"整体波动中等，{loc} 的短期波动幅度略高于其它阶段（标准差约为 {max_std:.2f}）。"
            else:
                vol_sent = "整体波动中等，各阶段波动水平相近。"
        else:  # high
            if ratio >= 1.5:
                vol_sent = f"整体波动较大，尤其是 {loc} 的短期波动幅度最为明显（标准差约为 {max_std:.2f}）。"
            else:
                vol_sent = "整体波动较大，各阶段均存在明显的短期波动。"

    # ---------- 4. 峰谷事件（使用真实时间） ----------
    peak_sent_parts = []
    if summary.peaks:
        sorted_peaks = sorted(summary.peaks, key=lambda e: -abs(e.z_value))[:3]
        for e in sorted_peaks:
            idx = e.index
            val = float(x[idx])
            change_pct = e.rel_change * 100.0
            time_desc = f"在 {idx_time(idx)} 附近"
            peak_sent_parts.append(
                f"{time_desc}，{target_col} 约为 {val:.3f}，"
                f"高于该窗口均值约 {change_pct:.1f}%。"
            )

    valley_sent_parts = []
    if summary.valleys:
        sorted_vals = sorted(summary.valleys, key=lambda e: -abs(e.z_value))[:3]
        for e in sorted_vals:
            idx = e.index
            val = float(x[idx])
            change_pct = e.rel_change * 100.0
            time_desc = f"在 {idx_time(idx)} 附近"
            valley_sent_parts.append(
                f"{time_desc}，{target_col} 约为 {val:.3f}，"
                f"低于该窗口均值约 {abs(change_pct):.1f}%。"
            )

    event_sent = " ".join(peak_sent_parts + valley_sent_parts)

    # ---------- 5. 周期性 ----------
    seas = summary.seasonality
    if seas.has_seasonality and seas.period is not None:
        s = seas.strength
        if s >= 0.6:
            prefix = "序列中存在显著的周期性"
        elif s >= 0.4:
            prefix = "序列中存在较明显的周期性"
        elif s >= 0.25:
            prefix = "序列中存在较弱的周期性"
        else:
            prefix = "序列中仅存在很弱的周期性成分"
        seas_sent = f"{prefix}，主周期大约为 {seas.period} 个时间步（自相关强度约 {seas.strength:.2f}）。"
    else:
        seas_sent = "未检测到明显的周期性结构。"

    # ---------- 6. 多变量相关性 ----------
    corr_sent = ""
    if summary.correlations:
        parts = []
        for info in summary.correlations:
            rel = "正相关" if info.relation == "positive" else "负相关"
            if info.lag > 0:
                lag_desc = f"，在 {info.lag} 个时间步滞后处相关性最强"
            elif info.lag < 0:
                lag_desc = f"，在提前 {abs(info.lag)} 个时间步处相关性最强"
            else:
                lag_desc = "，在无滞后时相关性最强"
            parts.append(
                f"{info.var} 与 {target_col} 呈{rel}（相关系数约 {info.corr:.2f}{lag_desc}）"
            )
        corr_sent = "在多变量特征中，" + "；".join(parts) + "。"

    sentences = [
        global_sent,   # 全局句（有具体数值和时间）
        ramps_sent,    # 重要上升/下降坡
        vol_sent,
        event_sent,
        seas_sent,
        corr_sent,
    ]
    caption_body = " ".join([s for s in sentences if s])
    return caption_body


# =========================
# Pipeline: ETT csv -> samples
# =========================

def generate_windows(df: pd.DataFrame, window_len: int, stride: int,
                     max_windows: Optional[int] = None):
    """
    对长序列做滑动窗口，返回 meta + 子 DataFrame。
    """
    n = len(df)
    windows_generated = 0
    for start in range(0, n - window_len + 1, stride):
        end = start + window_len
        if max_windows is not None and windows_generated >= max_windows:
            break
        win_df = df.iloc[start:end].reset_index(drop=True)
        meta = WindowMeta(
            series_id=0,
            global_start_idx=start,
            global_end_idx=end - 1,
            start_time=win_df["date"].iloc[0].strftime("%Y-%m-%d %H:%M"),
            end_time=win_df["date"].iloc[-1].strftime("%Y-%m-%d %H:%M"),
            length=window_len,
        )
        yield meta, win_df
        windows_generated += 1


def analyze_window(meta: WindowMeta, win_df: pd.DataFrame,
                   target_col: str = "OT",
                   corr_cols: Optional[List[str]] = None) -> StructuredSummary:
    """
    针对单个窗口构建 StructuredSummary，correlations 只在 corr_cols 范围内算。
    """
    x = win_df[target_col].to_numpy(dtype=float)

    trend_segments = compute_trend_segments(x, n_segments=3)
    global_trend_label = summarize_global_trend(trend_segments)
    volatility = compute_volatility(x, n_segments=len(trend_segments) if trend_segments else 3)
    peaks, valleys = detect_peaks_and_valleys(x, z_thresh=1.0, min_distance=5)
    seasonality = estimate_dominant_period(x, max_lag=min(200, len(x) // 2))

    if corr_cols is None or len(corr_cols) <= 1:
        correlations = []
    else:
        df_corr = win_df[["date"] + corr_cols]
        correlations = compute_lagged_correlations(
            df_corr, target_col=target_col, candidate_cols=corr_cols,
            top_k=3, max_lag=24, min_abs_corr=0.3
        )

    return StructuredSummary(
        meta=meta,
        global_trend_label=global_trend_label,
        trend_segments=trend_segments,
        volatility=volatility,
        peaks=peaks,
        valleys=valleys,
        seasonality=seasonality,
        correlations=correlations,
    )


def run_ett_caption_pipeline(
    csv_path: str,
    output_jsonl: str,
    dataset_name: str,
    task: str = "forecasting",
    window_len: int = 1024,
    stride: int = 256,
    target_col: str = "OT",
    series_cols_str: Optional[str] = None,
    max_windows: Optional[int] = None,
):
    """
    End-to-end pipeline:
      1. 读取 ETT CSV；
      2. 滑动窗口；
      3. 分析每个窗口并生成 caption + features；
      4. 输出 JSONL，每行一个样本。
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    if "date" not in df.columns:
        raise ValueError("Expected a 'date' column in ETT CSV.")
    df["date"] = pd.to_datetime(df["date"])

    # ===== series_cols: 决定 timeseries 中有哪些变量，也决定相关性计算范围 =====
    if series_cols_str is None or series_cols_str.strip() == "":
        series_cols = [target_col]  # 默认单变量
    else:
        series_cols = [c.strip() for c in series_cols_str.split(",") if c.strip()]

    # 保证 target_col 在 series_cols 里且顺序为第一
    if target_col not in series_cols:
        series_cols = [target_col] + series_cols
    else:
        series_cols = [target_col] + [c for c in series_cols if c != target_col]

    # 检查这些列都在数据里
    for c in series_cols:
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not found in CSV.")

    with open(output_jsonl, "w", encoding="utf-8") as f_out:
        for meta, win_df in generate_windows(
            df, window_len=window_len, stride=stride, max_windows=max_windows
        ):
            # 只针对 series_cols 分析 & 导出
            win_df_sub = win_df[["date"] + series_cols]

            summary = analyze_window(
                meta, win_df_sub, target_col=target_col, corr_cols=series_cols
            )

            # ====== 构造 features ======
            x_target = win_df_sub[target_col].to_numpy(dtype=float)
            trend_label = trend_feature_label(summary)
            seasonality_label = seasonality_feature_label(summary.seasonality)
            volatility_label = volatility_feature_label(x_target)
            anomaly_segments = anomaly_segments_from_events(summary.peaks, summary.valleys)
            correlations_feature = [
                {
                    "pair": [info.var, target_col],
                    "rho": info.corr,
                    "lag": info.lag,
                }
                for info in summary.correlations
            ]

            features = {
                "trend": trend_label,
                "seasonality": seasonality_label,
                "volatility": volatility_label,
                "anomaly_segments": anomaly_segments,
                "correlations": correlations_feature,
            }

            # ====== 变量元信息 ======
            variables_meta = []
            for idx, col in enumerate(series_cols):
                info = VAR_INFO_ETT.get(col, {})
                variables_meta.append({
                    "name": col,
                    "index": idx,
                    "role": "target" if col == target_col else "feature",
                    "meaning_zh": info.get("meaning_zh", col),
                    "unit": info.get("unit", None),
                })

                # ====== 时间索引（字符串） ======
                time_list = win_df_sub["date"].dt.strftime("%Y-%m-%d %H:%M").tolist()

                # ====== caption：变量导语 + 模式描述 ======
                intro = build_variable_intro(series_cols, target_col)
                x_target = win_df_sub[target_col].to_numpy(dtype=float)

                caption_body = structured_to_caption(
                    summary,
                    target_col=target_col,
                    volatility_label=volatility_label,
                    x_target=x_target,
                    time_index=time_list,  # ★ 传入真实时间列表
                )
                full_caption = intro + " " + caption_body

                # ====== 其它字段 ======
                timeseries_values = win_df_sub[series_cols].to_numpy(dtype=float).tolist()

            label = {"anomaly": False, "class": None}

            record = {
                "dataset": dataset_name,
                "task": task,
                "window_length": meta.length,
                "indices": [meta.global_start_idx, meta.global_end_idx],
                "time": time_list,
                "timeseries": timeseries_values,
                "variables": variables_meta,
                "label": label,
                "features": features,
                "descriptions": [full_caption],
            }

            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")


# =========================
# CLI
# =========================

def build_arg_parser():
    parser = argparse.ArgumentParser(description="ETT -> factual captions & features (multi-var aware).")
    parser.add_argument("--csv_path", type=str, required=True)
    parser.add_argument("--dataset_name", type=str, required=True)
    parser.add_argument("--task", type=str, default="forecasting")
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--window_len", type=int, default=512)
    parser.add_argument("--stride", type=int, default=256)
    parser.add_argument("--target_col", type=str, default="OT")
    parser.add_argument(
        "--series_cols",
        type=str,
        default=None,
        help="逗号分隔的变量名列表，决定 timeseries 中哪些列被包含；若为空则只用 target_col。",
    )
    parser.add_argument("--max_windows", type=int, default=None)
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    run_ett_caption_pipeline(
        csv_path=args.csv_path,
        output_jsonl=args.output,
        dataset_name=args.dataset_name,
        task=args.task,
        window_len=args.window_len,
        stride=args.stride,
        target_col=args.target_col,
        series_cols_str=args.series_cols,
        max_windows=args.max_windows,
    )


if __name__ == "__main__":
    main()
