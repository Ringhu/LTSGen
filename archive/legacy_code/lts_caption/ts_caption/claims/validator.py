# ts_caption/claims/validator.py
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from .schema import Claim
from ts_caption.features.utils import z_normalize, robust_scale, pct_change
from ts_caption.features.trend import compute_trend_segments, summarize_global_trend
from ts_caption.features.seasonality import estimate_dominant_period_acf
from ts_caption.features.volatility import compute_volatility
from ts_caption.features.correlation import compute_lagged_correlations_stable
from ts_caption.claims.consistency import apply_consistency_rules


def _validate_phase(claim, win_df, time_col: str):
    d = claim.data or {}
    x = win_df[claim.target].to_numpy(dtype=float)
    s, e = int(claim.start), int(claim.end)
    xs = x[s:e+1]

    g_mean = float(np.mean(x))
    g_std = float(np.std(x))
    scale = max(abs(g_mean), g_std, 1e-8)

    start_v = float(x[s]); end_v = float(x[e])
    delta_pct = (end_v - start_v) / scale * 100.0

    ok = abs(delta_pct - float(d.get("delta_pct", 0.0))) <= float(d.get("tol_pct_points", 2.0))
    claim.ok = bool(ok)
    claim.evidence = {
        "recomputed_delta_pct": delta_pct,
        "recomputed_start_v": start_v,
        "recomputed_end_v": end_v,
    }
    if not ok:
        claim.reason = (claim.reason or "") + "|phase_delta_mismatch"
    return claim

def validate_claim(c: Claim, win_df: pd.DataFrame, time_col: str) -> Claim:
    x = win_df[c.target].to_numpy(dtype=float)
    x = np.asarray(x, float)
    scale = robust_scale(x)

    t = c.type
    d = c.data or {}
    ok = True
    reason = ""
    evidence: Dict[str, Any] = {}

    # 1. 校验 phase 类型的 claim
    if t == "phase":
        return _validate_phase(c, win_df, time_col)

    # 2. 处理其他类型的 claim
    if t == "global_trend_label":
        segs = compute_trend_segments(x, n_segments=3)
        lab2 = summarize_global_trend(segs)
        ok = (lab2 == d.get("label"))
        evidence = {"recomputed_label": lab2}

    elif t == "global_net_change":
        start_v, end_v = float(x[0]), float(x[-1])
        delta2 = pct_change(start_v, end_v, scale)
        tol = float(d.get("tol_pct_points", 1.0))
        ok = abs(delta2 - float(d.get("delta_pct"))) <= tol
        evidence = {"recomputed_delta_pct": float(delta2)}

    elif t == "ramp":
        s, e = int(c.start), int(c.end)
        delta2 = pct_change(float(x[s]), float(x[e]), scale)
        tol = float(d.get("tol_pct_points", 2.0))
        ok = abs(delta2 - float(d.get("delta_pct"))) <= tol
        evidence = {"recomputed_delta_pct": float(delta2)}

    elif t in ("peak", "valley"):
        idx = int(c.idx)
        z = z_normalize(x)
        z2 = float(z[idx])
        tol_z = float(d.get("tol_z", 0.2))
        ok = abs(z2 - float(d.get("z"))) <= tol_z
        if t == "peak":
            ok = ok and (z2 >= float(d.get("min_z", 1.0)))
        else:
            ok = ok and (z2 <= float(d.get("max_z", -1.0)))
        evidence = {"recomputed_z": z2}

    elif t == "seasonality":
        seas2 = estimate_dominant_period_acf(x, max_lag=min(200, len(x)//2), detrend=True)
        has2 = bool(seas2.has_seasonality and seas2.period is not None)
        ok = (has2 == bool(d.get("has")))
        if has2 and d.get("period") is not None:
            ok = ok and (abs(int(seas2.period) - int(d["period"])) <= int(d.get("tol_period", 1)))
        evidence = {"recomputed_has": has2, "recomputed_period": seas2.period, "recomputed_strength": seas2.strength}

    elif t == "volatility_most_segment":
        nseg = int(d.get("n_segments", 3))
        vol2 = compute_volatility(x, n_segments=nseg)
        ok = int(vol2.most_volatile_segment) == int(d.get("most"))
        evidence = {"recomputed_most": int(vol2.most_volatile_segment)}

    elif t == "lagged_corr":
        var = d.get("var")
        if var is None or var not in win_df.columns:
            ok = False
            reason = "var missing"
        else:
            df2 = win_df[[time_col, c.target, var]].copy()
            res = compute_lagged_correlations_stable(df2, target_col=c.target, candidate_cols=[c.target, var], top_k=1, max_lag=24, min_abs_corr=0.0)
            if not res:
                ok = False
                reason = "recompute failed"
            else:
                ci = res[0]
                if ci.corr is None or (isinstance(ci.corr, float) and np.isnan(ci.corr)):
                    ok = False
                    reason = "recomputed corr is nan (std≈0 or insufficient valid points)"
                else:
                    tol = float(d.get("tol_corr", 0.05))
                    ok = (abs(ci.corr - float(d.get("corr"))) <= tol) and (int(ci.lag) == int(d.get("lag")))
                    ok = ok and (abs(ci.corr) >= float(d.get("min_abs_corr", 0.3)))
                    evidence = {"recomputed_corr": float(ci.corr), "recomputed_lag": int(ci.lag), "recomputed_stable": bool(ci.stable)}

    c.ok = bool(ok)
    c.reason = reason
    c.evidence = evidence
    return c

def validate_claims(claims: List[Claim], win_df: pd.DataFrame, time_col: str) -> Dict[str, Any]:
    checked = [validate_claim(c, win_df, time_col) for c in claims]
    checked = apply_consistency_rules(checked)   # <--- 新增
    failed = [c for c in checked if c.ok is False]
    return {
        "pass": len(failed) == 0,
        "n": len(checked),
        "n_failed": len(failed),
        "failed": [c.to_dict() for c in failed[:10]],
    }
