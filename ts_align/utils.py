#ts_align/utils.py
from __future__ import annotations

import os
import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import numpy as np
import torch


def set_global_seed(seed: int) -> None:
    """Set python / numpy / torch seeds for reproducibility."""
    seed = int(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def worker_init_fn(worker_id: int) -> None:
    """Init each dataloader worker with a different (but deterministic) seed."""
    # torch initial seed is set by DataLoader generator; derive python/numpy from it.
    seed = torch.initial_seed() % (2**32)
    random.seed(seed + worker_id)
    np.random.seed(seed + worker_id)


def save_checkpoint(
    path: str,
    *,
    model: torch.nn.Module,
    args: Dict[str, Any],
    optimizer: Optional[torch.optim.Optimizer] = None,
    scheduler: Optional[Any] = None,
    scaler: Optional[Any] = None,
    step: Optional[int] = None,
    metrics: Optional[Dict[str, float]] = None,
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ckpt: Dict[str, Any] = {
        "model_state_dict": model.state_dict(),
        "args": args,
    }
    if optimizer is not None:
        ckpt["optimizer_state_dict"] = optimizer.state_dict()
    if scheduler is not None and hasattr(scheduler, "state_dict"):
        ckpt["scheduler_state_dict"] = scheduler.state_dict()
    if scaler is not None and hasattr(scaler, "state_dict"):
        ckpt["scaler_state_dict"] = scaler.state_dict()
    if step is not None:
        ckpt["step"] = int(step)
    if metrics is not None:
        ckpt["metrics"] = dict(metrics)
    torch.save(ckpt, path)


def load_checkpoint(path: str, map_location: str | torch.device = "cpu") -> Dict[str, Any]:
    ckpt = torch.load(path, map_location=map_location)
    if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
        return ckpt
    # Backward compatibility: old training code saved {"model": ...}
    if isinstance(ckpt, dict) and "model" in ckpt:
        ckpt = {"model_state_dict": ckpt["model"], "args": ckpt.get("args", {})}
        return ckpt
    # Or raw state_dict
    if isinstance(ckpt, dict):
        return {"model_state_dict": ckpt, "args": {}}
    raise ValueError(f"Unsupported checkpoint format: {type(ckpt)}")
