# ts_caption/claims/schema.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, List

@dataclass
class Claim:
    id: str
    type: str
    target: str

    # span/index
    start: Optional[int] = None
    end: Optional[int] = None
    idx: Optional[int] = None

    # timestamp anchors (optional but推荐写入)
    t_start: Optional[str] = None
    t_end: Optional[str] = None
    t_idx: Optional[str] = None

    # payload
    data: Dict[str, Any] = None

    # rendering & checking
    sentence: Optional[str] = None
    ok: Optional[bool] = None
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["data"] is None:
            d["data"] = {}
        return d
