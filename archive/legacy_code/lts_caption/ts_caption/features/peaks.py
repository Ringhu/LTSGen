# ts_caption/features/peaks.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from .utils import z_normalize, robust_scale, pct_change

@dataclass
class PeakValleyEvent:
    kind: str   # peak / valley
    index: int
    z_value: float
    delta_pct_vs_mean: float  # 稳健尺度口径下相对均值的变化百分比

def detect_peaks_and_valleys(x: np.ndarray, z_thresh: float = 1.0, min_distance: int = 5) -> Tuple[List[PeakValleyEvent], List[PeakValleyEvent]]:
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

    peaks, valleys = [], []
    for idx in thin(cand_p):
        d = pct_change(mean, float(x[idx]), scale)
        peaks.append(PeakValleyEvent("peak", int(idx), float(z[idx]), float(d)))
    for idx in thin(cand_v):
        d = pct_change(mean, float(x[idx]), scale)
        valleys.append(PeakValleyEvent("valley", int(idx), float(z[idx]), float(d)))
    return peaks, valleys
