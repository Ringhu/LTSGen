# ts_align/models/layers.py
import math
import torch
import torch.nn as nn


class RevIN(nn.Module):
    """
    Reversible Instance Normalization (ICLR 2022).
    We only use 'norm' during encoding to reduce per-series scale shift.
    """
    def __init__(self, num_features: int, eps: float = 1e-5, affine: bool = True):
        super().__init__()
        self.num_features = int(num_features)
        self.eps = float(eps)
        self.affine = bool(affine)
        if self.affine:
            self.affine_weight = nn.Parameter(torch.ones(self.num_features))
            self.affine_bias = nn.Parameter(torch.zeros(self.num_features))

    def forward(self, x: torch.Tensor, mode: str) -> torch.Tensor:
        if mode == "norm":
            self._get_statistics(x)
            return self._normalize(x)
        if mode == "denorm":
            return self._denormalize(x)
        raise ValueError(f"Unknown mode: {mode}")

    def _get_statistics(self, x: torch.Tensor) -> None:
        # x: [B,C,T] => reduce over T
        dim2reduce = (2,)
        self.mean = torch.mean(x, dim=dim2reduce, keepdim=True).detach()
        self.stdev = torch.sqrt(torch.var(x, dim=dim2reduce, keepdim=True, unbiased=False) + self.eps).detach()

    def _normalize(self, x: torch.Tensor) -> torch.Tensor:
        x = (x - self.mean) / self.stdev
        if self.affine:
            w = self.affine_weight[None, :, None]
            b = self.affine_bias[None, :, None]
            x = x * w + b
        return x

    def _denormalize(self, x: torch.Tensor) -> torch.Tensor:
        if self.affine:
            w = self.affine_weight[None, :, None]
            b = self.affine_bias[None, :, None]
            x = (x - b) / (w + 1e-10)
        return x * self.stdev + self.mean


class SinusoidalPositionalEmbedding(nn.Module):
    """Standard sinusoidal positional embedding."""
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0), persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B,N,D]
        return x + self.pe[:, : x.size(1), :]
