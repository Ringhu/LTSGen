# ts_align/data/jsonl_dataset.py
from __future__ import annotations
import json
import random
from typing import Any, Dict, List, Optional, Sequence
import torch
from torch.utils.data import Dataset
from .text_augment import normalize_space, strip_numbers

def _as_tensor_timeseries(obj: Any) -> torch.Tensor:
    """
    Convert obj["timeseries"] (typically list of length T, each element list of D)
    into torch FloatTensor of shape [C, T] where C=D.
    """
    ts = obj
    if ts is None:
        raise KeyError("jsonl record missing 'timeseries'")
    x = torch.tensor(ts, dtype=torch.float32)  # [T,D] or [T] or [T,1]
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2:
        raise ValueError(f"Unexpected timeseries shape: {tuple(x.shape)}")
    x = x.transpose(0, 1).contiguous()  # [D,T]
    return x


def _get_nested(d: Dict[str, Any], keys: Sequence[str], default: Any = "") -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _pick_caption_by_mode(obj: Dict[str, Any], mode: str) -> str:
    """
    Select a single global caption string from the record given mode.
    Supported modes:
      - global_en / global_zh
      - domain_en / domain_zh
      - desc0 (obj["descriptions"][0]) / desc1
      - caption_base
    """
    mode = str(mode)
    if mode in ("global_en", "global_zh"):
        lang = mode.split("_", 1)[1]
        return str(_get_nested(obj, ["dense_captions", "global", lang], default="")).strip()
    if mode in ("domain_en", "domain_zh"):
        lang = mode.split("_", 1)[1]
        return str(_get_nested(obj, ["dense_captions", "domain_integrated", lang], default="")).strip()
    if mode.startswith("desc"):
        idx = int(mode.replace("desc", ""))
        descs = obj.get("descriptions") or []
        if isinstance(descs, list) and len(descs) > idx:
            return str(descs[idx]).strip()
        return ""
    if mode == "caption_base":
        return str(obj.get("caption_base", "")).strip()
    # fallback: try global_en then global_zh then descriptions[0]
    t = str(_get_nested(obj, ["dense_captions", "global", "en"], default="")).strip()
    if t:
        return t
    t = str(_get_nested(obj, ["dense_captions", "global", "zh"], default="")).strip()
    if t:
        return t
    descs = obj.get("descriptions") or []
    if isinstance(descs, list) and descs:
        return str(descs[0]).strip()
    return ""


def _pick_captions_by_modes(obj: Dict[str, Any], modes: Sequence[str]) -> List[str]:
    """
    Return multiple captions (deduped, non-empty) for one record.
    """
    outs: List[str] = []
    seen = set()
    for m in modes:
        t = _pick_caption_by_mode(obj, str(m))
        t = normalize_space(t)
        if not t:
            continue
        if t in seen:
            continue
        outs.append(t)
        seen.add(t)
    return outs

def _extract_local_events_dense(obj: Dict[str, Any], mode: str, *, non_numeric: bool = False) -> List[Dict[str, Any]]:
    """
    Extract local events from dense_captions.local.
    Returns list of dicts:
      {start:int, end:int (inclusive), type:str, text:str}
    """
    mode = str(mode)
    if mode not in ("local_en", "local_zh"):
        return []
    lang = mode.split("_", 1)[1]
    locals_ = _get_nested(obj, ["dense_captions", "local"], default=[])
    out: List[Dict[str, Any]] = []
    if not isinstance(locals_, list):
        return out
    for ev in locals_:
        if not isinstance(ev, dict):
            continue
        s = ev.get("start", None)
        e = ev.get("end", None)
        if s is None or e is None:
            continue
        t = ev.get(f"description_{lang}", "") or ev.get(f"description_{'en' if lang=='zh' else 'zh'}", "")
        t = normalize_space(t)
        if not t:
            continue
        if non_numeric:
            t = strip_numbers(t)
        out.append({
            "start": int(s),
            "end": int(e),  # inclusive
            "type": str(ev.get("type", "")),
            "text": t,
        })
    return out


class TSCapJSONLDataset(Dataset):
    def __init__(
        self,
        jsonl_path: str,
        *,
        max_records: Optional[int] = None,
        seed: int = 0,
        global_caption: str | List[str] = "global_en",   # <-- allow list
        local_caption: str = "local_en",
        non_numeric_local: bool = False,
        local_types: Optional[List[str]] = None,
    ) -> None:
        self.jsonl_path = str(jsonl_path)
        self.rng = random.Random(int(seed))

        # normalize to list
        if isinstance(global_caption, (list, tuple)):
            self.global_captions = [str(x) for x in global_caption]
        else:
            self.global_captions = [str(global_caption)]

        self.local_caption = str(local_caption)
        self.non_numeric_local = bool(non_numeric_local)
        self.local_types = [str(x) for x in (local_types or [])]
        self.offsets: List[int] = []


        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            pos = f.tell()
            line = f.readline()
            n = 0
            while line:
                self.offsets.append(pos)
                n += 1
                if max_records is not None and n >= int(max_records):
                    break
                pos = f.tell()
                line = f.readline()
        if not self.offsets:
            raise ValueError(f"No records found: {self.jsonl_path}")

    def __len__(self) -> int:
        return len(self.offsets)


    def __getitem__(self, idx: int) -> Dict[str, Any]:
        off = self.offsets[int(idx)]
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            f.seek(off)
            obj = json.loads(f.readline())

        x = _as_tensor_timeseries(obj.get("timeseries"))
        length = int(x.shape[1])

        global_texts = _pick_captions_by_modes(obj, self.global_captions)

        # fallback
        if not global_texts:
            global_texts = ["This is a time series segment."]

        global_text = global_texts[0]

        locals_ = _extract_local_events_dense(obj, self.local_caption, non_numeric=self.non_numeric_local)
        if self.local_types:
            keep = set(self.local_types)
            locals_ = [ev for ev in locals_ if str(ev.get("type","")) in keep]

        meta = {
            "dataset": obj.get("dataset", None),
            "task": obj.get("task", None),
            "series_key": obj.get("series_key", None),
            "label": obj.get("label", None),
        }
        return {
            "x": x,
            "length": length,
            "global_text": global_text,     # backward-compatible
            "global_texts": global_texts,   # NEW: multi-positive
            "locals": locals_,
            "meta": meta,
        }