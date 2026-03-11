# ts_caption/features/ramps.py
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
from .utils import z_normalize, robust_scale, pct_change
from .trend import segment_by_slope_fixed

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
    ramps = []
    for seg in segs:
        s, e, lab = int(seg["start"]), int(seg["end"]), int(seg["label"])
        length = e - s + 1
        if lab == 0 or length < min_ramp_len:
            continue
        delta_z = float(z[e] - z[s])
        if abs(delta_z) < min_ramp_z_change:
            continue
        delta_pct = float(pct_change(float(x[s]), float(x[e]), scale))
        ramps.append({
            "kind": "ramp_up" if lab > 0 else "ramp_down",
            "start": s, "end": e,
            "delta_z": delta_z,
            "delta_pct": delta_pct,
        })

    ramps = sorted(ramps, key=lambda r: -abs(r["delta_z"]))
    selected = []
    used = np.zeros(n, dtype=bool)
    for r in ramps:
        s, e = r["start"], r["end"]
        if used[s:e + 1].mean() > 0.3:
            continue
        selected.append(r)
        used[s:e + 1] = True
        if len(selected) >= max_ramps:
            break
    return selected
