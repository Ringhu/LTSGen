# ts_capv2/core/samples.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .features import (
    StructuredSummary,
    compute_trend_segments,
    summarize_global_trend,
    compute_volatility,
    detect_peaks_and_valleys,
    estimate_dominant_period_robust,  # Changed from _acf
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
from .render_zh import render_caption_zh


@dataclass
class CoreMeta:
    dataset: str
    task: str
    series_key: str
    indices: Tuple[int, int]


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
    
    # Updated to use Robust (FFT + ACF) estimator
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


def build_features(summary: StructuredSummary, x_target: np.ndarray, target_col: str) -> Dict[str, Any]:
    vol_lab = volatility_label(x_target)
    seas_lab = seasonality_strength_label(summary.seasonality)
    corr_feature = [
        {"pair": [ci.var, target_col], "rho": ci.corr, "lag": ci.lag, "stable": ci.stable} for ci in summary.correlations
    ]
    return {
        "trend": summary.global_trend_label,
        "seasonality": seas_lab,
        "volatility": vol_lab,
        "correlations": corr_feature,
    }


def _light_validate_caption(s: Any) -> Optional[str]:
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    if len(s) < 4:
        return None
    return s


def generate_sample(
    *,
    timestamps: List[str],
    values: Sequence[Sequence[float]],
    series_cols: List[str],
    target_col: str,
    dataset_name: str,
    task: str,
    series_key: str = "series_0",
    indices: Tuple[int, int] = (0, 0),
    variables_meta: Optional[List[Dict[str, Any]]] = None,
    label: Optional[Dict[str, Any]] = None,
    domain_context: Optional[Dict[str, Any]] = None,
    enforce_claims: bool = True,
    caption_lang: str = "zh",
    caption_style: str = "human",
    llm_hook: Optional[Callable[[Dict[str, Any]], str]] = None,
    llm_enabled: bool = False,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    if caption_lang != "zh":
        raise ValueError("This refactor currently implements zh renderer only.")

    if len(timestamps) == 0:
        raise ValueError("timestamps is empty.")
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"values must be 2D array-like, got shape={arr.shape}")
    T, D = arr.shape
    if indices is None:
        indices = (0, T)
    if len(series_cols) != D:
        raise ValueError(f"series_cols length must equal D. len={len(series_cols)} D={D}")
    if len(timestamps) != T:
        raise ValueError(f"timestamps length must equal T. len={len(timestamps)} T={T}")
    if target_col not in series_cols:
        raise ValueError(f"target_col='{target_col}' not found in series_cols={series_cols}")

    series_map = {name: np.asarray(arr[:, i], float) for i, name in enumerate(series_cols)}
    x_target = np.asarray(series_map[target_col], float)
    if label is not None and not isinstance(label, dict):
        label = {"class": label}

    meta = {
        "dataset": dataset_name,
        "task": task,
        "series_key": series_key,
        "indices": [int(indices[0]), int(indices[1])],
        "length": int(T),
        "t_start": timestamps[0],
        "t_end": timestamps[-1],
    }

    summary = analyze_window(meta, series_map, target_col=target_col, series_cols=series_cols)
    features = build_features(summary, x_target, target_col=target_col)

    vol_lab = features["volatility"]
    claims = build_claims(summary, target_col, x_target, timestamps, vol_lab)

    check = validate_claims(claims, series_map, target_col=target_col)
    claims_checked: List[Claim] = check["checked"]

    claims_checked = apply_consistency_rules(claims_checked)
    claims_checked = apply_claim_policy(claims_checked, enforce=enforce_claims)

    trend_claim = next((c for c in claims_checked if c.type == "global_trend_label"), None)
    if trend_claim is not None:
        features["trend"] = (trend_claim.data or {}).get("label_final") or (trend_claim.data or {}).get("label") or features["trend"]

    if not (isinstance(variables_meta, list) and all(isinstance(v, dict) for v in variables_meta)):
        variables_meta = [
            {"name": c, "index": i, "role": ("target" if c == target_col else "feature")}
            for i, c in enumerate(series_cols)
        ]
    if seed is None:
        seed = (hash((dataset_name, series_key, indices[0], indices[1], target_col)) & 0xFFFFFFFF)

    base_caption = render_caption_zh(
        claims=claims_checked,
        variables=variables_meta,
        target_col=target_col,
        seed=int(seed),
    )

    enhanced_caption = None
    if llm_hook is not None and llm_enabled:
        payload = {
            "base_caption": base_caption,
            "dataset": dataset_name,
            "task": task,
            "series_key": series_key,
            "indices": [int(indices[0]), int(indices[1])],
            "variables": variables_meta,
            "label": label,
            "domain_context": domain_context or {},
            "features": features,
            "claims": [c.to_dict() for c in claims_checked],
        }
        try:
            enhanced_caption = _light_validate_caption(llm_hook(payload))
        except Exception:
            enhanced_caption = None

    final_caption = enhanced_caption or base_caption

    record = {
        "dataset": dataset_name,
        "task": task,
        "series_key": series_key,
        "window_length": int(T),
        "indices": [int(indices[0]), int(indices[1])],
        "time": list(timestamps),
        "timeseries": arr.tolist(),
        "variables": variables_meta,
        "label": label if label is not None else {"anomaly": False, "class": None},
        "features": features,
        "descriptions": [final_caption],
        "caption_base": base_caption,
        "caption_enhanced": enhanced_caption,
        "claims": [c.to_dict() for c in claims_checked],
        "claim_check": {
            "pass": bool(check["pass"]),
            "n": int(check["n"]),
            "n_failed": int(check["n_failed"]),
            "failed": check["failed"],
        },
        "domain_context": domain_context or {},
    }
    return record


def write_jsonl(records: List[Dict[str, Any]], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")