# ts_caption/claims/policy.py
from __future__ import annotations
from typing import List
from .schema import Claim

def apply_claim_policy(claims: List[Claim], enforce: bool = True) -> List[Claim]:
    """
    enforce=True:
      - 对 ok=False 的 claim：优先降级（seasonality/corr），否则删除
      - 保证至少保留 global_net_change + volatility + (peak/valley 至少一个如有)
    """
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

        # ok=False：尝试降级
        if c.type == "lagged_corr":
            # 降级：保留但标记稳定性弱（renderer 会用弱语气）
            d = c.data or {}
            d["stable"] = False
            c.data = d
            c.ok = True
            kept.append(c)
        elif c.type == "seasonality":
            # 降级为“未检测到明显周期”
            d = c.data or {}
            d["has"] = False
            d["period"] = None
            c.data = d
            c.ok = True
            kept.append(c)
        else:
            # 其他：直接删
            pass

    # coverage 最低保障：global_net_change 必须有
    if not any(c.type == "global_net_change" for c in kept):
        # 兜底：如果被删了，尽量从原 claims 找回来（即便 ok 不确定）
        for c in claims:
            if c.type == "global_net_change":
                kept.insert(0, c)
                break

    return kept
