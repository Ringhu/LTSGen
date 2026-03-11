# ts_caption/features/volatility.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import numpy as np
from .utils import z_normalize

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
