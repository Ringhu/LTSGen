# ts_capv2/core/claims.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .features import (
    StructuredSummary,
    compute_trend_segments,
    summarize_global_trend,
    robust_scale,
    pct_change,
    z_normalize,
    estimate_dominant_period_acf,
    compute_volatility,
    compute_lagged_correlations_stable,
    detect_ramps,
    segment_by_slope_fixed,
)


@dataclass
class Claim:
    id: str
    type: str
    target: str

    start: Optional[int] = None
    end: Optional[int] = None
    idx: Optional[int] = None

    t_start: Optional[str] = None
    t_end: Optional[str] = None
    t_idx: Optional[str] = None

    data: Dict[str, Any] = None

    sentence: Optional[str] = None
    ok: Optional[bool] = None
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["data"] is None:
            d["data"] = {}
        return d


def _t_at(time_list: List[str], i: int) -> str:
    if not time_list:
        return ""
    i = max(0, min(int(i), len(time_list) - 1))
    return time_list[i]


# ---------------- budget policy (optional) ----------------
def apply_budget_policy(
    claims: List[Claim],
    max_peaks: int = 1,
    max_valleys: int = 1,
    max_corrs: int = 1,
) -> List[Claim]:
    peaks = [c for c in claims if c.type == "peak"]
    valleys = [c for c in claims if c.type == "valley"]
    others = [c for c in claims if c.type not in ("peak", "valley", "lagged_corr")]

    peaks = sorted(peaks, key=lambda c: -abs(float((c.data or {}).get("z", 0.0))))[:max_peaks]
    valleys = sorted(valleys, key=lambda c: -abs(float((c.data or {}).get("z", 0.0))))[:max_valleys]

    corrs = [c for c in claims if c.type == "lagged_corr"]
    stable = [c for c in corrs if bool((c.data or {}).get("stable", False))]
    unstable = [c for c in corrs if not bool((c.data or {}).get("stable", False))]

    kept_corrs: List[Claim] = []
    if stable:
        stable = sorted(stable, key=lambda c: -abs(float((c.data or {}).get("corr", 0.0))))
        kept_corrs = stable[:max_corrs]
    else:
        unstable = sorted(unstable, key=lambda c: -abs(float((c.data or {}).get("corr", 0.0))))
        kept_corrs = unstable[:max_corrs]

    return others + peaks + valleys + kept_corrs


# ---------------- phase claims ----------------
def build_phase_claims(
    x: np.ndarray,
    target_col: str,
    time_list: List[str],
    win: int = 5,
    slope_eps: float = 0.02,
    min_seg_len: int = 20,
    fallback_n: int = 3,
) -> List[Claim]:
    x = np.asarray(x, float)
    n = len(x)
    if n <= 1:
        return []

    segs = segment_by_slope_fixed(x, smooth_win=win, slope_eps=slope_eps, min_seg_len=min_seg_len)

    if segs is None or len(segs) < 2:
        cuts = [int(round(i * n / fallback_n)) for i in range(fallback_n)] + [n]
        segs = []
        for i in range(fallback_n):
            s = cuts[i]
            e = cuts[i + 1] - 1
            if e <= s:
                continue
            segs.append({"start": s, "end": e, "label": 0, "slope": 0.0})

    g_mean = float(np.mean(x))
    g_std = float(np.std(x))
    scale = max(abs(g_mean), g_std, 1e-8)

    claims: List[Claim] = []
    for i, seg in enumerate(segs):
        s, e = int(seg["start"]), int(seg["end"])
        s = max(0, min(s, n - 1))
        e = max(0, min(e, n - 1))
        if e <= s:
            continue

        xs = x[s : e + 1]
        start_v, end_v = float(x[s]), float(x[e])
        delta_v = end_v - start_v
        delta_pct = (delta_v / scale) * 100.0

        eps = 0.01 * scale
        if abs(delta_v) <= eps:
            label = "flat"
        elif delta_v > 0:
            label = "up"
        else:
            label = "down"

        min_idx_local = int(np.argmin(xs))
        max_idx_local = int(np.argmax(xs))
        min_idx = s + min_idx_local
        max_idx = s + max_idx_local

        data = {
            "label": label,
            "start_v": start_v,
            "end_v": end_v,
            "delta_v": float(delta_v),
            "delta_pct": float(delta_pct),
            "min_v": float(xs[min_idx_local]),
            "max_v": float(xs[max_idx_local]),
            "min_idx": int(min_idx),
            "max_idx": int(max_idx),
            "std": float(np.std(xs) / scale),
            "scale_def": "max(|global_mean|, global_std)",
            "tol_pct_points": 2.0,
        }

        claims.append(
            Claim(
                id=f"phase_{i}",
                type="phase",
                target=target_col,
                start=s,
                end=e,
                idx=None,
                t_start=_t_at(time_list, s),
                t_end=_t_at(time_list, e),
                t_idx=None,
                data=data,
                sentence=None,
                ok=None,
                reason="",
                evidence={},
            )
        )
    return claims


# ---------------- build claims ----------------
def build_claims(
    summary: StructuredSummary,
    target_col: str,
    x: np.ndarray,
    time_list: List[str],
    volatility_label: str,
) -> List[Claim]:
    x = np.asarray(x, float)
    n = len(x)
    scale = robust_scale(x)
    claims: List[Claim] = []

    claims.append(
        Claim(
            id="global_trend_label",
            type="global_trend_label",
            target=target_col,
            start=0,
            end=n - 1,
            t_start=_t_at(time_list, 0),
            t_end=_t_at(time_list, n - 1),
            data={"label": summary.global_trend_label},
        )
    )

    delta_pct = pct_change(float(x[0]), float(x[-1]), scale)
    claims.append(
        Claim(
            id="global_net_change",
            type="global_net_change",
            target=target_col,
            start=0,
            end=n - 1,
            t_start=_t_at(time_list, 0),
            t_end=_t_at(time_list, n - 1),
            data={
                "start_v": float(x[0]),
                "end_v": float(x[-1]),
                "delta_pct": float(delta_pct),
                "scale_def": "max(|mean|, std)",
                "tol_pct_points": 1.0,
            },
        )
    )

    ramps = detect_ramps(x, min_ramp_len=24, min_ramp_z_change=0.8, max_ramps=3)
    for k, r in enumerate(ramps):
        s, e = int(r["start"]), int(r["end"])
        claims.append(
            Claim(
                id=f"ramp_{k}",
                type="ramp",
                target=target_col,
                start=s,
                end=e,
                t_start=_t_at(time_list, s),
                t_end=_t_at(time_list, e),
                data={"kind": r["kind"], "delta_pct": float(r["delta_pct"]), "tol_pct_points": 2.0},
            )
        )

    claims.extend(build_phase_claims(x, target_col, time_list))

    vol = summary.volatility
    claims.append(
        Claim(
            id="volatility",
            type="volatility_most_segment",
            target=target_col,
            start=0,
            end=n - 1,
            t_start=_t_at(time_list, 0),
            t_end=_t_at(time_list, n - 1),
            data={
                "label": volatility_label,
                "n_segments": len(vol.segment_stds),
                "most": int(vol.most_volatile_segment),
                "segment_stds": [float(v) for v in vol.segment_stds],
            },
        )
    )

    for k, e in enumerate(sorted(summary.peaks, key=lambda ev: -abs(ev.z_value))[:3]):
        idx = int(e.index)
        claims.append(
            Claim(
                id=f"peak_{k}",
                type="peak",
                target=target_col,
                idx=idx,
                t_idx=_t_at(time_list, idx),
                data={
                    "value": float(x[idx]),
                    "z": float(e.z_value),
                    "delta_pct_vs_mean": float(e.delta_pct_vs_mean),
                    "tol_z": 0.2,
                    "min_z": 1.0,
                },
            )
        )

    for k, e in enumerate(sorted(summary.valleys, key=lambda ev: -abs(ev.z_value))[:3]):
        idx = int(e.index)
        claims.append(
            Claim(
                id=f"valley_{k}",
                type="valley",
                target=target_col,
                idx=idx,
                t_idx=_t_at(time_list, idx),
                data={
                    "value": float(x[idx]),
                    "z": float(e.z_value),
                    "delta_pct_vs_mean": float(e.delta_pct_vs_mean),
                    "tol_z": 0.2,
                    "max_z": -1.0,
                },
            )
        )

    seas = summary.seasonality
    claims.append(
        Claim(
            id="seasonality",
            type="seasonality",
            target=target_col,
            start=0,
            end=n - 1,
            t_start=_t_at(time_list, 0),
            t_end=_t_at(time_list, n - 1),
            data={
                "has": bool(seas.has_seasonality and seas.period is not None),
                "period": int(seas.period) if seas.period is not None else None,
                "strength": float(seas.strength),
                "tol_period": 1,
            },
        )
    )

    for k, ci in enumerate(summary.correlations):
        claims.append(
            Claim(
                id=f"corr_{k}",
                type="lagged_corr",
                target=target_col,
                data={
                    "var": ci.var,
                    "corr": float(ci.corr),
                    "lag": int(ci.lag),
                    "stable": bool(ci.stable),
                    "min_abs_corr": 0.3,
                    "tol_corr": 0.05,
                    "note": ci.stability_note,
                },
            )
        )

    return claims


# ---------------- consistency ----------------
def _find_one(claims: List[Claim], claim_type: str) -> Optional[Claim]:
    for c in claims:
        if c.type == claim_type:
            return c
    return None


def _find_all(claims: List[Claim], claim_type: str) -> List[Claim]:
    return [c for c in claims if c.type == claim_type]


def _repair_trend_label_from_evidence(claims: List[Claim], delta_thr: float = 10.0) -> None:
    trend = _find_one(claims, "global_trend_label")
    net = _find_one(claims, "global_net_change")
    ramps = _find_all(claims, "ramp")
    if trend is None or net is None:
        return

    d_tr = trend.data or {}
    label_raw = d_tr.get("label", None)
    delta = float((net.data or {}).get("delta_pct", 0.0))

    if label_raw != "flat" or abs(delta) < delta_thr:
        d_tr["label_raw"] = label_raw
        d_tr["label_final"] = label_raw
        trend.data = d_tr
        return

    kinds = [((r.data or {}).get("kind"), r.start, r.end) for r in ramps if r.start is not None and r.end is not None]
    has_up = any(k[0] == "ramp_up" for k in kinds)
    has_dn = any(k[0] == "ramp_down" for k in kinds)

    repaired = None
    if has_up and has_dn:
        kinds_sorted = sorted(kinds, key=lambda x: int(x[1]))
        first_kind = kinds_sorted[0][0]
        last_kind = kinds_sorted[-1][0]
        if first_kind == "ramp_down" and last_kind == "ramp_up":
            repaired = "down_then_up"
        elif first_kind == "ramp_up" and last_kind == "ramp_down":
            repaired = "up_then_down"

    if repaired is None:
        repaired = "up" if delta > 0 else "down"

    d_tr["label_raw"] = label_raw
    d_tr["label_final"] = repaired
    d_tr["repair"] = "flat_vs_delta"
    trend.data = d_tr
    trend.reason = (trend.reason or "") + "|repaired:flat_vs_delta"


def _inject_amplitude_note(claims: List[Claim], amp_thr: float = 30.0) -> None:
    vol = _find_one(claims, "volatility_most_segment")
    if vol is None:
        return
    if (vol.data or {}).get("label") != "low":
        return

    deltas = []
    for c in claims:
        if c.type in ("peak", "valley"):
            d = c.data or {}
            if "delta_pct_vs_mean" in d:
                deltas.append(abs(float(d["delta_pct_vs_mean"])))
    if not deltas:
        return
    if max(deltas) >= amp_thr:
        vol.data["note"] = "low_short_term_but_large_amplitude"


def apply_consistency_rules(claims: List[Claim]) -> List[Claim]:
    _repair_trend_label_from_evidence(claims, delta_thr=10.0)
    _inject_amplitude_note(claims, amp_thr=30.0)
    return claims


# ---------------- policy ----------------
def apply_claim_policy(claims: List[Claim], enforce: bool = True) -> List[Claim]:
    if not enforce:
        return claims

    kept: List[Claim] = []
    for c in claims:
        if c.ok is None:
            kept.append(c)
            continue
        if c.ok:
            kept.append(c)
            continue

        if c.type == "lagged_corr":
            d = c.data or {}
            d["stable"] = False
            c.data = d
            c.ok = True
            kept.append(c)
        elif c.type == "seasonality":
            d = c.data or {}
            d["has"] = False
            d["period"] = None
            c.data = d
            c.ok = True
            kept.append(c)
        else:
            pass

    if not any(c.type == "global_net_change" for c in kept):
        for c in claims:
            if c.type == "global_net_change":
                kept.insert(0, c)
                break

    return kept


# ---------------- validation ----------------
def _validate_phase(c: Claim, x: np.ndarray) -> Claim:
    d = c.data or {}
    s, e = int(c.start), int(c.end)
    xs = x[s : e + 1]

    g_mean = float(np.mean(x))
    g_std = float(np.std(x))
    scale = max(abs(g_mean), g_std, 1e-8)

    start_v = float(x[s])
    end_v = float(x[e])
    delta_pct = (end_v - start_v) / scale * 100.0

    ok = abs(delta_pct - float(d.get("delta_pct", 0.0))) <= float(d.get("tol_pct_points", 2.0))
    c.ok = bool(ok)
    c.evidence = {
        "recomputed_delta_pct": float(delta_pct),
        "recomputed_start_v": float(start_v),
        "recomputed_end_v": float(end_v),
        "min_v": float(np.min(xs)) if len(xs) else None,
        "max_v": float(np.max(xs)) if len(xs) else None,
    }
    if not ok:
        c.reason = (c.reason or "") + "|phase_delta_mismatch"
    return c


def validate_claim(
    c: Claim,
    series_map: Dict[str, np.ndarray],
    target_col: str,
) -> Claim:
    if target_col not in series_map:
        c.ok = False
        c.reason = "target missing"
        c.evidence = {}
        return c

    x = np.asarray(series_map[target_col], float)
    scale = robust_scale(x)

    t = c.type
    d = c.data or {}
    ok = True
    reason = ""
    evidence: Dict[str, Any] = {}

    if t == "phase":
        return _validate_phase(c, x)

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
        seas2 = estimate_dominant_period_acf(x, max_lag=min(200, len(x) // 2), detrend=True)
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
        if var is None or var not in series_map:
            ok = False
            reason = "var missing"
        else:
            res = compute_lagged_correlations_stable(
                series_map=series_map,
                target_col=target_col,
                candidate_cols=[var],
                top_k=1,
                max_lag=24,
                min_abs_corr=0.0,
            )
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


def validate_claims(claims: List[Claim], series_map: Dict[str, np.ndarray], target_col: str) -> Dict[str, Any]:
    checked = [validate_claim(c, series_map, target_col=target_col) for c in claims]
    checked = apply_consistency_rules(checked)
    failed = [c for c in checked if c.ok is False]
    return {
        "pass": len(failed) == 0,
        "n": len(checked),
        "n_failed": len(failed),
        "failed": [c.to_dict() for c in failed[:10]],
        "checked": checked,  # 方便上层继续用（不写入 json 也行）
    }
