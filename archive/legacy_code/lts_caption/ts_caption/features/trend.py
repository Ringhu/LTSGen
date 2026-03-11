# ts_caption/features/trend.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np
from .utils import z_normalize

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
    修复版：在 diff 空间分段，再映射到 x 的 inclusive [start,end]
    diff index i 对应 (x[i] -> x[i+1])
    diff segment [s_diff, e_diff] => x segment [s_diff, e_diff+1]
    """
    x = np.asarray(x, float)
    z = z_normalize(x)
    n = len(z)
    if n < 2:
        return [{"start": 0, "end": n - 1, "label": 0, "slope": 0.0}]

    d = np.diff(z)  # len = n-1
    if len(d) == 0:
        return [{"start": 0, "end": n - 1, "label": 0, "slope": 0.0}]

    k = max(1, int(smooth_win))
    kernel = np.ones(k) / k
    d_pad = np.concatenate([d[:1], d, d[-1:]])
    ma = np.convolve(d_pad, kernel, mode="same")[1:-1]  # len n-1

    labels = np.zeros_like(ma, dtype=int)
    labels[ma > slope_eps] = 1
    labels[ma < -slope_eps] = -1

    # segments in diff space (inclusive)
    segs_diff = []
    cur = int(labels[0])
    s = 0
    for i in range(1, len(labels)):
        if int(labels[i]) != cur:
            segs_diff.append((s, i - 1, cur))
            s = i
            cur = int(labels[i])
    segs_diff.append((s, len(labels) - 1, cur))

    # merge short segments based on x-length
    merged = []
    for s_d, e_d, lab in segs_diff:
        x_s = s_d
        x_e = e_d + 1
        if merged:
            prev = merged[-1]
            prev_len = prev[1] - prev[0] + 1
            cur_len = x_e - x_s + 1
            if cur_len < min_seg_len:
                merged[-1] = (prev[0], x_e, prev[2])  # merge into prev
                continue
        merged.append((x_s, x_e, lab))

    segments = []
    for x_s, x_e, lab in merged:
        xs = np.arange(x_e - x_s + 1, dtype=float)
        ys = z[x_s:x_e + 1]
        if len(xs) < 2:
            slope = 0.0
        else:
            A = np.vstack([xs, np.ones_like(xs)]).T
            slope, _ = np.linalg.lstsq(A, ys, rcond=None)[0]
        segments.append({"start": int(x_s), "end": int(x_e), "label": int(lab), "slope": float(slope)})
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
        out.append(TrendSegment(start=start, end=end - 1, slope_z=float(slope), label=lab))
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
