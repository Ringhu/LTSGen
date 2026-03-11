# ts_align/models/text_encoder.py
from __future__ import annotations

from typing import List, Optional

import torch
import torch.nn as nn

try:
    from transformers import AutoModel, AutoTokenizer
except Exception as e:  # pragma: no cover
    AutoModel = None
    AutoTokenizer = None


class TextEncoder(nn.Module):
    """
    HuggingFace encoder with mean pooling. Designed for CLIP-style retrieval.

    By default we **freeze** the HF backbone for stability and speed.
    """
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        max_length: int = 256,
        fine_tune: bool = False,
    ) -> None:
        super().__init__()
        if AutoModel is None or AutoTokenizer is None:
            raise ImportError("transformers is required for TextEncoder. Please pip install transformers.")
        self.model_name = str(model_name)
        self.max_length = int(max_length)

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.out_dim = int(self.model.config.hidden_size)

        if not fine_tune:
            for p in self.model.parameters():
                p.requires_grad = False

    def forward(self, texts: List[str]) -> torch.Tensor:
        device = next(self.model.parameters()).device
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        ).to(device)
        outputs = self.model(**inputs)
        token_embeddings = outputs.last_hidden_state          # [B,L,H]
        attention = inputs["attention_mask"].unsqueeze(-1)    # [B,L,1]
        attention = attention.to(token_embeddings.dtype)
        summed = (token_embeddings * attention).sum(dim=1)    # [B,H]
        denom = attention.sum(dim=1).clamp(min=1e-9)
        return summed / denom
