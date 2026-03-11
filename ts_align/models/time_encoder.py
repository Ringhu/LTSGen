# ts_align/models/time_encoder.py
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .layers import SinusoidalPositionalEmbedding


def _ceil_div(a: int, b: int) -> int:
    return (int(a) + int(b) - 1) // int(b)


class PatchTimeEncoder(nn.Module):
    """
    Patchify time series with 1D conv (kernel=stride=patch_size), then a Transformer encoder.

    Input: x [B,C,T]
    Output:
      H [B,N,D], patch_mask [B,N] where True indicates valid patches
    """
    def __init__(
        self,
        *,
        in_channels: int,
        d_model: int = 256,
        patch_size: int = 16,
        n_layers: int = 6,
        n_heads: int = 8,
        dropout: float = 0.1,
        max_len: int = 5000,
    ) -> None:
        super().__init__()
        self.in_channels = int(in_channels)
        self.d_model = int(d_model)
        self.patch_size = int(patch_size)

        self.patch_proj = nn.Conv1d(
            in_channels=self.in_channels,
            out_channels=self.d_model,
            kernel_size=self.patch_size,
            stride=self.patch_size,
            bias=True,
        )
        self.pos_emb = SinusoidalPositionalEmbedding(self.d_model, max_len=max_len)

        enc_layer = nn.TransformerEncoderLayer(
            d_model=self.d_model,
            nhead=max(1, int(n_heads)),
            dim_feedforward=self.d_model * 4,
            dropout=float(dropout),
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=int(n_layers))
        self.dropout = nn.Dropout(float(dropout))
        self.norm = nn.LayerNorm(self.d_model)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        B, C, T = x.shape
        ps = self.patch_size

        # pad to multiple of patch_size for conv
        T_pad = _ceil_div(int(T), ps) * ps
        if T_pad != int(T):
            x = F.pad(x, (0, T_pad - int(T)), mode="constant", value=0.0)

        h = self.patch_proj(x)           # [B,D,N]
        h = h.transpose(1, 2).contiguous()  # [B,N,D]
        h = self.pos_emb(h)

        N = int(h.shape[1])
        # patch mask based on original lengths
        patch_mask = torch.zeros((B, N), dtype=torch.bool, device=x.device)
        for i in range(B):
            npi = _ceil_div(int(lengths[i].item()), ps)
            npi = max(1, min(npi, N))
            patch_mask[i, :npi] = True

        key_padding_mask = ~patch_mask  # True = pad
        h = self.dropout(h)
        h = self.encoder(h, src_key_padding_mask=key_padding_mask)
        h = self.norm(h)
        return h, patch_mask
