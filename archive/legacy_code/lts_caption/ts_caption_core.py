# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

# ---- import your existing pipeline modules ----
from ts_caption.pipeline.analyze import analyze_window, build_features
from ts_caption.claims.builder import build_claims
from ts_caption.claims.validator import validate_claims
from ts_caption.claims.policy import apply_claim_policy
from ts_caption.claims.consistency import apply_consistency_rules
from ts_caption.claims.renderer_zh import render_caption_zh, stable_seed

# WindowMeta: try import; otherwise provide a minimal fallback
try:
    from ts_caption.pipeline.windowing import WindowMeta  # type: ignore
except Exception:
    @dataclass
    class WindowMeta:  # fallback
        series_id: int
        global_start_idx: int
        global_end_idx: int
        start_time: str
        end_time: str
        length: int


# -----------------------------
# Core input schema
# -----------------------------

@dataclass
class SampleInput:
    dataset: str
    dataset_name: str
    task: str = "forecasting"

    series_key: str = "series_0"

    # core requirement: timestamp is always List[str]
    time: Optional[List[str]] = None

    # values: (T, D)
    values: Optional[np.ndarray] = None
    series_cols: Optional[List[str]] = None
    target_col: Optional[str] = None

    # optional, provided by wrapper when needed (anomaly/classification)
    label: Optional[Dict[str, Any]] = None

    # domain background & column meaning provided by wrapper
    domain_context_zh: Optional[str] = None
    col_meaning_zh: Optional[Dict[str, str]] = None


def _default_time_strings(T: int) -> List[str]:
    return [f"t{i}" for i in range(T)]


def _build_variables_meta(series_cols: List[str], target_col: str, col_meaning_zh: Dict[str, str]) -> List[dict]:
    out = []
    for i, c in enumerate(series_cols):
        meaning = (col_meaning_zh or {}).get(c, c)
        out.append(
            {
                "name": c,
                "index": i,
                "role": "target" if c == target_col else "feature",
                "meaning_zh": meaning,
                "unit": None,
            }
        )
    return out


def _build_intro_zh(sample: SampleInput, variables_meta: List[dict]) -> str:
    ctx = sample.domain_context_zh or ""
    items = []
    for v in variables_meta:
        name = v.get("name", "")
        meaning = v.get("meaning_zh", "")
        if meaning and meaning != name:
            items.append(f"{name}（{meaning}）")
        else:
            items.append(f"{name}")
    vars_str = "、".join(items)

    if len(variables_meta) == 1:
        return f"{ctx} 本样本为单变量时间序列：{vars_str}。"
    return f"{ctx} 本样本包含 {len(variables_meta)} 个变量：{vars_str}。"


# -----------------------------
# LLM hook + lightweight guard
# -----------------------------

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _lite_guard_llm_caption(
    base_caption: str,
    enhanced_caption: str,
    series_cols: List[str],
    domain_context: str,
) -> bool:
    # 1) 不引入新数字（非常保守，防幻觉）
    base_nums = set(_NUM_RE.findall(base_caption))
    ctx_nums = set(_NUM_RE.findall(domain_context or ""))
    enh_nums = set(_NUM_RE.findall(enhanced_caption))
    allowed_nums = base_nums | ctx_nums
    if not enh_nums.issubset(allowed_nums):
        return False

    # 2) 不引入看起来像列名的未知 token
    token_re = re.compile(r"\b[A-Za-z][A-Za-z0-9_\.]*\b")
    tokens = set(token_re.findall(enhanced_caption))
    suspicious = set()
    for t in tokens:
        if t.startswith("MT_") or "_" in t or (t.isupper() and len(t) <= 12):
            suspicious.add(t)
    if not suspicious.issubset(set(series_cols)):
        return False

    return True


LLMFn = Callable[[str, str, Dict[str, Any]], str]


# -----------------------------
# Core: single sample -> record
# -----------------------------

def core_build_record(
    sample: SampleInput,
    enforce_claims: bool = True,
    use_llm: bool = False,
    llm_fn: Optional[LLMFn] = None,
) -> Dict[str, Any]:
    if sample.values is None or sample.series_cols is None:
        raise ValueError("SampleInput.values and SampleInput.series_cols are required.")

    X = np.asarray(sample.values, dtype=float)
    if X.ndim != 2:
        raise ValueError(f"values must be 2D array (T,D), got shape {X.shape}")

    T, D = X.shape
    series_cols = list(sample.series_cols)
    if len(series_cols) != D:
        raise ValueError(f"series_cols length {len(series_cols)} != D {D}")

    target_col = sample.target_col or (series_cols[0] if series_cols else "target")
    if target_col not in series_cols:
        raise ValueError(f"target_col={target_col} not in series_cols={series_cols}")

    time_list = sample.time if sample.time else _default_time_strings(T)
    if len(time_list) != T:
        raise ValueError(f"time length {len(time_list)} != T {T}")

    # Build df for your existing pipeline
    time_col = "timestamp"
    win_df = pd.DataFrame(X, columns=series_cols)
    win_df.insert(0, time_col, pd.Series(time_list, dtype=str))

    meta = WindowMeta(
        series_id=0,
        global_start_idx=0,
        global_end_idx=T - 1,
        start_time=str(time_list[0]),
        end_time=str(time_list[-1]),
        length=T,
    )

    summary = analyze_window(meta, win_df, time_col=time_col, target_col=target_col, series_cols=series_cols)
    x_target = win_df[target_col].to_numpy(float)

    features = build_features(summary, x_target, target_col=target_col)
    vol_lab = features.get("volatility", "low")

    claims = build_claims(summary, target_col, x_target, time_list, volatility_label=vol_lab)
    check = validate_claims(claims, win_df[[time_col] + series_cols].copy(), time_col=time_col)

    claims = apply_consistency_rules(claims)
    claims = apply_claim_policy(claims, enforce=enforce_claims)

    trend_claim = next((c for c in claims if c.type == "global_trend_label"), None)
    if trend_claim is not None:
        features["trend"] = (trend_claim.data or {}).get("label_final") or (trend_claim.data or {}).get("label") or features.get("trend")

    col_meaning = sample.col_meaning_zh or {}
    variables_meta = _build_variables_meta(series_cols, target_col, col_meaning)
    intro = _build_intro_zh(sample, variables_meta)

    seed = stable_seed(sample.dataset_name, sample.series_key, 0, T - 1, target_col)
    caption_body = render_caption_zh(
        claims=claims,
        variables=variables_meta,
        target_col=target_col,
        seed=seed,
        include_vars_intro=False,
    )
    base_caption = (intro + " " + caption_body).strip()
    final_caption = base_caption

    if use_llm and llm_fn is not None:
        domain_ctx = sample.domain_context_zh or ""
        draft_record = {
            "dataset": sample.dataset_name,
            "series_key": sample.series_key,
            "time": time_list,
            "series_cols": series_cols,
            "target_col": target_col,
            "features": features,
            "claims": [c.to_dict() for c in claims],
            "claim_check": check,
            "label": sample.label,
        }
        try:
            enhanced = (llm_fn(base_caption, domain_ctx, draft_record) or "").strip()
            if enhanced and _lite_guard_llm_caption(base_caption, enhanced, series_cols, domain_ctx):
                final_caption = enhanced
        except Exception:
            final_caption = base_caption

    record = {
        "dataset": sample.dataset_name,
        "task": sample.task,
        "series_key": sample.series_key,
        "window_length": T,
        "indices": [0, T - 1],
        "time": time_list,
        "timeseries": X.tolist(),
        "variables": variables_meta,
        "label": sample.label if sample.label is not None else {"anomaly": False, "class": None},
        "features": features,
        "descriptions": [final_caption],        # exactly 1 enhanced caption
        "descriptions_base": [base_caption],    # keep base for debugging
        "claims": [c.to_dict() for c in claims],
        "claim_check": check,
        "domain_context_zh": sample.domain_context_zh,
    }
    return record
