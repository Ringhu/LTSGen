# ts_align/models/chronos2_encoder.py
from __future__ import annotations

from typing import Any, Tuple
import numpy as np
import torch
import torch.nn as nn

try:
    # pip package is typically "chronos-forecasting", import name "chronos"
    from chronos import Chronos2Pipeline
except Exception:  # pragma: no cover
    Chronos2Pipeline = None


class Chronos2TimeEncoder(nn.Module):
    """
    Thin wrapper around Chronos2Pipeline to extract token embeddings for alignment.

    Notes:
    - Chronos pipeline system supports from_pretrained and NaN padding masks.  :contentReference[oaicite:2]{index=2}
    - Chronos-2 is encoder-only foundation model. :contentReference[oaicite:3]{index=3}

    This wrapper assumes `.embed()` exists in your installed chronos-forecasting version.
    If not, you should upgrade chronos-forecasting.
    """
    def __init__(
        self,
        model_name: str = "autogluon/chronos-2",
        *,
        device_map: str = "cuda",
        torch_dtype: str | torch.dtype = "bfloat16",
        channel_pool: str = "first",   # "first" or "mean"
        fine_tune: bool = False,
    ) -> None:
        super().__init__()
        if Chronos2Pipeline is None:
            raise ImportError(
                "Chronos2Pipeline not found. Please install chronos-forecasting (amazon-science/chronos-forecasting)."
            )

        self.model_name = str(model_name)
        self.channel_pool = str(channel_pool)

        self.pipeline = Chronos2Pipeline.from_pretrained(
            self.model_name,
            device_map=device_map,
            torch_dtype=torch_dtype,
        )

        # freeze backbone by default
        if not fine_tune:
            for p in self.pipeline.inner_model.parameters():
                p.requires_grad = False

        # infer hidden size
        cfg = getattr(self.pipeline.inner_model, "config", None)
        hs = getattr(cfg, "hidden_size", None)
        if hs is None:
            hs = getattr(cfg, "d_model", None)
        if hs is None:
            raise ValueError("Cannot infer Chronos-2 hidden size from model config.")
        self.out_dim = int(hs)

        # check embed
        if not hasattr(self.pipeline, "embed"):
            raise AttributeError(
                "Your Chronos2Pipeline has no `.embed()` method. Please upgrade chronos-forecasting."
            )

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        x: (B,C,T) preferred, but also accept:
        - (B,T)   -> treated as single-channel
        - (B,T,C) -> transposed to (B,C,T) if heuristic matches

        Returns:
        H: [B,N,D] token embeddings
        mask: [B,N] True=valid token
        """
        # -------- 1) normalize input shape --------
        if x.dim() == 2:
            # (B,T) -> (B,1,T)
            x = x.unsqueeze(1)
        elif x.dim() == 3:
            # maybe (B,T,C) -> (B,C,T)
            if x.shape[2] <= 32 and x.shape[1] > x.shape[2]:
                x = x.transpose(1, 2).contiguous()
        else:
            raise ValueError(f"Chronos2TimeEncoder expects x dim=2 or 3, got shape={tuple(x.shape)}")

        B, C, T = x.shape

        # lengths
        if lengths is None:
            lengths = torch.full((B,), T, dtype=torch.long, device=x.device)
        else:
            lengths = lengths.to(dtype=torch.long, device=x.device).clamp(min=1, max=T)

        device = x.device

        # -------- 2) build context for Chronos2 (CPU!) --------
        # Chronos2 expects (n_series, n_variates, history_length) if tensor input
        # IMPORTANT: pass CPU tensor to avoid pin_memory trying to pin CUDA tensors
        context = x.detach().to("cpu")

        # -------- 3) call embed --------
        emb = self.pipeline.embed(context)

        # -------- 4) normalize embed output to padded Tensor --------
        # emb can be:
        #  - torch.Tensor [B,N,D] or [B,D]
        #  - np.ndarray
        #  - list[Tensor] or list[np.ndarray]
        #  - list[dict] where embedding is in some key
        if isinstance(emb, np.ndarray):
            emb = torch.from_numpy(emb)

        if isinstance(emb, torch.Tensor):
            # [B,D] -> [B,1,D]
            if emb.ndim == 2:
                H = emb[:, None, :]
                mask = torch.ones((B, 1), dtype=torch.bool)
            elif emb.ndim == 3:
                H = emb
                mask = torch.ones((B, H.shape[1]), dtype=torch.bool)
            else:
                raise ValueError(f"Unexpected embed tensor ndim={emb.ndim}")
            return H.to(device), mask.to(device)

        if isinstance(emb, (list, tuple)):
            # if tuple like (list_or_tensor, extra)
            if isinstance(emb, tuple) and len(emb) > 0:
                emb = emb[0]

            if not isinstance(emb, list):
                # could still be tensor/ndarray handled above; anything else is error
                raise TypeError(f"Unexpected embed output container type: {type(emb)}")

            if len(emb) == 0:
                raise RuntimeError("Chronos2Pipeline.embed returned an empty list.")

            # list[dict] -> extract embedding field
            if isinstance(emb[0], dict):
                # try common keys
                cand_keys = ["embedding", "embeddings", "encoder_hidden_states", "hidden_states", "repr", "representation"]
                found_key = None
                for k in cand_keys:
                    if k in emb[0]:
                        found_key = k
                        break
                if found_key is None:
                    raise KeyError(f"embed returned list[dict] but none of keys {cand_keys} found in first item.")
                seqs = [e[found_key] for e in emb]
            else:
                seqs = emb  # list[tensor/ndarray]

            # convert each to CPU tensor [N,D] (or [D] -> [1,D])
            seq_tensors = []
            for s in seqs:
                if isinstance(s, np.ndarray):
                    t = torch.from_numpy(s)
                elif isinstance(s, torch.Tensor):
                    t = s.detach().to("cpu")
                else:
                    raise TypeError(f"Unexpected per-sample embed type in list: {type(s)}")

                if t.ndim == 1:
                    t = t[None, :]
                elif t.ndim == 2:
                    pass
                else:
                    # sometimes might be [1,N,D] etc; squeeze common cases
                    t = t.squeeze(0)
                    if t.ndim == 1:
                        t = t[None, :]
                    if t.ndim != 2:
                        raise ValueError(f"Per-sample embed must be 1D/2D after squeeze, got shape={tuple(t.shape)}")

                seq_tensors.append(t)

            # pad to max length
            max_n = max(t.shape[0] for t in seq_tensors)
            D = seq_tensors[0].shape[-1]
            dtype = seq_tensors[0].dtype

            H = torch.zeros((B, max_n, D), dtype=dtype)
            mask = torch.zeros((B, max_n), dtype=torch.bool)
            for i, t in enumerate(seq_tensors):
                n = t.shape[0]
                H[i, :n, :] = t
                mask[i, :n] = True

            return H.to(device), mask.to(device)

        raise TypeError(f"Unexpected embed output type: {type(emb)}")

    # def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    #     """
    #     x: expected (B, C, T). But we also accept:
    #        - (B, T)  -> treat as single-channel
    #        - (B, T, C) -> transpose to (B, C, T)

    #     Returns:
    #       H: [B,N,D] token embeddings
    #       mask: [B,N] True=valid
    #     """
    #     B, C, T = x.shape
    #     if x.dim() == 2:
    #         # (B, T) -> (B, 1, T)
    #         x = x.unsqueeze(1)
    #     elif x.dim() == 3:
    #         # might be (B, T, C) from some pipelines
    #         # heuristic: if last dim is small (#channels) and middle dim is long (T), transpose
    #         if x.shape[2] <= 32 and x.shape[1] > x.shape[2]:
    #             # (B, T, C) -> (B, C, T)
    #             x = x.transpose(1, 2).contiguous()
    #     else:
    #         raise ValueError(f"Chronos2TimeEncoder expects x dim=2 or 3, got shape={tuple(x.shape)}")

    #     # lengths are for time dimension (last dim)
    #     T = x.shape[-1]
    #     if lengths is None:
    #         lengths = torch.full((x.shape[0],), T, dtype=torch.long, device=x.device)
    #     else:
    #         lengths = lengths.to(dtype=torch.long, device=x.device).clamp(min=1, max=T)
            
    #     context = x  # or your cropped/padded version based on lengths
    #     context = context.detach().to("cpu")
    #     # B, C, T = x.shape
    #     device = x.device

    #     # # reduce to univariate if needed
    #     # if self.channel_pool == "mean":
    #     #     v = x.mean(dim=1)  # [B,T]
    #     # else:
    #     #     v = x[:, 0, :]     # [B,T]

    #     # # Chronos pipelines commonly use NaN padding + ~isnan mask. :contentReference[oaicite:4]{index=4}
    #     # # We'll left-pad with NaN so that the most recent values align to the right.
    #     # context = torch.full((B, T), float("nan"), dtype=torch.float32, device=device)
    #     # for i in range(B):
    #     #     L = int(lengths[i].item())
    #     #     L = max(1, min(L, T))
    #     #     context[i, T - L : T] = v[i, :L].to(torch.float32)

    #     emb = self.pipeline.embed(context)

    #     # normalize types to torch.Tensor on the same device
    #     if isinstance(emb, np.ndarray):
    #         emb = torch.from_numpy(emb)
    #     if isinstance(emb, (list, tuple)):
    #         # some implementations may return list[Tensor] or (emb, extra)
    #         emb0 = emb[0]
    #         if isinstance(emb0, np.ndarray):
    #             emb0 = torch.from_numpy(emb0)
    #         emb = emb0

    #     if not isinstance(emb, torch.Tensor):
    #         raise TypeError(f"Unexpected embed output type: {type(emb)}")

    #     if emb.device != device:
    #         emb = emb.to(device)

    #     if emb.ndim == 2:
    #         # [B,D] -> treat as single token
    #         H = emb[:, None, :]
    #         mask = torch.ones((B, 1), dtype=torch.bool, device=device)
    #         return H, mask

    #     if emb.ndim == 3:
    #         # [B,N,D]
    #         H = emb
    #         mask = torch.ones((B, H.shape[1]), dtype=torch.bool, device=device)
    #         return H, mask

    #     raise ValueError(f"Unexpected embed tensor ndim={emb.ndim}")
