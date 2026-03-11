# ts_cap/core/samples.py
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .features import (
    StructuredSummary,
    compute_trend_segments,
    summarize_global_trend,
    compute_volatility,
    detect_peaks_and_valleys,
    estimate_dominant_period_robust,
    compute_lagged_correlations_stable,
    volatility_label,
    seasonality_strength_label,
)
from .claims import (
    Claim,
    build_claims,
    validate_claims,
    apply_claim_policy,
    apply_consistency_rules,
)
from .prompts import SYSTEM_PROMPT_TEMPLATE, build_user_prompt
from .llm_schemas import HierarchicalCaption
from ts_cap.utils.openai_chat import OpenAIChatClient

logger = logging.getLogger(__name__)


def _round_floats(obj: Any, digits: int = 4) -> Any:
    """递归数值修剪"""
    if isinstance(obj, float):
        return round(obj, digits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, digits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(x, digits) for x in obj]
    return obj


import math
from typing import Any, Dict, List, Optional, Tuple


def _phase_importance_score(p: Dict[str, Any]) -> float:
    d = p.get("data") or {}

    # 1) 幅度（最关键）
    delta_pct = d.get("delta_pct")
    try:
        amp = abs(float(delta_pct)) if delta_pct is not None else 0.0
    except Exception:
        amp = 0.0

    # 2) 长度（log 降权）
    s = p.get("start")
    e = p.get("end")
    try:
        length = max(1, int(e) - int(s) + 1)
    except Exception:
        length = 1
    len_term = math.log1p(length)

    # 3) 段内波动（phase.std 是归一化后的 std）
    try:
        std = float(d.get("std", 0.0) or 0.0)
    except Exception:
        std = 0.0

    # 4) 突刺/深蹲 bonus（与 render_zh 的判断尽量一致）
    has_spike_or_dip = 0.0
    try:
        sv0 = d.get("start_v")
        ev0 = d.get("end_v")
        mn0 = d.get("min_v")
        mx0 = d.get("max_v")
        if sv0 is not None and ev0 is not None:
            sv0 = float(sv0)
            ev0 = float(ev0)
            base_min = min(sv0, ev0)
            base_max = max(sv0, ev0)
            span = abs(ev0 - sv0)
            thr = max(span * 1.5, abs(sv0) * 0.05, 1e-8)

            if mx0 is not None and float(mx0) > base_max + thr:
                has_spike_or_dip = 1.0
            if mn0 is not None and float(mn0) < base_min - thr:
                has_spike_or_dip = 1.0
    except Exception:
        pass

    # 权重（可调）
    score = (
        1.0 * amp +        # 幅度主导
        3.0 * len_term +   # 长度适度加成
        50.0 * std +       # 段内波动（std）加成
        10.0 * has_spike_or_dip
    )
    return float(score)


def _seg_iou(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """Index-based IoU for segments [start,end] inclusive."""
    try:
        a0, a1 = int(a.get("start", 0)), int(a.get("end", 0))
        b0, b1 = int(b.get("start", 0)), int(b.get("end", 0))
    except Exception:
        return 0.0
    if a1 < a0:
        a0, a1 = a1, a0
    if b1 < b0:
        b0, b1 = b1, b0

    inter = max(0, min(a1, b1) - max(a0, b0) + 1)
    if inter <= 0:
        return 0.0
    union = (a1 - a0 + 1) + (b1 - b0 + 1) - inter
    return float(inter) / float(max(union, 1))


def _bucket_id(start_idx: int, global_s: int, global_e: int, k: int) -> int:
    span = max(1, global_e - global_s + 1)
    pos = (start_idx - global_s) / span  # 0~1
    b = int(pos * k)
    if b < 0:
        b = 0
    if b >= k:
        b = k - 1
    return b


def _select_phases_mmr(
    phases: List[Dict[str, Any]],
    k: int = 5,
    n_buckets: Optional[int] = None,
    lambda_iou: float = 25.0,
    coverage_bonus: float = 8.0,
) -> List[Dict[str, Any]]:
    """
    MMR 选择：
      argmax_p [ base_score(p) - lambda_iou * max_iou(p, selected) + coverage_bonus * is_new_bucket(p) ]

    - lambda_iou 越大：越强调“别重叠”（多样性更强）
    - coverage_bonus 越大：越强调时间覆盖（更分散）
    """
    if not phases:
        return []

    nb = int(n_buckets or k)

    # global range
    starts, ends = [], []
    for p in phases:
        try:
            starts.append(int(p.get("start", 0)))
            ends.append(int(p.get("end", 0)))
        except Exception:
            continue
    if not starts or not ends:
        phases_sorted = sorted(phases, key=_phase_importance_score, reverse=True)
        return phases_sorted[:k]

    global_s, global_e = min(starts), max(ends)

    # 预计算 base score + bucket
    enriched: List[Tuple[Dict[str, Any], float, int]] = []
    for p in phases:
        try:
            s = int(p.get("start", global_s))
        except Exception:
            s = global_s
        b = _bucket_id(s, global_s, global_e, nb)
        enriched.append((p, _phase_importance_score(p), b))

    # 先保证“绝对最强”不会被多样性误伤：先把 top-1 base score 选入
    enriched.sort(key=lambda x: x[1], reverse=True)
    selected: List[Dict[str, Any]] = []
    used_buckets = set()

    def take(p: Dict[str, Any], b: int) -> None:
        selected.append(p)
        used_buckets.add(b)

    take(enriched[0][0], enriched[0][2])

    # 迭代 MMR
    remaining = enriched[1:]
    while remaining and len(selected) < k:
        best_idx = -1
        best_val = -1e18

        for i, (p, base, b) in enumerate(remaining):
            # diversity: max IoU to selected
            if selected:
                max_iou = max(_seg_iou(p, q) for q in selected)
            else:
                max_iou = 0.0

            cov = 1.0 if b not in used_buckets else 0.0
            mmr = base - lambda_iou * max_iou + coverage_bonus * cov

            if mmr > best_val:
                best_val = mmr
                best_idx = i

        p_best, base_best, b_best = remaining.pop(best_idx)
        take(p_best, b_best)

    # 若仍不足 k（极端情况），用 base score 补齐
    if len(selected) < k:
        leftover = [p for (p, _, _) in remaining]
        leftover.sort(key=_phase_importance_score, reverse=True)
        selected.extend(leftover[: (k - len(selected))])

    # 按时间排序输出（利于叙述）
    selected = selected[:k]
    selected.sort(key=lambda x: int(x.get("start", 0) or 0))
    return selected

def _select_target_segments(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    targets: List[Dict[str, Any]] = []
    seg_id = 0

    # -------- phase: MMR 选最重要的 5 段 --------
    MAX_PHASES = 5
    phases = [c for c in claims if c.get("type") == "phase"]

    chosen_phases = _select_phases_mmr(
        phases,
        k=MAX_PHASES,
        n_buckets=MAX_PHASES,   # 5 个桶（覆盖用）
        lambda_iou=25.0,        # 重叠惩罚强度（可调）
        coverage_bonus=8.0,     # 覆盖奖励（可调）
    )

    for p in chosen_phases:
        targets.append(
            {
                "segment_id": seg_id,
                "type": "phase",
                "start": p.get("start"),
                "end": p.get("end"),
                "info": (
                    f"Trend: {(p.get('data') or {}).get('label')}, "
                    f"Change: {(p.get('data') or {}).get('delta_pct')}%, "
                    f"score={_phase_importance_score(p):.2f}"
                ),
            }
        )
        seg_id += 1

    # -------- ramps: Top-2（保持原逻辑）--------
    ramps = [c for c in claims if c.get("type") == "ramp"]
    ramps.sort(key=lambda x: abs((x.get("data") or {}).get("delta_pct", 0) or 0), reverse=True)
    for r in ramps[:2]:
        targets.append(
            {
                "segment_id": seg_id,
                "type": "ramp",
                "start": r.get("start"),
                "end": r.get("end"),
                "info": f"Ramp: {(r.get('data') or {}).get('kind')}, Change: {(r.get('data') or {}).get('delta_pct')}%",
            }
        )
        seg_id += 1

    # -------- extremes: Top-2（保持原逻辑）--------
    extremes = [c for c in claims if c.get("type") in ("peak", "valley")]
    extremes.sort(key=lambda x: abs((x.get("data") or {}).get("z", 0) or 0), reverse=True)
    for e in extremes[:2]:
        idx = e.get("idx")
        targets.append(
            {
                "segment_id": seg_id,
                "type": e.get("type"),
                "start": idx,
                "end": idx,
                "info": f"{e.get('type')} at {idx}, value={(e.get('data') or {}).get('value')}",
            }
        )
        seg_id += 1

    return targets



def analyze_window(
    meta: Dict[str, Any],
    series_map: Dict[str, np.ndarray],
    target_col: str,
    series_cols: List[str],
) -> StructuredSummary:
    x = np.asarray(series_map[target_col], float)

    trend_segments = compute_trend_segments(x, n_segments=3)
    global_trend = summarize_global_trend(trend_segments)
    vol = compute_volatility(x, n_segments=3)
    peaks, valleys = detect_peaks_and_valleys(x, z_thresh=1.0, min_distance=5)
    seas = estimate_dominant_period_robust(x, max_lag=min(200, len(x) // 2))

    corr = []
    if len(series_cols) > 1:
        corr = compute_lagged_correlations_stable(
            series_map=series_map,
            target_col=target_col,
            candidate_cols=series_cols,
            top_k=3,
            max_lag=24,
            min_abs_corr=0.3,
        )

    return StructuredSummary(
        meta=meta,
        global_trend_label=global_trend,
        trend_segments=trend_segments,
        volatility=vol,
        peaks=peaks,
        valleys=valleys,
        seasonality=seas,
        correlations=corr,
    )


def generate_sample(
    *,
    timestamps: List[str],
    values: Sequence[Sequence[float]],
    series_cols: List[str],
    target_col: str,
    dataset_name: str,
    task: str,
    series_key: str = "series_0",
    indices: Optional[Tuple[int, int]] = None,
    variables_meta: Optional[List[Dict[str, Any]]] = None,
    label: Optional[Dict[str, Any]] = None,
    domain_context: Optional[Dict[str, Any]] = None,
    enforce_claims: bool = True,
    llm_enabled: bool = True,
    seed: Optional[int] = None,
    llm_client: Optional[OpenAIChatClient] = None,
) -> Dict[str, Any]:
    """
    关键增强：
    - llm_client 可从外部传入（用于线程池内复用 thread-local client，避免每条样本都 new）
    - dense_captions.local 补齐 t_start/t_end（与你给出的样本一致）
    """
    if indices is None:
        indices = (0, len(values))

    arr = np.asarray(values, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"values must be 2D (T,D), got shape={arr.shape}")

    T, D = arr.shape
    if T == 0:
        raise ValueError("Empty timeseries window (T==0)")

    if len(timestamps) != T:
        # timestamps 必须和 values 对齐
        raise ValueError(f"timestamps length {len(timestamps)} != values length {T}")

    series_map = {name: np.asarray(arr[:, i], float) for i, name in enumerate(series_cols)}
    x_target = np.asarray(series_map[target_col], float)

    meta = {
        "dataset": dataset_name,
        "task": task,
        "series_key": series_key,
        "indices": list(indices),
        "length": T,
        "t_start": timestamps[0],
        "t_end": timestamps[-1],
        "target_col": target_col,
        "variables": variables_meta,
    }

    # --- Math & Claims ---
    summary = analyze_window(meta, series_map, target_col, series_cols)
    features = {
        "trend": summary.global_trend_label,
        "seasonality": seasonality_strength_label(summary.seasonality),
        "volatility": volatility_label(x_target),
        "correlations": [{"pair": [c.var, target_col], "rho": c.corr} for c in summary.correlations],
    }

    raw_claims = build_claims(summary, target_col, x_target, timestamps, features["volatility"])
    check_result = validate_claims(raw_claims, series_map, target_col)
    checked_claims: List[Claim] = check_result["checked"]
    checked_claims = apply_consistency_rules(checked_claims)
    checked_claims = apply_claim_policy(checked_claims, enforce=enforce_claims)

    claims_list = [c.to_dict() for c in checked_claims]

    # 数值清洗（输出更干净）
    features = _round_floats(features, 2)
    claims_list = _round_floats(claims_list, 4)

    # --- Target segments ---
    target_segments = _select_target_segments(claims_list)
    target_segments = _round_floats(target_segments, 4)

    # --- LLM Generation ---
    caption_data = None
    final_local_captions: List[Dict[str, Any]] = []

    if llm_enabled:
        client = llm_client or OpenAIChatClient()

        user_prompt = build_user_prompt(
            meta,
            features,
            claims_list,
            domain_context or {},
            target_segments,
        )

        structured_out: Optional[HierarchicalCaption] = client.generate_structured_caption(
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT_TEMPLATE,
        )

        if structured_out:
            # segment_id -> description
            llm_locals_map = {item.segment_id: item.description for item in structured_out.local_captions}

            for tgt in target_segments:
                sid = tgt["segment_id"]
                desc = llm_locals_map.get(sid)

                s = int(tgt["start"])
                e = int(tgt["end"])
                s = max(0, min(s, T - 1))
                e = max(0, min(e, T - 1))

                final_segment = {
                    "start": s,
                    "end": e,
                    "t_start": timestamps[s],
                    "t_end": timestamps[e],
                    "type": tgt["type"],
                    "description_zh": desc.zh if desc else "生成缺失",
                    "description_en": desc.en if desc else "Missing generation",
                }
                final_local_captions.append(final_segment)

            domain_dict = {"zh": "", "en": ""}
            if structured_out.domain_summary:
                domain_dict = {"zh": structured_out.domain_summary.zh, "en": structured_out.domain_summary.en}

            caption_data = {
                "global": {"zh": structured_out.global_summary.zh, "en": structured_out.global_summary.en},
                "domain_integrated": domain_dict,
                "local": final_local_captions,
                "time_kind": "index",  # wrapper 若给真实 timestamp，也保留在 time 字段里；这里仅标注语义
            }
        else:
            logger.warning(f"LLM generation failed for series_key={series_key}")

    global_zh = caption_data["global"]["zh"] if caption_data else ""
    domain_zh = caption_data.get("domain_integrated", {}).get("zh", "") if caption_data else ""

    record = {
        "dataset": dataset_name,
        "task": task,
        "series_key": series_key,
        "indices": list(indices),
        "time": list(timestamps),
        "timeseries": arr.tolist(),
        "variables": variables_meta,
        "label": label,
        "features": features,
        "claims": claims_list,
        "claim_check": {"pass": check_result["pass"], "n_failed": check_result["n_failed"]},
        "descriptions": [global_zh, domain_zh],
        "dense_captions": caption_data,
        "domain_context": domain_context or {},
    }
    return record
