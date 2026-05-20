from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Iterator, Sequence

import torch
from torch.utils.data import Sampler


def _row_value_dim(row: dict[str, Any]) -> str:
    values = row.get("values", [])
    if not values:
        return "0"
    first = values[0]
    return str(len(first) if isinstance(first, list) else 1)


def row_group_key(row: dict[str, Any], key: str = "merge_source_name") -> str:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    if key == "value_dim":
        return _row_value_dim(row)
    if key == "merge_source_name":
        return str(row.get("merge_source_name") or meta.get("merge_source_name") or "unknown")
    if key == "multisim_source_domain":
        return str(row.get("multisim_source_domain") or meta.get("multisim_source_domain") or row.get("domain") or "unknown")
    if key == "domain":
        return str(row.get("domain") or meta.get("domain") or "unknown")
    return str(row.get(key) or meta.get(key) or "unknown")


class SourceGroupedBatchSampler(Sampler[list[int]]):
    """Yield mini-batches whose rows share a source/domain/dimension key."""

    def __init__(
        self,
        rows: Sequence[dict[str, Any]],
        batch_size: int,
        *,
        group_key: str = "merge_source_name",
        shuffle: bool = True,
        seed: int = 42,
        drop_last: bool = False,
    ) -> None:
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")
        self.rows = rows
        self.batch_size = int(batch_size)
        self.group_key = group_key
        self.shuffle = bool(shuffle)
        self.seed = int(seed)
        self.drop_last = bool(drop_last)
        groups: dict[str, list[int]] = defaultdict(list)
        for idx, row in enumerate(rows):
            groups[row_group_key(row, group_key)].append(idx)
        self.groups = dict(groups)

    def __iter__(self) -> Iterator[list[int]]:
        rng = random.Random(self.seed)
        batches: list[list[int]] = []
        for _, indices in sorted(self.groups.items()):
            local = list(indices)
            if self.shuffle:
                rng.shuffle(local)
            for start in range(0, len(local), self.batch_size):
                batch = local[start : start + self.batch_size]
                if len(batch) == self.batch_size or (batch and not self.drop_last):
                    batches.append(batch)
        if self.shuffle:
            rng.shuffle(batches)
        yield from batches

    def __len__(self) -> int:
        total = 0
        for indices in self.groups.values():
            if self.drop_last:
                total += len(indices) // self.batch_size
            else:
                total += math.ceil(len(indices) / self.batch_size)
        return total


def inspect_grouped_batches(
    rows: Sequence[dict[str, Any]],
    *,
    batch_size: int,
    group_key: str = "merge_source_name",
    max_batches: int = 20,
) -> dict[str, Any]:
    sampler = SourceGroupedBatchSampler(rows, batch_size=batch_size, group_key=group_key, shuffle=False)
    previews = []
    violations = 0
    for batch in sampler:
        keys = [row_group_key(rows[idx], group_key) for idx in batch]
        if len(set(keys)) != 1:
            violations += 1
        if len(previews) < max_batches:
            previews.append({"size": len(batch), "keys": keys, "ids": [rows[idx].get("id", "") for idx in batch[:3]]})
    return {
        "batch_size": batch_size,
        "group_key": group_key,
        "num_groups": len(sampler.groups),
        "group_sizes": {key: len(value) for key, value in sorted(sampler.groups.items())},
        "num_batches": len(sampler),
        "mixed_group_batch_violations": violations,
        "preview_batches": previews,
    }
