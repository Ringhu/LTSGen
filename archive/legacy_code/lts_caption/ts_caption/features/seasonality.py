# ts_caption/features/seasonality.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np
from .utils import detrend_linear

@dataclass
class SeasonalityInfo:
    has_seasonality: bool
    period: Optional[int]
    strength: float

def estimate_dominant_period_acf(
    x: np.ndarray,
    max_lag: int = 200,
    min_strength: float = 0.3,
    detrend: bool = True
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
                best_lag = i + 1  # acf[0] -> lag=1

    if best_lag is None:
        return SeasonalityInfo(False, None, float(np.max(acf)) if len(acf) else 0.0)
    return SeasonalityInfo(True, int(best_lag), float(best_strength))

def seasonality_strength_label(info: SeasonalityInfo) -> dict:
    if not info.has_seasonality or info.period is None:
        return {"period": None, "strength": "none"}
    s = info.strength
    if s >= 0.6:
        lab = "strong"
    elif s >= 0.4:
        lab = "medium"
    elif s >= 0.25:
        lab = "weak"
    else:
        lab = "none"
    return {"period": info.period, "strength": lab}
