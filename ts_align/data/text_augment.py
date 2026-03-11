# ts_align/data/text_augment.py
from __future__ import annotations

import re
from typing import Optional

_NUM_RE = re.compile(r"[-+]?\d+(\.\d+)?%?")
_IDX_RE = re.compile(r"(time\s*\d+)|(index\s*\d+)|(索引\s*\d+)|(时间点\s*\d+)", flags=re.IGNORECASE)

def strip_numbers(text: str) -> str:
    """Remove explicit numbers (including percentages) from a caption."""
    t = str(text)
    t = _IDX_RE.sub("", t)
    t = _NUM_RE.sub("", t)
    # cleanup repeated spaces/punct
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s*([,.;:，。；：])\s*", r"\1 ", t).strip()
    return t

def normalize_space(text: str) -> str:
    return " ".join(str(text).strip().split())
