# ts_align_scripts/eval_grounding_v2.py
from __future__ import annotations

import argparse
from typing import Dict, List, Tuple

import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from ts_align.data import TSCapJSONLDataset, hsa_collate_fn
from ts_align.metrics import Span, hit_at_1_peak, recall_iou_at_k, topk_spans_avg, iou_1d
from ts_align.models import HSAClipModel
from ts_align.utils import load_checkpoint, worker_init_fn


@torch.no_grad()
def encode_all(model: HSAClipModel, loader: DataLoader, device: torch.device):
    """
    Encode all series to get:
      z_patch_list: list of [N,E] (valid patches only)
      z_global_all: [S,E] global embedding for shortlist retrieval
      meta_list: list of dict
      locals_flat: list of (series_idx, gt_s, gt_e, text)
    """
    model.eval()
    z_patch_list: List[torch.Tensor] = []
    z_global_list: List[torch.Tensor] = []
    meta_list: List[dict] = []
    locals_flat: List[Tuple[int, int, int, str]] = []

    series_base = 0
    for batch in tqdm(loader, desc="Encoding series"):
        if not batch:
            continue
        x = batch["x"].to(device)
        lengths = batch["lengths"].to(device)

        enc = model.encode_time(x, lengths)

        if "z_patch" not in enc:
            raise RuntimeError(
                "Model has no z_patch. Grounding requires patch tokens. "
                "Please use time_backbone=patch or time_backbone=hybrid."
            )

        z_patch = enc["z_patch"]        # [B,N,E]
        patch_mask = enc["patch_mask"]  # [B,N]
        z_global = enc["z_global"]      # [B,E]

        B = z_patch.size(0)
        for i in range(B):
            n_valid = int(patch_mask[i].sum().item())
            z_patch_list.append(z_patch[i, :n_valid].cpu())
        z_global_list.append(z_global.cpu())

        meta_list.extend(batch["meta"])

        # flatten locals
        local_texts = batch["local_texts"]
        bidx = batch["local_batch_idx"]
        ps = batch["local_ps"]
        pe = batch["local_pe"]
        for j in range(len(local_texts)):
            si = series_base + int(bidx[j].item())
            gt_s = int(ps[j].item())
            gt_e = int(pe[j].item())
            locals_flat.append((si, gt_s, gt_e, local_texts[j]))

        series_base += B

    Zg = torch.cat(z_global_list, dim=0) if z_global_list else torch.zeros((0, 1))
    return z_patch_list, Zg, meta_list, locals_flat


@torch.no_grad()
def evaluate_within_series(
    model: HSAClipModel,
    z_patch_list: List[torch.Tensor],
    locals_flat: List[Tuple[int, int, int, str]],
    device: torch.device,
    *,
    max_span_len: int,
    topk: int,
) -> Dict[str, float]:
    if not locals_flat:
        return {}

    pred_spans: List[List[Span]] = []
    gt_spans: List[Tuple[int, int]] = []
    hits = []

    texts = [t for (_, _, _, t) in locals_flat]
    z_q_all = []
    bs = 256
    for i in range(0, len(texts), bs):
        z_q_all.append(model.encode_text(texts[i:i + bs]).cpu())
    z_q_all = torch.cat(z_q_all, dim=0)

    scale = model.get_scale()

    for qi, (si, gt_s, gt_e, _) in enumerate(locals_flat):
        z_patch = z_patch_list[si].to(device)   # [N,E]
        n_valid = int(z_patch.shape[0])
        z_q = z_q_all[qi].to(device)

        scores = (z_patch @ z_q) * scale
        preds = topk_spans_avg(scores, n_valid=n_valid, max_span_len=max_span_len, topk=topk)

        pred_spans.append(preds)
        gt_spans.append((gt_s, gt_e))
        hits.append(hit_at_1_peak(scores, n_valid=n_valid, gt_s=gt_s, gt_e=gt_e))

    metrics = recall_iou_at_k(pred_spans, gt_spans, ks=(1, topk), iou_thresholds=(0.3, 0.5, 0.7))
    metrics["Hit@1_peak"] = float(sum(hits) / len(hits))
    return metrics


@torch.no_grad()
def evaluate_full_corpus_shortlist_by_global(
    model: HSAClipModel,
    z_patch_list: List[torch.Tensor],
    Z_global: torch.Tensor,  # [S,E] on CPU
    locals_flat: List[Tuple[int, int, int, str]],
    device: torch.device,
    *,
    max_span_len: int,
    topk: int,
    shortlist: int = 50,
) -> Dict[str, float]:
    """
    Retrieval+Localization:
      1) use global embedding to shortlist series (fast)
      2) decode best span in each shortlisted series
      3) rank candidate spans by score and evaluate (series id must match)
    """
    if not locals_flat:
        return {}

    S = int(Z_global.shape[0])
    if S == 0:
        return {}

    # encode queries
    texts = [t for (_, _, _, t) in locals_flat]
    z_q_all = []
    bs = 256
    for i in range(0, len(texts), bs):
        z_q_all.append(model.encode_text(texts[i:i + bs]).cpu())
    z_q_all = torch.cat(z_q_all, dim=0)  # [Q,E]

    Zg = Z_global.to(device)  # [S,E]
    scale = model.get_scale()

    iou_thresholds = (0.3, 0.5, 0.7)
    ks = (1, topk)

    # mIoU@1
    ious_top1 = []

    # Recall@K IoU@th
    hits = { (k, th): 0 for k in ks for th in iou_thresholds }

    for qi, (gt_series, gt_s, gt_e, _) in enumerate(tqdm(locals_flat, desc="Full-corpus grounding (shortlist)")):
        z_q = z_q_all[qi].to(device)  # [E]

        # shortlist series by global sim
        sim_series = (Zg @ z_q) * scale  # [S]
        k0 = min(int(shortlist), S)
        vals, idxs = torch.topk(sim_series, k=k0, largest=True, sorted=True)
        shortlisted = idxs.tolist()

        # decode best span per shortlisted series
        candidates: List[Tuple[float, int, Span]] = []
        for si in shortlisted:
            z_patch = z_patch_list[si].to(device)
            n_valid = int(z_patch.shape[0])
            scores = (z_patch @ z_q) * scale
            spans = topk_spans_avg(scores, n_valid=n_valid, max_span_len=max_span_len, topk=1)
            if spans:
                candidates.append((spans[0].score, si, spans[0]))

        candidates.sort(key=lambda x: x[0], reverse=True)

        # mIoU@1 with series match
        if candidates:
            _, si1, sp1 = candidates[0]
            if si1 == gt_series:
                ious_top1.append(iou_1d(sp1.start, sp1.end, gt_s, gt_e))
            else:
                ious_top1.append(0.0)
        else:
            ious_top1.append(0.0)

        # Recall@K IoU@th
        for k in ks:
            topk_cand = candidates[:k]
            for th in iou_thresholds:
                ok = False
                for _, si, sp in topk_cand:
                    if si != gt_series:
                        continue
                    if iou_1d(sp.start, sp.end, gt_s, gt_e) >= float(th):
                        ok = True
                        break
                if ok:
                    hits[(k, th)] += 1

    Q = len(locals_flat)
    out: Dict[str, float] = {}
    out["mIoU@1"] = float(sum(ious_top1) / max(1, len(ious_top1)))
    for k in ks:
        for th in iou_thresholds:
            out[f"R@{k} IoU@{th}"] = float(hits[(k, th)] / Q)

    return out


def main():
    p = argparse.ArgumentParser("Evaluate grounding v2")
    p.add_argument("--jsonl", required=True)
    p.add_argument("--ckpt", required=True)
    p.add_argument("--batch_size", type=int, default=64)
    p.add_argument("--num_workers", type=int, default=4)
    p.add_argument("--max_records", type=int, default=None)
    p.add_argument("--max_span_len", type=int, default=32)
    p.add_argument("--topk", type=int, default=5)
    p.add_argument("--shortlist", type=int, default=50)
    p.add_argument("--run_full_corpus", type=int, default=0, help="1 to run full-corpus (shortlist by global)")
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = load_checkpoint(args.ckpt, map_location=device)
    train_args = ckpt.get("args", {})

    global_caps = train_args.get("global_captions", train_args.get("global_caption", "global_zh"))
    local_caption = train_args.get("local_caption", "local_zh")
    non_numeric_local = bool(train_args.get("non_numeric_local", 0))

    ds = TSCapJSONLDataset(
        args.jsonl,
        max_records=args.max_records,
        seed=0,
        global_caption=global_caps,
        local_caption=local_caption,
        non_numeric_local=non_numeric_local,
    )
    in_channels = int(ds[0]["x"].shape[0])

    def collate_eval(b):
        return hsa_collate_fn(
            b,
            patch_size=int(train_args.get("patch_size", 16)),
            max_local_per_sample=int(train_args.get("max_local_per_sample", 4)),
            max_global_texts_per_sample=1,  # grounding只需要locals，global随便
            positive_key=str(train_args.get("positive_key", "instance")),
            random_crop=False,
            seed=0,
        )

    loader = DataLoader(
        ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=collate_eval,
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
        dropout=float(train_args.get("dropout", 0.1)),
        fine_tune_text=(int(train_args.get("freeze_text", 1)) == 0),

        time_backbone=str(train_args.get("time_backbone", "patch")),
        chronos2_model=str(train_args.get("chronos2_model", "autogluon/chronos-2")),
        chronos2_device_map=str(train_args.get("chronos2_device_map", "cuda")),
        chronos2_dtype=train_args.get("chronos2_dtype", "bfloat16"),
        fine_tune_chronos2=bool(train_args.get("fine_tune_chronos2", 0)),
        chronos2_channel_pool=str(train_args.get("chronos2_channel_pool", "first")),

        hier_pool=bool(train_args.get("hier_pool", 0)),
        hier_stride=int(train_args.get("hier_stride", 4)),
        hier_pool_for_global=bool(train_args.get("hier_pool_for_global", 1)),
    ).to(device)
    model.load_state_dict(ckpt["model_state_dict"], strict=True)

    z_patch_list, Z_global, meta_list, locals_flat = encode_all(model, loader, device)
    print(f"[INFO] series={len(z_patch_list)}, local_queries={len(locals_flat)}")

    m_within = evaluate_within_series(
        model, z_patch_list, locals_flat, device,
        max_span_len=args.max_span_len, topk=args.topk
    )
    print("\n=== Grounding: within-series ===")
    for k, v in m_within.items():
        print(f"{k}: {v:.4f}")

    if args.run_full_corpus == 1:
        m_full = evaluate_full_corpus_shortlist_by_global(
            model, z_patch_list, Z_global, locals_flat, device,
            max_span_len=args.max_span_len, topk=args.topk, shortlist=args.shortlist
        )
        print("\n=== Grounding: full-corpus (shortlist by global) ===")
        for k, v in m_full.items():
            print(f"{k}: {v:.4f}")


if __name__ == "__main__":
    main()
