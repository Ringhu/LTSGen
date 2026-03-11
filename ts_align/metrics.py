# ts_align/metrics.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import torch


def ranks_from_sim(sim: torch.Tensor, dim_candidates: int = 1) -> torch.Tensor:
    """
    Compute 1-based ranks for diagonal ground truth in a similarity matrix.

    sim: [N, N], higher is better.
    For Text->TS: sim[text_i, ts_j], gt is j=i (diagonal), candidates are columns => dim_candidates=1.
    For TS->Text: dim_candidates=0.
    """
    assert sim.ndim == 2 and sim.shape[0] == sim.shape[1]
    N = sim.shape[0]
    if dim_candidates == 1:
        ranks = torch.argsort(sim, dim=1, descending=True)  # [N,N] indices of candidates per query
        gt = torch.arange(N, device=sim.device)
        pos = (ranks == gt[:, None]).nonzero(as_tuple=False)  # [N,2]
        # pos[:,0] is query index, pos[:,1] is rank-1
        out = torch.empty((N,), device=sim.device, dtype=torch.long)
        out[pos[:, 0]] = pos[:, 1] + 1
        return out
    else:
        ranks = torch.argsort(sim, dim=0, descending=True)  # [N,N] indices of candidates per query(col)
        gt = torch.arange(N, device=sim.device)
        pos = (ranks == gt[None, :]).nonzero(as_tuple=False)
        out = torch.empty((N,), device=sim.device, dtype=torch.long)
        out[pos[:, 1]] = pos[:, 0] + 1
        return out


def recall_at_k_from_ranks(ranks: torch.Tensor, ks: Sequence[int]) -> Dict[int, float]:
    out = {}
    r = ranks.detach().cpu().numpy()
    for k in ks:
        k = int(k)
        out[k] = float((r <= k).mean())
    return out


def mrr_from_ranks(ranks: torch.Tensor) -> float:
    r = ranks.detach().cpu().numpy().astype(np.float32)
    return float((1.0 / r).mean())


def summarize_ranks(ranks: torch.Tensor, ks: Sequence[int] = (1, 5, 10)) -> Dict[str, float]:
    r = ranks.detach().cpu().numpy()
    out: Dict[str, float] = {}
    for k, v in recall_at_k_from_ranks(ranks, ks).items():
        out[f"R@{k}"] = v
    out["MedR"] = float(np.median(r))
    out["MeanR"] = float(np.mean(r))
    out["MRR"] = mrr_from_ranks(ranks)
    return out


def iou_1d(a0: int, a1: int, b0: int, b1: int) -> float:
    """IoU for half-open intervals [a0,a1) and [b0,b1) in patch indices."""
    a0, a1, b0, b1 = int(a0), int(a1), int(b0), int(b1)
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    if union <= 0:
        return 0.0
    return float(inter / union)


@dataclass
class Span:
    start: int
    end: int  # exclusive
    score: float


def topk_spans_avg(
    scores: torch.Tensor,
    *,
    n_valid: int,
    max_span_len: int,
    topk: int,
) -> List[Span]:
    """
    Enumerate spans and return top-k by **average** score over the span.
    scores: [N] tensor (can be on GPU).
    n_valid: number of valid patches (mask True count). We use scores[:n_valid].
    max_span_len: maximum span length in patches.
    """
    n_valid = int(n_valid)
    topk = int(topk)
    max_span_len = int(max_span_len)
    if n_valid <= 0:
        return []
    s = scores[:n_valid]  # [N]
    N = int(s.numel())
    max_span_len = max(1, min(max_span_len, N))

    ps = torch.zeros((N + 1,), device=s.device, dtype=s.dtype)
    ps[1:] = torch.cumsum(s, dim=0)  # prefix sum

    spans: List[Span] = []
    # Enumerate by length using prefix sums; complexity O(N*max_span_len).
    for L in range(1, max_span_len + 1):
        # window sums for all start positions
        sums = ps[L:] - ps[:-L]  # [N-L+1]
        avgs = sums / float(L)
        if avgs.numel() == 0:
            continue
        # take local topk for this length to reduce candidates
        kL = min(topk, int(avgs.numel()))
        vals, idxs = torch.topk(avgs, k=kL, largest=True, sorted=False)
        for v, st in zip(vals.tolist(), idxs.tolist()):
            spans.append(Span(start=int(st), end=int(st + L), score=float(v)))

    # global topk over all candidate spans
    spans.sort(key=lambda x: x.score, reverse=True)
    return spans[:topk]


def hit_at_1_peak(scores: torch.Tensor, *, n_valid: int, gt_s: int, gt_e: int) -> float:
    """
    Pointing-game Hit@1: does argmax patch fall into GT span?
    gt_s/gt_e are in patch indices, half-open [gt_s, gt_e).
    """
    n_valid = int(n_valid)
    if n_valid <= 0:
        return 0.0
    idx = int(torch.argmax(scores[:n_valid]).item())
    return 1.0 if (gt_s <= idx < gt_e) else 0.0


def recall_iou_at_k(
    pred_spans: List[List[Span]],
    gt_spans: List[Tuple[int, int]],
    *,
    ks: Sequence[int] = (1, 5),
    iou_thresholds: Sequence[float] = (0.3, 0.5, 0.7),
) -> Dict[str, float]:
    """
    pred_spans: list over queries, each is list of predicted spans ordered by score desc.
    gt_spans: list over queries, each is (gt_s, gt_e) in patch indices, half-open.
    """
    assert len(pred_spans) == len(gt_spans)
    Q = len(gt_spans)
    out: Dict[str, float] = {}
    if Q == 0:
        for k in ks:
            for th in iou_thresholds:
                out[f"R@{int(k)} IoU@{th}"] = 0.0
        out["mIoU@1"] = 0.0
        return out

    # mIoU@1
    ious_top1 = []
    for preds, (gs, ge) in zip(pred_spans, gt_spans):
        if not preds:
            ious_top1.append(0.0)
            continue
        ious_top1.append(iou_1d(preds[0].start, preds[0].end, gs, ge))
    out["mIoU@1"] = float(np.mean(ious_top1))

    # Recall@K with IoU threshold
    for k in ks:
        k = int(k)
        for th in iou_thresholds:
            hit = 0
            for preds, (gs, ge) in zip(pred_spans, gt_spans):
                ok = False
                for p in preds[:k]:
                    if iou_1d(p.start, p.end, gs, ge) >= float(th):
                        ok = True
                        break
                hit += 1 if ok else 0
            out[f"R@{k} IoU@{th}"] = float(hit / Q)
    return out


@torch.no_grad()
def ranks_from_sim_multipos(
    sim: torch.Tensor,             # [Q, C]
    group_q: torch.Tensor,         # [Q]
    group_c: torch.Tensor,         # [C]
    *,
    dim_candidates: int = 1,
) -> torch.Tensor:
    """
    Multi-positive rank: for each query, rank of the FIRST candidate whose group matches.

    For Text->TS: sim[text_i, ts_j], candidates are columns => dim_candidates=1.
    For TS->Text: sim[ts_i, text_j], candidates are columns => dim_candidates=1.
    """
    assert sim.ndim == 2
    Q, C = sim.shape
    device = sim.device
    group_q = group_q.to(device)
    group_c = group_c.to(device)

    # sort candidates per query
    if dim_candidates != 1:
        raise ValueError("This helper expects candidates along dim=1 (columns).")

    order = torch.argsort(sim, dim=1, descending=True)  # [Q,C]
    # iterate (vectorized-ish) to find first matching group
    ranks = torch.full((Q,), fill_value=C + 1, device=device, dtype=torch.long)

    # reorder group_c by candidate order => [Q,C]
    cand_groups = group_c[order]
    match = (cand_groups == group_q[:, None])  # [Q,C]
    has = match.any(dim=1)
    if has.any():
        # argmax on boolean gives first True only if we convert:
        # we want first True index; do cumulative trick
        # idx = first position where match is True
        idx = torch.argmax(match.to(torch.int32), dim=1)  # returns 0 if all False too
        # but for all-False rows, idx is 0; we guard with has mask
        ranks[has] = idx[has] + 1

    return ranks


@torch.no_grad()
def summarize_retrieval(
    z_ts: torch.Tensor, z_txt: torch.Tensor,
    *,
    group_ids_ts: torch.Tensor,
    group_ids_txt: torch.Tensor,
    ks: Sequence[int] = (1, 5, 10),
) -> Dict[str, float]:
    """
    Return a dict with both directions:
      - T2S/R@k, T2S/MedR, T2S/MRR
      - S2T/R@k, ...
    """
    # sim: [M,B] for text->ts
    sim_t2s = z_txt @ z_ts.t()
    ranks_t2s = ranks_from_sim_multipos(sim_t2s, group_ids_txt, group_ids_ts, dim_candidates=1)
    out = {f"T2S/{k}": v for k, v in _summ(ranks_t2s, ks).items()}

    # sim: [B,M] for ts->text
    sim_s2t = z_ts @ z_txt.t()
    ranks_s2t = ranks_from_sim_multipos(sim_s2t, group_ids_ts, group_ids_txt, dim_candidates=1)
    out.update({f"S2T/{k}": v for k, v in _summ(ranks_s2t, ks).items()})
    return out


def _summ(ranks: torch.Tensor, ks: Sequence[int]) -> Dict[str, float]:
    r = ranks.detach().cpu().numpy()
    out: Dict[str, float] = {}
    for k in ks:
        out[f"R@{int(k)}"] = float((r <= int(k)).mean())
    out["MedR"] = float(np.median(r))
    out["MeanR"] = float(np.mean(r))
    out["MRR"] = float((1.0 / r.astype(np.float32)).mean())
    return out