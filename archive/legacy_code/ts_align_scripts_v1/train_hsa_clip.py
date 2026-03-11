#ts_align_scripts/train_hsa_clip.py
from __future__ import annotations

import argparse
import os
from typing import Dict, Optional

import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from ts_align.data import TSCapJSONLDataset, hsa_collate_fn
from ts_align.losses import clip_infonce, local_clip_infonce, span_localization_loss
from ts_align.metrics import ranks_from_sim, summarize_ranks
from ts_align.models import HSAClipModel
from ts_align.utils import load_checkpoint, save_checkpoint, set_global_seed, worker_init_fn


def get_cosine_schedule_with_warmup(optimizer, num_warmup_steps: int, num_training_steps: int, min_lr_ratio: float = 0.01):
    def lr_lambda(step: int):
        if step < num_warmup_steps:
            return float(step) / float(max(1, num_warmup_steps))
        progress = float(step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
        # cosine decay
        return max(min_lr_ratio, 0.5 * (1.0 + torch.cos(torch.tensor(progress * 3.1415926535))).item())
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


@torch.no_grad()
def evaluate_retrieval(model: HSAClipModel, loader: DataLoader, device: torch.device) -> Dict[str, float]:
    model.eval()
    zs_ts = []
    zs_txt = []
    for batch in loader:
        if not batch:
            continue
        x = batch["x"].to(device)
        lengths = batch["lengths"].to(device)
        global_texts = batch["global_texts"]
        enc = model.encode_time(x, lengths)
        z_ts = enc["z_global"]
        z_txt = model.encode_text(global_texts)
        zs_ts.append(z_ts.cpu())
        zs_txt.append(z_txt.cpu())
    if not zs_ts:
        return {"R@1": 0.0, "R@5": 0.0, "R@10": 0.0, "MedR": 0.0, "MeanR": 0.0, "MRR": 0.0}
    Zt = torch.cat(zs_ts, dim=0)
    Zx = torch.cat(zs_txt, dim=0)
    sim = Zx @ Zt.t()  # text->ts
    ranks_t2s = ranks_from_sim(sim, dim_candidates=1)
    ranks_s2t = ranks_from_sim(sim, dim_candidates=0)
    out = {}
    for k, v in summarize_ranks(ranks_t2s).items():
        out[f"T2S_{k}"] = v
    for k, v in summarize_ranks(ranks_s2t).items():
        out[f"S2T_{k}"] = v
    return out


def main():
    p = argparse.ArgumentParser("Train HSA-CLIP (time series ↔ text)")
    # data
    p.add_argument("--train_jsonl", required=True)
    p.add_argument("--val_jsonl", default=None)
    p.add_argument("--global_caption", default="global_en", help="global_en/global_zh/domain_en/domain_zh/desc0/desc1/caption_base")
    p.add_argument("--local_caption", default="local_en", help="local_en/local_zh")
    p.add_argument("--non_numeric_local", type=int, default=0, help="1 to strip numbers from local captions")
    p.add_argument("--local_types", default="", help="comma separated types to keep (e.g., phase,ramp,peak,valley). Empty=all")
    p.add_argument("--max_train_records", type=int, default=None)
    p.add_argument("--max_val_records", type=int, default=2048)
    p.add_argument("--num_workers", type=int, default=4)

    # model
    p.add_argument("--patch_size", type=int, default=16)
    p.add_argument("--d_model", type=int, default=256)
    p.add_argument("--time_layers", type=int, default=6)
    p.add_argument("--time_heads", type=int, default=8)
    p.add_argument("--d_embed", type=int, default=256)
    p.add_argument("--text_model", default="sentence-transformers/all-MiniLM-L6-v2")
    p.add_argument("--freeze_text", type=int, default=1, help="1 freeze text backbone, 0 fine-tune")
    p.add_argument("--dropout", type=float, default=0.1)

    # training
    p.add_argument("--out_dir", default="runs/hsa_clip")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch_size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--weight_decay", type=float, default=1e-4)
    p.add_argument("--warmup_ratio", type=float, default=0.1)
    p.add_argument("--min_lr_ratio", type=float, default=0.01)
    p.add_argument("--grad_clip", type=float, default=1.0)
    p.add_argument("--max_local_per_sample", type=int, default=4)
    p.add_argument("--lambda_local", type=float, default=0.5)
    p.add_argument("--lambda_loc", type=float, default=0.5)
    p.add_argument("--amp", type=int, default=1)
    p.add_argument("--seed", type=int, default=0)

    args = p.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    set_global_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] device={device}")

    local_types = [t.strip() for t in args.local_types.split(",") if t.strip()] if args.local_types else None

    train_ds = TSCapJSONLDataset(
        args.train_jsonl,
        max_records=args.max_train_records,
        seed=args.seed,
        global_caption=args.global_caption,
        local_caption=args.local_caption,
        non_numeric_local=bool(args.non_numeric_local),
        local_types=local_types,
    )
    in_channels = int(train_ds[0]["x"].shape[0])

    collate = lambda b: hsa_collate_fn(b, patch_size=args.patch_size, max_local_per_sample=args.max_local_per_sample)

    g = torch.Generator()
    g.manual_seed(args.seed)

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=collate,
        drop_last=True,
        worker_init_fn=worker_init_fn,
        generator=g,
        persistent_workers=(args.num_workers > 0),
    )

    val_loader = None
    if args.val_jsonl:
        val_ds = TSCapJSONLDataset(
            args.val_jsonl,
            max_records=args.max_val_records,
            seed=args.seed + 123,
            global_caption=args.global_caption,
            local_caption=args.local_caption,
            non_numeric_local=bool(args.non_numeric_local),
            local_types=local_types,
        )
        val_loader = DataLoader(
            val_ds,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            collate_fn=collate,
            drop_last=False,
            worker_init_fn=worker_init_fn,
            generator=g,
            persistent_workers=(args.num_workers > 0),
        )

    model = HSAClipModel(
        in_channels=in_channels,
        patch_size=args.patch_size,
        d_model=args.d_model,
        n_time_layers=args.time_layers,
        n_time_heads=args.time_heads,
        text_model=args.text_model,
        d_embed=args.d_embed,
        dropout=args.dropout,
        fine_tune_text=(args.freeze_text == 0),
    ).to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    total_steps = len(train_loader) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    sched = get_cosine_schedule_with_warmup(opt, warmup_steps, total_steps, min_lr_ratio=args.min_lr_ratio)

    scaler = torch.amp.GradScaler('cuda', enabled=(args.amp == 1 and device.type == "cuda"))
    
    best_val = -1.0
    global_step = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs}")
        for batch in pbar:
            if not batch:
                continue
            x = batch["x"].to(device)
            lengths = batch["lengths"].to(device)
            global_texts = batch["global_texts"]
            local_texts = batch["local_texts"]

            with torch.amp.autocast('cuda', enabled=(scaler.is_enabled())):
                enc = model.encode_time(x, lengths)
                z_ts_g = enc["z_global"]
                z_txt_g = model.encode_text(global_texts)
                scale = model.get_scale()
                loss_g = clip_infonce(z_ts_g, z_txt_g, logit_scale=scale)

                loss_l = torch.zeros((), device=device)
                loss_loc = torch.zeros((), device=device)

                if len(local_texts) > 0:
                    z_q = model.encode_text(local_texts)  # [M,E]
                    bidx = batch["local_batch_idx"].to(device)
                    ps = batch["local_ps"].to(device)
                    pe = batch["local_pe"].to(device)
                    z_patch = enc["z_patch"]              # [B,N,E]
                    patch_mask = enc["patch_mask"]        # [B,N]

                    # Local TS embeddings by mean-pooling patch embeddings in GT span.
                    # Vectorized by per-query gather via prefix sums per batch item.
                    # (Simple loop is okay because M is small; this keeps code clear.)
                    z_ts_local = []
                    keep = []
                    for i in range(z_q.size(0)):
                        b = int(bidx[i].item())
                        s = int(ps[i].item())
                        e = int(pe[i].item())
                        if e <= s:
                            e = s + 1
                        # guard against out-of-range due to bad data
                        n_valid = int(patch_mask[b].sum().item())
                        s = max(0, min(s, n_valid - 1))
                        e = max(s + 1, min(e, n_valid))
                        seg = z_patch[b, s:e]  # [L,E]
                        if seg.numel() == 0:
                            continue
                        z_ts_local.append(seg.mean(dim=0))
                        keep.append(i)

                    if z_ts_local:
                        z_ts_local = torch.stack(z_ts_local, dim=0)
                        z_q2 = z_q[torch.tensor(keep, device=device, dtype=torch.long)]
                        bidx2 = bidx[torch.tensor(keep, device=device, dtype=torch.long)]
                        ps2 = ps[torch.tensor(keep, device=device, dtype=torch.long)]
                        pe2 = pe[torch.tensor(keep, device=device, dtype=torch.long)]

                        loss_l = local_clip_infonce(z_ts_local, z_q2, logit_scale=scale)
                        loss_loc = span_localization_loss(
                            z_patch=z_patch,
                            patch_mask=patch_mask,
                            z_query=z_q2,
                            local_batch_idx=bidx2,
                            local_ps=ps2,
                            local_pe=pe2,
                            logit_scale=scale,
                        )

                loss = loss_g + args.lambda_local * loss_l + args.lambda_loc * loss_loc

            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            if args.grad_clip > 0:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=float(args.grad_clip))
            scaler.step(opt)
            scaler.update()
            sched.step()

            global_step += 1
            pbar.set_postfix({
                "loss": f"{loss.item():.3f}",
                "g": f"{loss_g.item():.3f}",
                "l": f"{loss_l.item():.3f}",
                "loc": f"{loss_loc.item():.3f}",
                "lr": f"{sched.get_last_lr()[0]:.2e}",
                "scale": f"{scale.item():.2f}",
            })

        # --- Eval + Save ---
        metrics = {}
        if val_loader is not None:
            metrics = evaluate_retrieval(model, val_loader, device)
            r1 = metrics.get("T2S_R@1", 0.0)
            print(f"[VAL] " + ", ".join([f"{k}={v:.4f}" for k, v in metrics.items() if k.endswith(("R@1","R@5","R@10","MedR","MRR"))]))
            # Save best by T2S_R@1
            if r1 > best_val:
                best_val = r1
                save_checkpoint(
                    os.path.join(args.out_dir, "best.pt"),
                    model=model,
                    args=vars(args),
                    optimizer=opt,
                    scheduler=sched,
                    scaler=scaler,
                    step=global_step,
                    metrics=metrics,
                )
                print(f"[INFO] saved best.pt (T2S_R@1={best_val:.4f})")

        save_checkpoint(
            os.path.join(args.out_dir, "latest.pt"),
            model=model,
            args=vars(args),
            optimizer=opt,
            scheduler=sched,
            scaler=scaler,
            step=global_step,
            metrics=metrics if metrics else None,
        )
        print(f"[INFO] saved latest.pt")

    print("[DONE]")


if __name__ == "__main__":
    main()
