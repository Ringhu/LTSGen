# ts_caption/claims/consistency.py
from __future__ import annotations
from typing import List, Optional
from ts_caption.claims.schema import Claim

def _find_one(claims: List[Claim], claim_type: str) -> Optional[Claim]:
    for c in claims:
        if c.type == claim_type:
            return c
    return None

def _find_all(claims: List[Claim], claim_type: str) -> List[Claim]:
    return [c for c in claims if c.type == claim_type]

def _repair_trend_label_from_evidence(claims, delta_thr: float = 10.0) -> None:
    trend = _find_one(claims, "global_trend_label")
    net = _find_one(claims, "global_net_change")
    ramps = _find_all(claims, "ramp")
    if trend is None or net is None:
        return

    d_tr = trend.data or {}
    label_raw = d_tr.get("label", None)
    delta = float((net.data or {}).get("delta_pct", 0.0))

    # 只对 raw=flat 且净变化足够大时触发
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
        kinds_sorted = sorted(kinds, key=lambda x: x[1])
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
    """
    规则：如果 volatility label=low 但峰谷相对均值变化很大（>|amp_thr|），
    给 volatility claim 加一个 note，让 renderer 写成“短期波动低但振幅大”。
    """
    vol = _find_one(claims, "volatility_most_segment")
    if vol is None:
        return
    if (vol.data or {}).get("label") != "low":
        return

    # 看 peak/valley 的 delta_pct_vs_mean（你 builder 里已经存了）
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
    """
    统一入口：在逐条 validator 之后调用
    """
    _repair_trend_label_from_evidence(claims, delta_thr=10.0)
    _inject_amplitude_note(claims, amp_thr=30.0)
    return claims
