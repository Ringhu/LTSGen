# ts_align/models/hsa_clip.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .layers import RevIN
from .time_encoder import PatchTimeEncoder
from .text_encoder import TextEncoder
from .chronos2_encoder import Chronos2TimeEncoder


def l2norm(x: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    return x / (x.norm(dim=-1, keepdim=True).clamp(min=eps))

def _ceil_div(a: int, b: int) -> int:
    return (int(a) + int(b) - 1) // int(b)


def hierarchical_pool_tokens(
    H: torch.Tensor,          # [B,N,D]
    mask: torch.Tensor,       # [B,N] bool
    *,
    stride: int = 4,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Downsample token sequence by stride with masked average pooling.
    Returns pooled_H [B,N2,D], pooled_mask [B,N2].
    """
    B, N, D = H.shape
    s = int(stride)
    if s <= 1:
        return H, mask

    N_pad = _ceil_div(N, s) * s
    if N_pad != N:
        pad = N_pad - N
        H = F.pad(H, (0, 0, 0, pad), value=0.0)
        mask = F.pad(mask, (0, pad), value=False)

    H = H.view(B, N_pad // s, s, D)
    m = mask.view(B, N_pad // s, s).to(H.dtype)  # [B,N2,s]
    denom = m.sum(dim=2, keepdim=True).clamp(min=1.0)
    pooled = (H * m.unsqueeze(-1)).sum(dim=2) / denom
    pooled_mask = mask.view(B, N_pad // s, s).any(dim=2)
    return pooled, pooled_mask

class HSAClipModel(nn.Module):
    """
    HSA-CLIP with pluggable time backbone:
      - "patch"   : your existing PatchTimeEncoder
      - "chronos2": Chronos-2 as global time encoder
      - "hybrid"  : Chronos-2 for global, PatchTimeEncoder for local/patch

    Also supports hierarchical token pooling (optional).
    """
    def __init__(
        self,
        *,
        in_channels: int,
        patch_size: int = 16,
        d_model: int = 256,
        n_time_layers: int = 6,
        n_time_heads: int = 8,

        # text
        text_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        d_embed: int = 256,
        dropout: float = 0.1,
        fine_tune_text: bool = False,

        # NEW: time backbone
        time_backbone: str = "patch",                 # "patch" | "chronos2" | "hybrid"
        chronos2_model: str = "autogluon/chronos-2",
        chronos2_device_map: str = "cuda",
        chronos2_dtype: str | torch.dtype = "bfloat16",
        fine_tune_chronos2: bool = False,
        chronos2_channel_pool: str = "first",         # "first" | "mean"

        # NEW: hierarchical pooling
        hier_pool: bool = False,
        hier_stride: int = 4,
        hier_pool_for_global: bool = True,
    ) -> None:
        super().__init__()
        self.patch_size = int(patch_size)
        self.time_backbone = str(time_backbone)

        self.hier_pool = bool(hier_pool)
        self.hier_stride = int(hier_stride)
        self.hier_pool_for_global = bool(hier_pool_for_global)

        # patch encoder (for patch/local)
        self.revin = RevIN(int(in_channels))
        if self.time_backbone in ("patch", "hybrid"):
            self.time_encoder_patch = PatchTimeEncoder(
                in_channels=int(in_channels),
                d_model=int(d_model),
                patch_size=int(patch_size),
                n_layers=int(n_time_layers),
                n_heads=int(n_time_heads),
                dropout=float(dropout),
            )
            self.proj_ts_patch = nn.Linear(int(d_model), int(d_embed), bias=False)
        else:
            self.time_encoder_patch = None
            self.proj_ts_patch = None

        # chronos2 encoder (for global)
        if self.time_backbone in ("chronos2", "hybrid"):
            self.time_encoder_chronos2 = Chronos2TimeEncoder(
                model_name=str(chronos2_model),
                device_map=str(chronos2_device_map),
                torch_dtype=chronos2_dtype,
                channel_pool=str(chronos2_channel_pool),
                fine_tune=bool(fine_tune_chronos2),
            )
            self.proj_ts_chronos2 = nn.Linear(int(self.time_encoder_chronos2.out_dim), int(d_embed), bias=False)
        else:
            self.time_encoder_chronos2 = None
            self.proj_ts_chronos2 = None

        # text encoder
        self.text_encoder = TextEncoder(model_name=text_model, fine_tune=bool(fine_tune_text))
        self.proj_txt = nn.Linear(int(self.text_encoder.out_dim), int(d_embed), bias=False)

        # CLIP temperature
        self.logit_scale = nn.Parameter(torch.ones([]) * float(np.log(1 / 0.07)))

    def get_scale(self) -> torch.Tensor:
        return self.logit_scale.exp().clamp(max=100.0)

    def encode_text(self, texts: List[str]) -> torch.Tensor:
        h = self.text_encoder(texts)
        return l2norm(self.proj_txt(h))

    def encode_time(self, x: torch.Tensor, lengths: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Returns dict including:
          z_global: [B,E]
          z_patch:  [B,N,E] (only if patch encoder enabled)
          patch_mask: [B,N] (only if patch encoder enabled)
        """
        out: Dict[str, torch.Tensor] = {}

        # (A) patch tokens (for local / span)
        if self.time_encoder_patch is not None:
            x_norm = self.revin(x, "norm")
            H, patch_mask = self.time_encoder_patch(x_norm, lengths)  # [B,N,D]
            z_patch = l2norm(self.proj_ts_patch(H))                   # [B,N,E]
            out["H"] = H
            out["patch_mask"] = patch_mask
            out["z_patch"] = z_patch

        # (B) global embedding
        if self.time_encoder_chronos2 is not None:
            Hc, mc = self.time_encoder_chronos2(x, lengths)  # Hc: [B,Nc,Dc]
            if self.hier_pool and self.hier_pool_for_global:
                Hc2, mc2 = hierarchical_pool_tokens(Hc, mc, stride=self.hier_stride)
            else:
                Hc2, mc2 = Hc, mc
            m = mc2.unsqueeze(-1).to(Hc2.dtype)
            h_global = (Hc2 * m).sum(dim=1) / m.sum(dim=1).clamp(min=1.0)
            proj_dtype = self.proj_ts_chronos2.weight.dtype
            h_global = h_global.to(dtype=proj_dtype)
            out["z_global"] = l2norm(self.proj_ts_chronos2(h_global))
            # optional: expose chronos tokens for future Q-former
            out["H_chronos2"] = Hc2
            out["mask_chronos2"] = mc2

        else:
            # fallback: global from patch tokens
            if self.time_encoder_patch is None:
                raise RuntimeError("No time encoder available.")
            H = out["H"]
            patch_mask = out["patch_mask"]
            if self.hier_pool and self.hier_pool_for_global:
                Hp, mp = hierarchical_pool_tokens(H, patch_mask, stride=self.hier_stride)
            else:
                Hp, mp = H, patch_mask
            m = mp.unsqueeze(-1).to(Hp.dtype)
            h_global = (Hp * m).sum(dim=1) / m.sum(dim=1).clamp(min=1.0)
            proj_dtype = self.proj_ts_chronos2.weight.dtype
            h_global = h_global.to(dtype=proj_dtype)
            out["z_global"] = l2norm(self.proj_ts_chronos2(h_global))

        return out

    @torch.no_grad()
    def pool_local_spans(
        self,
        z_patch: torch.Tensor,            # [B,N,E] (L2-normalized)
        patch_mask: torch.Tensor,         # [B,N]
        local_batch_idx: torch.Tensor,    # [M]
        local_ps: torch.Tensor,           # [M]
        local_pe: torch.Tensor,           # [M] exclusive
    ) -> torch.Tensor:
        """
        Average-pool patch embeddings in each [ps,pe) span to produce [M,E].
        Useful for local event CLIP loss (z_ts_local vs z_txt_local).
        """
        M = int(local_batch_idx.numel())
        if M == 0:
            return torch.zeros((0, z_patch.size(-1)), device=z_patch.device, dtype=z_patch.dtype)

        device = z_patch.device
        local_batch_idx = local_batch_idx.to(device)
        local_ps = local_ps.to(device)
        local_pe = local_pe.to(device)
        local_pe = torch.maximum(local_pe, local_ps + 1)

        outs: List[torch.Tensor] = []
        for i in range(M):
            b = int(local_batch_idx[i].item())
            ps = int(local_ps[i].item())
            pe = int(local_pe[i].item())
            seg = z_patch[b, ps:pe, :]  # [L,E]
            m = patch_mask[b, ps:pe].to(seg.dtype).unsqueeze(-1)
            denom = m.sum().clamp(min=1.0)
            outs.append((seg * m).sum(dim=0) / denom)
        return torch.stack(outs, dim=0)