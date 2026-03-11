from __future__ import annotations

import argparse
import os

import numpy as np
import torch
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader

from ts_align.data import TSCapJSONLDataset, hsa_collate_fn
from ts_align.models import HSAClipModel
from ts_align.utils import load_checkpoint, worker_init_fn


@torch.no_grad()
def visualize_one(model: HSAClipModel, batch, device: torch.device, save_path: str):
    model.eval()
    x = batch["x"].to(device)
    lengths = batch["lengths"].to(device)
    texts = batch["global_texts"]

    enc = model.encode_time(x, lengths)
    z_patch = enc["z_patch"]  # [B,N,E]
    patch_mask = enc["patch_mask"]

    z_txt = model.encode_text(texts)  # [B,E]
    scale = model.get_scale()

    idx = 0
    n_valid = int(patch_mask[idx].sum().item())
    patches = z_patch[idx, :n_valid]  # [N,E]
    query = z_txt[idx]                # [E]
    sim = (patches @ query) * scale   # [N]
    sim = sim.detach().cpu().numpy()

    ts_data = x[idx, 0, : int(lengths[idx].item())].detach().cpu().numpy()

    # upsample patch scores to time axis
    patch_size = model.patch_size
    heat = np.repeat(sim, patch_size)[: len(ts_data)]
    if heat.max() > heat.min():
        heat = (heat - heat.min()) / (heat.max() - heat.min())

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(ts_data, alpha=0.9)
    ax.imshow([heat], aspect="auto", extent=[0, len(ts_data), ts_data.min(), ts_data.max()], alpha=0.5, origin="lower")
    ax.set_title(f"Alignment Heatmap\nText: {texts[idx][:120]}{'...' if len(texts[idx])>120 else ''}")
    ax.set_xlabel("Time index")
    ax.set_ylabel("Value")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser("Visualize patch-text alignment heatmap")
    p.add_argument("--jsonl", required=True)
    p.add_argument("--ckpt", required=True)
    p.add_argument("--save_dir", default="vis")
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--num_workers", type=int, default=2)
    p.add_argument("--max_records", type=int, default=256)
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = load_checkpoint(args.ckpt, map_location=device)
    train_args = ckpt.get("args", {})

    ds = TSCapJSONLDataset(
        args.jsonl,
        max_records=args.max_records,
        seed=0,
        global_caption=train_args.get("global_caption", "global_en"),
        local_caption=train_args.get("local_caption", "local_en"),
        non_numeric_local=bool(train_args.get("non_numeric_local", 0)),
    )
    in_channels = int(ds[0]["x"].shape[0])
    patch_size = int(train_args.get("patch_size", 16))
    collate = lambda b: hsa_collate_fn(b, patch_size=patch_size, max_local_per_sample=0)
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

    # visualize first few batches
    os.makedirs(args.save_dir, exist_ok=True)
    for bi, batch in enumerate(loader):
        if not batch:
            continue
        save_path = os.path.join(args.save_dir, f"heatmap_batch{bi}.png")
        visualize_one(model, batch, device, save_path=save_path)
        print(f"[INFO] saved {save_path}")
        if bi >= 4:
            break


if __name__ == "__main__":
    main()
