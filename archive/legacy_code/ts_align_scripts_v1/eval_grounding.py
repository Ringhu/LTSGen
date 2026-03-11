from __future__ import annotations

import argparse
from typing import Dict, List, Tuple

import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from ts_align.data import TSCapJSONLDataset, hsa_collate_fn
from ts_align.metrics import Span, hit_at_1_peak, recall_iou_at_k, topk_spans_avg
from ts_align.models import HSAClipModel
from ts_align.utils import load_checkpoint, worker_init_fn


@torch.no_grad()
def encode_all(model: HSAClipModel, loader: DataLoader, device: torch.device):
    """
    Encode all series to get patch embeddings for grounding.
    Returns lists aligned by dataset order:
      z_patch_list: list of [N,E]
      patch_mask_list: list of [N] bool
      meta_list: list of dict
      global_texts: list of str
      locals_flat: list of (series_idx, gt_s, gt_e, text)
    """
    model.eval()
    z_patch_list = []
    patch_mask_list = []
    meta_list = []
    global_texts = []
    locals_flat = []  # list of tuples (series_global_idx, gt_ps, gt_pe, text)

    series_base = 0
    for batch in tqdm(loader, desc="Encoding series"):
        if not batch:
            continue
        x = batch["x"].to(device)
        lengths = batch["lengths"].to(device)
        enc = model.encode_time(x, lengths)
        z_patch = enc["z_patch"]      # [B,N,E]
        patch_mask = enc["patch_mask"]  # [B,N]
        B = z_patch.size(0)

        # record series embeddings
        for i in range(B):
            n_valid = int(patch_mask[i].sum().item())
            z_patch_list.append(z_patch[i, :n_valid].cpu())
            patch_mask_list.append(patch_mask[i, :n_valid].cpu())
        meta_list.extend(batch["meta"])
        global_texts.extend(batch["global_texts"])

        # flatten locals
        local_texts = batch["local_texts"]
        bidx = batch["local_batch_idx"]
        ps = batch["local_ps"]
        pe = batch["local_pe"]
        for j in range(len(local_texts)):
            si = series_base + int(bidx[j].item())  # global series index
            gt_s = int(ps[j].item())
            gt_e = int(pe[j].item())
            locals_flat.append((si, gt_s, gt_e, local_texts[j]))

        series_base += B

    return z_patch_list, patch_mask_list, meta_list, global_texts, locals_flat


@torch.no_grad()
def evaluate_within_series(
    model: HSAClipModel,
    z_patch_list: List[torch.Tensor],
    patch_mask_list: List[torch.Tensor],
    locals_flat: List[Tuple[int, int, int, str]],
    device: torch.device,
    *,
    max_span_len: int,
    topk: int,
) -> Dict[str, float]:
    """
    Localization-only: for each local caption, localize within its parent series only.
    """
    if not locals_flat:
        return {}

    pred_spans: List[List[Span]] = []
    gt_spans: List[Tuple[int, int]] = []
    hits = []

    # batch text encoding for speed
    texts = [t for (_, _, _, t) in locals_flat]
    z_q_all = []
    bs = 256
    for i in range(0, len(texts), bs):
        z_q_all.append(model.encode_text(texts[i:i+bs]).cpu())
    z_q_all = torch.cat(z_q_all, dim=0)  # [Q,E]

    for qi, (si, gt_s, gt_e, _) in enumerate(locals_flat):
        z_patch = z_patch_list[si].to(device)   # [N,E]
        n_valid = int(z_patch.shape[0])
        z_q = z_q_all[qi].to(device)            # [E]
        scores = (z_patch @ z_q) * model.get_scale()  # [N]
        preds = topk_spans_avg(scores, n_valid=n_valid, max_span_len=max_span_len, topk=topk)
        pred_spans.append(preds)
        gt_spans.append((gt_s, gt_e))
        hits.append(hit_at_1_peak(scores, n_valid=n_valid, gt_s=gt_s, gt_e=gt_e))

    metrics = recall_iou_at_k(pred_spans, gt_spans, ks=(1, topk), iou_thresholds=(0.3, 0.5, 0.7))
    metrics["Hit@1_peak"] = float(sum(hits) / len(hits))
    return metrics


@torch.no_grad()
def evaluate_full_corpus(
    model: HSAClipModel,
    z_patch_list: List[torch.Tensor],
    locals_flat: List[Tuple[int, int, int, str]],
    device: torch.device,
    *,
    max_span_len: int,
    topk: int,
    shortlist: int = 50,
) -> Dict[str, float]:
    """
    Retrieval+Localization: for each local caption, retrieve top segments over the full corpus.

    Approximation for efficiency:
      1) score each series by its **max patch similarity** to the query (series-level)
      2) take top `shortlist` series
      3) within each shortlisted series, decode its best span (top-1) and use as segment candidate
      4) rank all candidates by their span score; evaluate top-K segments
    """
    if not locals_flat:
        return {}

    Q = len(locals_flat)

    # encode all query texts in batches
    texts = [t for (_, _, _, t) in locals_flat]
    z_q_all = []
    bs = 256
    for i in range(0, len(texts), bs):
        z_q_all.append(model.encode_text(texts[i:i+bs]).cpu())
    z_q_all = torch.cat(z_q_all, dim=0)  # [Q,E]

    pred_spans_all: List[List[Span]] = []
    gt_spans_all: List[Tuple[int, int]] = []

    for qi, (gt_series, gt_s, gt_e, _) in enumerate(tqdm(locals_flat, desc="Full-corpus grounding")):
        z_q = z_q_all[qi].to(device)  # [E]
        scale = model.get_scale()

        # series score by max patch similarity
        series_scores = []
        for si in range(len(z_patch_list)):
            z_patch = z_patch_list[si].to(device)
            # max over patches
            s = (z_patch @ z_q).max().item()
            series_scores.append((s, si))
        series_scores.sort(key=lambda x: x[0], reverse=True)
        shortlisted = [si for (_, si) in series_scores[:min(shortlist, len(series_scores))]]

        # generate one best span per shortlisted series
        candidates: List[Tuple[float, int, Span]] = []  # (score, series_id, span)
        for si in shortlisted:
            z_patch = z_patch_list[si].to(device)
            n_valid = int(z_patch.shape[0])
            scores = (z_patch @ z_q) * scale  # [N]
            spans = topk_spans_avg(scores, n_valid=n_valid, max_span_len=max_span_len, topk=1)
            if spans:
                candidates.append((spans[0].score, si, spans[0]))

        # rank segment candidates globally; keep topk
        candidates.sort(key=lambda x: x[0], reverse=True)
        preds: List[Span] = []
        for score, si, sp in candidates[:topk]:
            # encode series id into span by shifting start/end to avoid collisions? we handle separately in evaluation:
            # For full-corpus evaluation, we require series id match; we store it in Span.score sign? Better: wrap in a tuple.
            # Here we hack: set negative start to store series id is ugly. Instead we'll evaluate manually below.
            preds.append(Span(start=sp.start, end=sp.end, score=float(score)))

        # For recall_iou_at_k, we need to check both series id and IoU.
        # We'll store series id parallel list.
        pred_spans_all.append(preds)
        gt_spans_all.append((gt_s, gt_e))

    # Manual evaluation with series id condition:
    # Since recall_iou_at_k doesn't track series id, we recompute metrics here.
    # We'll do R@K IoU@th with a series-match check.
    iou_thresholds = (0.3, 0.5, 0.7)
    ks = (1, topk)
    out: Dict[str, float] = {}

    # Compute mIoU@1 with series check.
    ious = []
    for qi, (gt_series, gt_s, gt_e, _) in enumerate(locals_flat):
        # recompute top1 series by candidates again (we didn't store series ids); redo shortlisting quickly:
        z_q = z_q_all[qi].to(device)
        scale = model.get_scale()
        best_score = None
        best_si = None
        best_span = None
        for si in range(len(z_patch_list)):
            z_patch = z_patch_list[si].to(device)
            scores = (z_patch @ z_q) * scale
            spans = topk_spans_avg(scores, n_valid=int(z_patch.shape[0]), max_span_len=max_span_len, topk=1)
            if not spans:
                continue
            sc = spans[0].score
            if best_score is None or sc > best_score:
                best_score = sc
                best_si = si
                best_span = spans[0]
        if best_si == gt_series and best_span is not None:
            ious.append(float((min(best_span.end, gt_e) - max(best_span.start, gt_s)) / max(1e-9, (best_span.end-best_span.start) + (gt_e-gt_s) - max(0, min(best_span.end, gt_e) - max(best_span.start, gt_s)))))
        else:
            ious.append(0.0)
    out["mIoU@1"] = float(sum(ious) / max(1, len(ious)))

    # R@K IoU@th: compute topK segment candidates with series ids (redo per query; acceptable for moderate Q).
    for k in ks:
        for th in iou_thresholds:
            hit = 0
            for qi, (gt_series, gt_s, gt_e, _) in enumerate(locals_flat):
                z_q = z_q_all[qi].to(device)
                scale = model.get_scale()
                # collect candidates from all series (slow but ok for baseline)
                candidates = []
                for si in range(len(z_patch_list)):
                    z_patch = z_patch_list[si].to(device)
                    scores = (z_patch @ z_q) * scale
                    spans = topk_spans_avg(scores, n_valid=int(z_patch.shape[0]), max_span_len=max_span_len, topk=1)
                    if spans:
                        candidates.append((spans[0].score, si, spans[0]))
                candidates.sort(key=lambda x: x[0], reverse=True)
                ok = False
                for _, si, sp in candidates[:k]:
                    if si != gt_series:
                        continue
                    # IoU
                    inter = max(0, min(sp.end, gt_e) - max(sp.start, gt_s))
                    union = (sp.end - sp.start) + (gt_e - gt_s) - inter
                    iou = inter / union if union > 0 else 0.0
                    if iou >= th:
                        ok = True
                        break
                hit += 1 if ok else 0
            out[f"R@{k} IoU@{th}"] = float(hit / Q)

    return out


def main():
    p = argparse.ArgumentParser("Evaluate local grounding (within-series and full-corpus)")
    p.add_argument("--jsonl", required=True)
    p.add_argument("--ckpt", required=True)
    p.add_argument("--batch_size", type=int, default=64)
    p.add_argument("--num_workers", type=int, default=4)
    p.add_argument("--max_records", type=int, default=None)
    p.add_argument("--local_caption", default=None, help="Override local caption mode (local_en/local_zh)")
    p.add_argument("--non_numeric_local", type=int, default=None, help="Override number stripping (1/0)")
    p.add_argument("--max_span_len", type=int, default=32, help="Max predicted span length in patches")
    p.add_argument("--topk", type=int, default=5)
    p.add_argument("--shortlist", type=int, default=50)
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = load_checkpoint(args.ckpt, map_location=device)
    train_args = ckpt.get("args", {})

    local_caption = args.local_caption or train_args.get("local_caption", "local_en")
    global_caption = train_args.get("global_caption", "global_en")
    non_numeric_local = bool(args.non_numeric_local) if args.non_numeric_local is not None else bool(train_args.get("non_numeric_local", 0))

    ds = TSCapJSONLDataset(
        args.jsonl,
        max_records=args.max_records,
        seed=0,
        global_caption=global_caption,
        local_caption=local_caption,
        non_numeric_local=non_numeric_local,
    )
    in_channels = int(ds[0]["x"].shape[0])

    patch_size = int(train_args.get("patch_size", 16))
    collate = lambda b: hsa_collate_fn(b, patch_size=patch_size, max_local_per_sample=int(train_args.get("max_local_per_sample", 4)))

    loader = DataLoader(
        ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=collate,
        worker_init_fn=worker_init_fn,
        persistent_workers=(args.num_workers > 0),
    )

    model = HSAClipModel(
        in_channels=in_channels,
        patch_size=int(train_args.get("patch_size", 16)),
        d_model=int(train_args.get("d_model", 256)),
        n_time_layers=int(train_args.get("time_layers", 6)),
        n_time_heads=int(train_args.get("time_heads", 8)),
        text_model=str(train_args.get("text_model", "sentence-transformers/all-MiniLM-L6-v2")),
        d_embed=int(train_args.get("d_embed", 256)),
        dropout=float(train_args.get("dropout", 0.0)),
        fine_tune_text=(int(train_args.get("freeze_text", 1)) == 0),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"], strict=True)

    z_patch_list, patch_mask_list, meta_list, global_texts, locals_flat = encode_all(model, loader, device)

    print(f"[INFO] series={len(z_patch_list)}, local_queries={len(locals_flat)}")

    m_within = evaluate_within_series(
        model, z_patch_list, patch_mask_list, locals_flat, device,
        max_span_len=args.max_span_len, topk=args.topk
    )
    print("\n=== Grounding: within-series (localization only) ===")
    for k, v in m_within.items():
        print(f"{k}: {v:.4f}")

    # Full-corpus evaluation can be expensive; keep as optional baseline.
    m_full = evaluate_full_corpus(
        model, z_patch_list, locals_flat, device,
        max_span_len=args.max_span_len, topk=args.topk, shortlist=args.shortlist
    )
    print("\n=== Grounding: full-corpus (retrieval + localization) ===")
    for k, v in m_full.items():
        print(f"{k}: {v:.4f}")


if __name__ == "__main__":
    main()
