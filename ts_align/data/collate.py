# ts_align/data/collate.py
from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Tuple, Sequence, Optional

import torch

from .text_augment import strip_numbers, normalize_space


def _ceil_div(a: int, b: int) -> int:
    return (int(a) + int(b) - 1) // int(b)


def map_span_to_patch(start: int, end_inclusive: int, patch_size: int) -> Tuple[int, int]:
    s = int(start)
    e_excl = int(end_inclusive) + 1
    ps = s // int(patch_size)
    pe = _ceil_div(e_excl, int(patch_size))
    if pe <= ps:
        pe = ps + 1
    return ps, pe


def _label_to_str(label: Any) -> str:
    if label is None:
        return "none"
    if isinstance(label, dict):
        if "class" in label:
            return str(label["class"])
        try:
            return json.dumps(label, sort_keys=True, ensure_ascii=False)
        except Exception:
            return str(label)
    return str(label)


def _make_group_key(meta: Dict[str, Any], *, positive_key: str) -> str:
    """
    positive_key:
      - "instance": series_key (recommended default for multi-caption positives)
      - "label": dataset|task|label (supervised contrastive style)
    """
    positive_key = str(positive_key)
    dataset = str(meta.get("dataset", ""))
    task = str(meta.get("task", ""))
    series_key = str(meta.get("series_key", ""))
    label = _label_to_str(meta.get("label", None))

    if positive_key == "label":
        return f"{dataset}|{task}|label:{label}"
    # default instance
    return f"{dataset}|{task}|series:{series_key}"


def _apply_random_crop(
    x: torch.Tensor,                         # [C,T]
    locals_: List[Dict[str, Any]],
    *,
    crop_len: int,
    rng: random.Random,
) -> Tuple[torch.Tensor, List[Dict[str, Any]], int]:
    """
    Crop to length crop_len. Return (x_crop, locals_crop, start).
    locals_ use inclusive end in time indices.
    """
    C, T = x.shape
    crop_len = int(crop_len)
    if crop_len <= 0 or crop_len >= T:
        return x, locals_, 0

    start = rng.randint(0, T - crop_len)
    end = start + crop_len  # exclusive
    x2 = x[:, start:end].contiguous()

    locals2: List[Dict[str, Any]] = []
    for ev in locals_:
        s = int(ev["start"])
        e = int(ev["end"])  # inclusive

        # intersection with [start, end-1]
        is0 = max(s, start)
        ie0 = min(e, end - 1)
        if is0 > ie0:
            continue

        ev2 = dict(ev)
        ev2["start"] = int(is0 - start)
        ev2["end"] = int(ie0 - start)
        locals2.append(ev2)

    return x2, locals2, start


def hsa_collate_fn(
    batch: List[Dict[str, Any]],
    *,
    patch_size: int,
    max_local_per_sample: int = 4,

    # --- NEW: multi-positive captions ---
    max_global_texts_per_sample: int = 4,
    positive_key: str = "instance",          # "instance" or "label"

    # --- NEW: multi-scale random crop (augmentation) ---
    random_crop: bool = False,
    crop_prob: float = 1.0,
    crop_lengths: Optional[Sequence[int]] = None,   # e.g. [96,128,192,256,384,512]
    strip_numbers_on_crop: bool = False,

    seed: int = 0,
) -> Dict[str, Any]:
    """
    Returns (major fields):
      x: [B,C,Tmax]
      lengths: [B]

      global_texts: List[str] length M (flattened captions)
      global_batch_idx: LongTensor [M]  (caption -> which ts sample)
      group_ids_ts: LongTensor [B]
      group_ids_txt: LongTensor [M]

      local_texts, local_batch_idx, local_ps, local_pe ... (same as before)
    """
    if not batch:
        return {}

    rng = random.Random(int(seed))

    B = len(batch)
    C = int(batch[0]["x"].shape[0])

    # Preprocess each sample: maybe crop, maybe subsample locals, maybe cap global_texts
    xs: List[torch.Tensor] = []
    lens: List[int] = []
    metas: List[Dict[str, Any]] = []
    globals_per_sample: List[List[str]] = []
    locals_per_sample: List[List[Dict[str, Any]]] = []

    for b in batch:
        x: torch.Tensor = b["x"]  # [C,T]
        meta = b.get("meta", {}) or {}
        locals_ = list(b.get("locals") or [])

        # cap locals (memory control)
        if len(locals_) > int(max_local_per_sample):
            locals_ = rng.sample(locals_, int(max_local_per_sample))

        # get multiple global texts if present
        gtexts = b.get("global_texts", None)
        if not isinstance(gtexts, list) or not gtexts:
            gtexts = [str(b.get("global_text", ""))]

        # normalize & drop empties
        gtexts2: List[str] = []
        for t in gtexts:
            t = normalize_space(str(t))
            if t:
                gtexts2.append(t)
        if not gtexts2:
            gtexts2 = ["This is a time series segment."]

        # cap global texts per sample
        if len(gtexts2) > int(max_global_texts_per_sample):
            gtexts2 = rng.sample(gtexts2, int(max_global_texts_per_sample))

        # optional multi-scale crop
        T = int(x.shape[1])
        if bool(random_crop) and (rng.random() < float(crop_prob)) and crop_lengths:
            cand = [int(L) for L in crop_lengths if int(L) <= T]
            if cand:
                crop_len = rng.choice(cand)
                x, locals_, _ = _apply_random_crop(x, locals_, crop_len=crop_len, rng=rng)
                if strip_numbers_on_crop:
                    gtexts2 = [strip_numbers(t) for t in gtexts2]

        xs.append(x)
        lens.append(int(x.shape[1]))
        metas.append(meta)
        globals_per_sample.append(gtexts2)
        locals_per_sample.append(locals_)

    lengths = torch.tensor(lens, dtype=torch.long)
    T_max = int(lengths.max().item())
    x_pad = torch.zeros((B, C, T_max), dtype=torch.float32)

    for i in range(B):
        x = xs[i]
        T = int(x.shape[1])
        x_pad[i, :, :T] = x[:, :T]

    # Flatten global texts => M captions
    global_texts: List[str] = []
    global_batch_idx: List[int] = []
    for i in range(B):
        for t in globals_per_sample[i]:
            global_texts.append(t)
            global_batch_idx.append(i)

    global_batch_idx_t = (
        torch.tensor(global_batch_idx, dtype=torch.long)
        if global_batch_idx else torch.zeros((0,), dtype=torch.long)
    )

    # Build group ids for multi-positive
    group_keys_ts = [_make_group_key(metas[i], positive_key=positive_key) for i in range(B)]
    key2id: Dict[str, int] = {}
    group_ids_ts_list: List[int] = []
    for k in group_keys_ts:
        if k not in key2id:
            key2id[k] = len(key2id)
        group_ids_ts_list.append(key2id[k])

    group_ids_ts = torch.tensor(group_ids_ts_list, dtype=torch.long)
    if global_batch_idx:
        group_ids_txt = group_ids_ts[global_batch_idx_t].clone()
    else:
        group_ids_txt = torch.zeros((0,), dtype=torch.long)

    # Flatten local events (same logic as your original)
    local_texts: List[str] = []
    local_batch_idx: List[int] = []
    local_ps: List[int] = []
    local_pe: List[int] = []
    local_types: List[str] = []

    for bi in range(B):
        locals_ = locals_per_sample[bi]
        if not locals_:
            continue

        n_patches = _ceil_div(int(lengths[bi].item()), int(patch_size))
        n_patches = max(1, n_patches)

        for ev in locals_:
            s = int(ev["start"])
            e = int(ev["end"])  # inclusive
            ps, pe = map_span_to_patch(s, e, patch_size=int(patch_size))
            ps = max(0, min(ps, n_patches - 1))
            pe = max(ps + 1, min(pe, n_patches))
            txt = str(ev.get("text", "")).strip()
            if not txt:
                continue
            local_texts.append(txt)
            local_batch_idx.append(bi)
            local_ps.append(ps)
            local_pe.append(pe)
            local_types.append(str(ev.get("type", "")))

    out = {
        "x": x_pad,
        "lengths": lengths,

        # NEW: multi-caption + multi-positive mapping
        "global_texts": global_texts,                       # List[str], len M
        "global_batch_idx": global_batch_idx_t,             # [M]
        "group_ids_ts": group_ids_ts,                       # [B]
        "group_ids_txt": group_ids_txt,                     # [M]
        "group_keys_ts": group_keys_ts,                     # debug

        # locals (same as before)
        "local_texts": local_texts,
        "local_batch_idx": torch.tensor(local_batch_idx, dtype=torch.long) if local_batch_idx else torch.zeros((0,), dtype=torch.long),
        "local_ps": torch.tensor(local_ps, dtype=torch.long) if local_ps else torch.zeros((0,), dtype=torch.long),
        "local_pe": torch.tensor(local_pe, dtype=torch.long) if local_pe else torch.zeros((0,), dtype=torch.long),
        "local_types": local_types,

        "meta": metas,
    }
    return out
