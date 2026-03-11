# ts_caption/claims/budget.py
from __future__ import annotations
from typing import List
from .schema import Claim

def apply_budget_policy(
    claims: List[Claim],
    max_peaks: int = 1,
    max_valleys: int = 1,
    max_corrs: int = 1,
) -> List[Claim]:
    # peaks/valleys：按 |z| 排序保留最极端
    peaks = [c for c in claims if c.type == "peak"]
    valleys = [c for c in claims if c.type == "valley"]
    others = [c for c in claims if c.type not in ("peak", "valley", "lagged_corr")]

    peaks = sorted(peaks, key=lambda c: -abs(float((c.data or {}).get("z", 0.0))))[:max_peaks]
    valleys = sorted(valleys, key=lambda c: -abs(float((c.data or {}).get("z", 0.0))))[:max_valleys]

    # correlations：优先 stable=True；若都不 stable，只保留 |ρ| 最大 1 条
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
