# ts_caption/features/utils.py
from __future__ import annotations
import numpy as np

def z_normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    m = float(np.mean(x))
    s = float(np.std(x))
    if s < 1e-8:
        return np.zeros_like(x)
    return (x - m) / s

def robust_scale(x: np.ndarray, eps: float = 1e-8) -> float:
    """
    用 max(|mean|, std, eps) 作为尺度，避免 mean≈0 时百分比爆炸
    """
    x = np.asarray(x, float)
    m = float(np.mean(x))
    s = float(np.std(x))
    return max(abs(m), s, eps)

def pct_change(a: float, b: float, scale: float) -> float:
    return (b - a) / scale * 100.0

def detrend_linear(x: np.ndarray) -> np.ndarray:
    """
    线性去趋势：x - (k*t+b)
    """
    x = np.asarray(x, float)
    n = len(x)
    if n < 3:
        return x - float(np.mean(x)) if n else x
    t = np.arange(n, dtype=float)
    A = np.vstack([t, np.ones_like(t)]).T
    k, b = np.linalg.lstsq(A, x, rcond=None)[0]
    return x - (k * t + b)
