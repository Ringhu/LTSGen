# ts_caption/claims/builder.py
from __future__ import annotations
from typing import List
import numpy as np
from .schema import Claim
from ts_caption.features.utils import robust_scale, pct_change
from ts_caption.features.ramps import detect_ramps
from ts_caption.features.trend import segment_by_slope_fixed


def _t_at(time_list, i: int) -> str:
    if not time_list:
        return ""
    i = max(0, min(int(i), len(time_list) - 1))
    return time_list[i]

def build_phase_claims(
    x: np.ndarray,
    target_col: str,
    time_list: list[str],
    win: int = 5,
    slope_eps: float = 0.02,
    min_seg_len: int = 20,
    fallback_n: int = 3,
) -> list[Claim]:
    """
    把整段序列切成若干“阶段”，用于覆盖全序列变化。
    注意：phase 的 label 用该段起止值判断（避免 label 与 end-start 矛盾）。
    """
    x = np.asarray(x, float)
    n = len(x)
    if n <= 1:
        return []

    # 1) 主分段：按斜率分段（参数名是 smooth_win）
    segs = segment_by_slope_fixed(
        x,
        smooth_win=win,               # ✅ 修复：win -> smooth_win
        slope_eps=slope_eps,
        min_seg_len=min_seg_len
    )

    # 2) fallback：如果只分出 0/1 段，改用均匀切成 fallback_n 段，保证“分阶段”真的有阶段
    if segs is None or len(segs) < 2:
        cuts = [int(round(i * n / fallback_n)) for i in range(fallback_n)] + [n]
        segs = []
        for i in range(fallback_n):
            s = cuts[i]
            e = cuts[i + 1] - 1
            if e <= s:
                continue
            segs.append({"start": s, "end": e, "label": 0, "slope": 0.0})

    # 统一尺度（用于 delta_pct 校验；正文不一定用 percent）
    g_mean = float(np.mean(x))
    g_std = float(np.std(x))
    scale = max(abs(g_mean), g_std, 1e-8)

    claims: list[Claim] = []
    for i, seg in enumerate(segs):
        s, e = int(seg["start"]), int(seg["end"])
        s = max(0, min(s, n - 1))
        e = max(0, min(e, n - 1))
        if e <= s:
            continue

        xs = x[s:e + 1]
        start_v, end_v = float(x[s]), float(x[e])
        delta_v = end_v - start_v
        delta_pct = (delta_v / scale) * 100.0

        # ✅ phase 方向用该段净变化决定（避免“以下探为主但从 30→38”的违和）
        # 阈值用 scale 的一小部分判断 flat
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
            "delta_pct": float(delta_pct),          # 仍保留用于自动校验
            "min_v": float(xs[min_idx_local]),
            "max_v": float(xs[max_idx_local]),
            "min_idx": int(min_idx),
            "max_idx": int(max_idx),
            "std": float(np.std(xs) / scale),
            "scale_def": "max(|global_mean|, global_std)",
            "tol_pct_points": 2.0,
        }

        claims.append(Claim(
            id=f"phase_{i}",
            type="phase",
            target=target_col,
            start=s, end=e,
            idx=None,
            t_start=_t_at(time_list, s),
            t_end=_t_at(time_list, e),
            t_idx=None,
            data=data,
            sentence=None,
            ok=None,
            reason="",
            evidence={}
        ))
    return claims


def build_claims(
    summary,
    target_col: str,
    x: np.ndarray,
    time_list: List[str],
    volatility_label: str,
) -> List[Claim]:
    x = np.asarray(x, float)
    n = len(x)
    scale = robust_scale(x)
    claims: List[Claim] = []

    # global trend label (隐式也行，这里保留为可校验 claim)
    claims.append(Claim(
        id="global_trend_label",
        type="global_trend_label",
        target=target_col,
        start=0, end=n-1,
        t_start=_t_at(time_list, 0),
        t_end=_t_at(time_list, n-1),
        data={"label": summary.global_trend_label},
    ))

    # global net change
    delta_pct = pct_change(float(x[0]), float(x[-1]), scale)
    claims.append(Claim(
        id="global_net_change",
        type="global_net_change",
        target=target_col,
        start=0, end=n-1,
        t_start=_t_at(time_list, 0),
        t_end=_t_at(time_list, n-1),
        data={
            "start_v": float(x[0]),
            "end_v": float(x[-1]),
            "delta_pct": float(delta_pct),
            "scale_def": "max(|mean|, std)",
            "tol_pct_points": 1.0,
        },
    ))

    # ramps
    ramps = detect_ramps(x, min_ramp_len=24, min_ramp_z_change=0.8, max_ramps=3)
    for k, r in enumerate(ramps):
        s, e = int(r["start"]), int(r["end"])
        claims.append(Claim(
            id=f"ramp_{k}",
            type="ramp",
            target=target_col,
            start=s, end=e,
            t_start=_t_at(time_list, s),
            t_end=_t_at(time_list, e),
            data={
                "kind": r["kind"],
                "delta_pct": float(r["delta_pct"]),
                "tol_pct_points": 2.0,
            },
        ))

    claims.extend(build_phase_claims(x, target_col, time_list))  # 添加 phase claims
    # volatility
    vol = summary.volatility
    claims.append(Claim(
        id="volatility",
        type="volatility_most_segment",
        target=target_col,
        start=0, end=n-1,
        t_start=_t_at(time_list, 0),
        t_end=_t_at(time_list, n-1),
        data={
            "label": volatility_label,
            "n_segments": len(vol.segment_stds),
            "most": int(vol.most_volatile_segment),
            "segment_stds": [float(v) for v in vol.segment_stds],
        },
    ))

    # peaks/valleys (取 z 最大的前2~3个即可)
    for k, e in enumerate(sorted(summary.peaks, key=lambda ev: -abs(ev.z_value))[:3]):
        idx = int(e.index)
        claims.append(Claim(
            id=f"peak_{k}",
            type="peak",
            target=target_col,
            idx=idx,
            t_idx=_t_at(time_list, idx),
            data={"value": float(x[idx]), "z": float(e.z_value), "delta_pct_vs_mean": float(e.delta_pct_vs_mean), "tol_z": 0.2, "min_z": 1.0},
        ))

    for k, e in enumerate(sorted(summary.valleys, key=lambda ev: -abs(ev.z_value))[:3]):
        idx = int(e.index)
        claims.append(Claim(
            id=f"valley_{k}",
            type="valley",
            target=target_col,
            idx=idx,
            t_idx=_t_at(time_list, idx),
            data={"value": float(x[idx]), "z": float(e.z_value), "delta_pct_vs_mean": float(e.delta_pct_vs_mean), "tol_z": 0.2, "max_z": -1.0},
        ))

    # seasonality
    seas = summary.seasonality
    claims.append(Claim(
        id="seasonality",
        type="seasonality",
        target=target_col,
        start=0, end=n-1,
        t_start=_t_at(time_list, 0),
        t_end=_t_at(time_list, n-1),
        data={
            "has": bool(seas.has_seasonality and seas.period is not None),
            "period": int(seas.period) if seas.period is not None else None,
            "strength": float(seas.strength),
            "tol_period": 1,
        }
    ))

    # correlations (只输出 stable 的；不稳定也可当 claim 存下来但 renderer 降语气)
    for k, ci in enumerate(summary.correlations):
        claims.append(Claim(
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
            }
        ))

    return claims