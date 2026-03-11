from __future__ import annotations

import argparse
from typing import Dict

import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from ts_align.data import TSCapJSONLDataset, hsa_collate_fn
from ts_align.metrics import ranks_from_sim, summarize_ranks
from ts_align.models import HSAClipModel
from ts_align.utils import load_checkpoint, worker_init_fn


@torch.no_grad()
def compute_embeddings(model: HSAClipModel, loader: DataLoader, device: torch.device):
    model.eval()
    Z_ts = []
    Z_txt = []
    for batch in tqdm(loader, desc="Embedding"):
        if not batch:
            continue
        x = batch["x"].to(device)
        lengths = batch["lengths"].to(device)
        texts = batch["global_texts"]
        enc = model.encode_time(x, lengths)
        Z_ts.append(enc["z_global"].cpu())
        Z_txt.append(model.encode_text(texts).cpu())
    if not Z_ts:
        return None, None
    return torch.cat(Z_ts, dim=0), torch.cat(Z_txt, dim=0)


def main():
    p = argparse.ArgumentParser("Evaluate global retrieval (Text↔TS)")
    p.add_argument("--jsonl", required=True)
    p.add_argument("--ckpt", required=True)
    p.add_argument("--batch_size", type=int, default=128)
    p.add_argument("--num_workers", type=int, default=4)
    p.add_argument("--max_records", type=int, default=None)
    p.add_argument("--global_caption", default=None, help="Override caption mode (e.g., global_en)")
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = load_checkpoint(args.ckpt, map_location=device)
    train_args = ckpt.get("args", {})

    global_caption = args.global_caption or train_args.get("global_caption", "global_en")
    local_caption = train_args.get("local_caption", "local_en")
    non_numeric_local = bool(train_args.get("non_numeric_local", 0))

    ds = TSCapJSONLDataset(
        args.jsonl,
        max_records=args.max_records,
        seed=0,
        global_caption=global_caption,
        local_caption=local_caption,
        non_numeric_local=non_numeric_local,
    )
    in_channels = int(ds[0]["x"].shape[0])
    collate = lambda b: hsa_collate_fn(b, patch_size=int(train_args.get("patch_size", 16)), max_local_per_sample=0)
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

    Z_ts, Z_txt = compute_embeddings(model, loader, device)
    if Z_ts is None:
        print("[WARN] Empty embeddings.")
        return

    sim = Z_txt @ Z_ts.t()
    ranks_t2s = ranks_from_sim(sim, dim_candidates=1)
    ranks_s2t = ranks_from_sim(sim, dim_candidates=0)

    m_t2s = summarize_ranks(ranks_t2s)
    m_s2t = summarize_ranks(ranks_s2t)

    print("\n=== Text → TimeSeries ===")
    for k, v in m_t2s.items():
        print(f"{k}: {v:.4f}" if "R@" in k or k == "MRR" else f"{k}: {v:.2f}")

    print("\n=== TimeSeries → Text ===")
    for k, v in m_s2t.items():
        print(f"{k}: {v:.4f}" if "R@" in k or k == "MRR" else f"{k}: {v:.2f}")


if __name__ == "__main__":
    main()
