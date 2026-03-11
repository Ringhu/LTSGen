# ts_align/losses.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F



def clip_infonce(z_a: torch.Tensor, z_b: torch.Tensor, logit_scale: torch.Tensor) -> torch.Tensor:
    """
    Standard symmetric CLIP loss (in-batch negatives).
    z_a: [B,E], z_b: [B,E] (already L2-normalized)
    """
    logits = logit_scale * (z_a @ z_b.t())  # [B,B]
    labels = torch.arange(logits.size(0), device=logits.device)
    loss_a = F.cross_entropy(logits, labels)
    loss_b = F.cross_entropy(logits.t(), labels)
    return 0.5 * (loss_a + loss_b)


def clip_infonce_multipos(
    z_ts: torch.Tensor,             # [B,E]
    z_txt: torch.Tensor,            # [M,E]
    logit_scale: torch.Tensor,      # scalar (>0)
    *,
    group_ids_ts: torch.Tensor,     # [B] long
    group_ids_txt: torch.Tensor,    # [M] long
) -> torch.Tensor:
    """
    Multi-positive symmetric CLIP loss.

    A text i can have multiple positive time-series j where group_ids match.
    Likewise, a time-series j can have multiple positive texts i.

    loss_txt(i) = -log sum_{j in P(i)} exp(sim(i,j)) / sum_{j} exp(sim(i,j))
    loss_ts(j)  = -log sum_{i in P(j)} exp(sim(i,j)) / sum_{i} exp(sim(i,j))
    return 0.5*(mean_i loss_txt + mean_j loss_ts)
    """
    if z_ts.numel() == 0 or z_txt.numel() == 0:
        return torch.zeros((), device=z_ts.device)

    device = z_ts.device
    group_ids_ts = group_ids_ts.to(device)
    group_ids_txt = group_ids_txt.to(device)

    # logits_txt2ts: [M,B]
    logits_txt2ts = logit_scale * (z_txt @ z_ts.t())

    # positives mask: [M,B]
    pos_txt2ts = (group_ids_txt[:, None] == group_ids_ts[None, :])

    # text -> ts
    log_den = torch.logsumexp(logits_txt2ts, dim=1)  # [M]
    # use a very negative number rather than -inf for stability under mixed precision
    logits_pos = logits_txt2ts.masked_fill(~pos_txt2ts, -1e4)
    valid = pos_txt2ts.any(dim=1)
    if valid.any():
        log_num = torch.logsumexp(logits_pos[valid], dim=1)  # [m_valid]
        loss_txt = -(log_num - log_den[valid]).mean()
    else:
        loss_txt = torch.zeros((), device=device)

    # ts -> text
    logits_ts2txt = logits_txt2ts.t()          # [B,M]
    pos_ts2txt = pos_txt2ts.t()                # [B,M]
    log_den2 = torch.logsumexp(logits_ts2txt, dim=1)  # [B]
    logits_pos2 = logits_ts2txt.masked_fill(~pos_ts2txt, -1e4)
    valid2 = pos_ts2txt.any(dim=1)
    if valid2.any():
        log_num2 = torch.logsumexp(logits_pos2[valid2], dim=1)
        loss_ts = -(log_num2 - log_den2[valid2]).mean()
    else:
        loss_ts = torch.zeros((), device=device)

    return 0.5 * (loss_txt + loss_ts)

def local_clip_infonce(z_ts: torch.Tensor, z_txt: torch.Tensor, logit_scale: torch.Tensor) -> torch.Tensor:
    """
    Local event CLIP loss.
    z_ts: [M,E], z_txt: [M,E]
    """
    if z_ts.numel() == 0:
        return torch.zeros((), device=z_ts.device)
    logits = logit_scale * (z_ts @ z_txt.t())  # [M,M]
    labels = torch.arange(logits.size(0), device=logits.device)
    return 0.5 * (F.cross_entropy(logits, labels) + F.cross_entropy(logits.t(), labels))


def span_localization_loss(
    *,
    z_patch: torch.Tensor,      # [B,N,E] (L2-normalized patch embeddings)
    patch_mask: torch.Tensor,   # [B,N] bool (True=valid)
    z_query: torch.Tensor,      # [M,E] (L2-normalized text embeddings)
    local_batch_idx: torch.Tensor,  # [M]
    local_ps: torch.Tensor,         # [M] start patch idx (inclusive)
    local_pe: torch.Tensor,         # [M] end patch idx (exclusive)
    logit_scale: torch.Tensor,
    reduction: str = "mean",
) -> torch.Tensor:
    """
    For each query i:
      scores_j = scale * dot(z_patch[b, j], z_query[i])
      p = softmax(scores over j)
      loss_i = - mean_{j in [ps,pe)} log p_j

    Vectorized by grouping queries that belong to the same batch item b.
    """
    M = int(z_query.shape[0])
    if M == 0:
        return torch.zeros((), device=z_patch.device)

    device = z_patch.device
    local_batch_idx = local_batch_idx.to(device)
    local_ps = local_ps.to(device)
    local_pe = local_pe.to(device)

    # Make sure pe > ps
    local_pe = torch.maximum(local_pe, local_ps + 1)

    losses: List[torch.Tensor] = []
    for b in torch.unique(local_batch_idx).tolist():
        b = int(b)
        idxs = (local_batch_idx == b).nonzero(as_tuple=False).squeeze(1)  # [m]
        if idxs.numel() == 0:
            continue
        q = z_query[idxs]  # [m,E]
        ps = local_ps[idxs]  # [m]
        pe = local_pe[idxs]  # [m]
        # scores: [N,m]
        scores = logit_scale * (z_patch[b] @ q.t())
        # mask invalid patches
        m = patch_mask[b].unsqueeze(1)  # [N,1]
        scores = scores.masked_fill(~m, -1e4)
        # log-softmax over patches (dim=0)
        logp = F.log_softmax(scores, dim=0)  # [N,m]
        # interval mean log prob using prefix sums
        # psum[k] = sum_{j<k} logp[j]
        psum = torch.zeros((logp.size(0) + 1, logp.size(1)), device=device, dtype=logp.dtype)
        psum[1:] = torch.cumsum(logp, dim=0)
        ar = torch.arange(logp.size(1), device=device)
        interval_sum = psum[pe, ar] - psum[ps, ar]  # [m]
        denom = (pe - ps).to(logp.dtype).clamp(min=1.0)
        loss_b = -(interval_sum / denom)  # [m]
        losses.append(loss_b)

    if not losses:
        return torch.zeros((), device=device)
    loss_all = torch.cat(losses, dim=0)
    if reduction == "mean":
        return loss_all.mean()
    if reduction == "sum":
        return loss_all.sum()
    return loss_all
