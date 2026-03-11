# ts_align_scripts/train_hsa_clip_v2.py
from __future__ import annotations

import argparse
import os
from typing import Dict, List, Optional, Sequence, Tuple
from functools import partial
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from ts_align.data import TSCapJSONLDataset, hsa_collate_fn
from ts_align.losses import clip_infonce_multipos, local_clip_infonce, span_localization_loss
from ts_align.models import HSAClipModel
from ts_align.utils import save_checkpoint, set_global_seed, worker_init_fn



def get_cosine_schedule_with_warmup(
    optimizer,
    num_warmup_steps: int,
    num_training_steps: int,
    min_lr_ratio: float = 0.01,
):
    import math

    def lr_lambda(step: int):
        if step < num_warmup_steps:
            return float(step) / float(max(1, num_warmup_steps))
        progress = float(step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
        return max(min_lr_ratio, 0.5 * (1.0 + math.cos(progress * math.pi)))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def _parse_csv(s: str) -> List[str]:
    return [x.strip() for x in str(s).split(",") if x.strip()]


def _stable_group_ids_from_keys(keys: List[str]) -> torch.Tensor:
    """
    Map string keys -> int ids (global, stable within this eval call).
    """
    key2id: Dict[str, int] = {}
    ids: List[int] = []
    for k in keys:
        if k not in key2id:
            key2id[k] = len(key2id)
        ids.append(key2id[k])
    return torch.tensor(ids, dtype=torch.long)


@torch.no_grad()
def evaluate_retrieval_multipos(model: HSAClipModel, loader: DataLoader, device: torch.device) -> Dict[str, float]:
    """
    Multi-positive retrieval evaluation on the whole loader.
    Works for both single-caption (M==N) and multi-caption (M>=N).
    """
    model.eval()

    Z_ts: List[torch.Tensor] = []
    keys_ts_all: List[str] = []

    Z_txt: List[torch.Tensor] = []
    keys_txt_all: List[str] = []

    for batch in loader:
        if not batch:
            continue
        x = batch["x"].to(device)
        lengths = batch["lengths"].to(device)

        enc = model.encode_time(x, lengths)
        z_ts = enc["z_global"]  # [B,E]
        Z_ts.append(z_ts.cpu())

        # stable group keys per time sample in this batch
        keys_ts = batch.get("group_keys_ts", None)
        if keys_ts is None:
            raise RuntimeError("collate_fn must return 'group_keys_ts' for multi-positive eval.")
        keys_ts_all.extend([str(k) for k in keys_ts])

        # text side
        texts: List[str] = batch["global_texts"]  # flattened captions, len M_batch
        z_txt = model.encode_text(texts)          # [M_batch,E]
        Z_txt.append(z_txt.cpu())

        # build keys for each caption by indexing group_keys_ts with global_batch_idx
        gbidx = batch["global_batch_idx"].tolist()  # caption -> which ts index in this batch
        keys_txt = [str(keys_ts[i]) for i in gbidx]
        keys_txt_all.extend(keys_txt)

    if not Z_ts or not Z_txt:
        return {
            "T2S_R@1": 0.0, "T2S_R@5": 0.0, "T2S_R@10": 0.0, "T2S_MedR": 0.0, "T2S_MRR": 0.0,
            "S2T_R@1": 0.0, "S2T_R@5": 0.0, "S2T_R@10": 0.0, "S2T_MedR": 0.0, "S2T_MRR": 0.0,
        }

    Zt = torch.cat(Z_ts, dim=0)   # [N,E]
    Zx = torch.cat(Z_txt, dim=0)  # [M,E]

    # global ids based on keys
    # use one shared mapping so equality works across ts/txt
    all_keys = keys_ts_all + keys_txt_all
    all_ids = _stable_group_ids_from_keys(all_keys)
    ids_ts = all_ids[: len(keys_ts_all)]
    ids_txt = all_ids[len(keys_ts_all):]

    # similarity
    sim_t2s = (Zx @ Zt.t())  # [M,N]
    sim_s2t = (Zt @ Zx.t())  # [N,M]

    # ranks: first positive rank
    def ranks_from_sim_multipos(sim: torch.Tensor, ids_q: torch.Tensor, ids_c: torch.Tensor) -> torch.Tensor:
        order = torch.argsort(sim, dim=1, descending=True)
        cand_ids = ids_c[order]  # [Q,C]
        match = (cand_ids == ids_q[:, None])
        ranks = torch.full((sim.size(0),), fill_value=sim.size(1) + 1, dtype=torch.long)
        has = match.any(dim=1)
        if has.any():
            idx = torch.argmax(match.to(torch.int32), dim=1)
            ranks[has] = idx[has] + 1
        return ranks

    def summarize(r: torch.Tensor) -> Dict[str, float]:
        import numpy as np
        rr = r.detach().cpu().numpy()
        out = {}
        for k in (1, 5, 10):
            out[f"R@{k}"] = float((rr <= k).mean())
        out["MedR"] = float(np.median(rr))
        out["MRR"] = float((1.0 / rr.astype(np.float32)).mean())
        return out

    r_t2s = ranks_from_sim_multipos(sim_t2s, ids_txt, ids_ts)
    r_s2t = ranks_from_sim_multipos(sim_s2t, ids_ts, ids_txt)

    mt = summarize(r_t2s)
    ms = summarize(r_s2t)

    out = {
        "T2S_R@1": mt["R@1"], "T2S_R@5": mt["R@5"], "T2S_R@10": mt["R@10"], "T2S_MedR": mt["MedR"], "T2S_MRR": mt["MRR"],
        "S2T_R@1": ms["R@1"], "S2T_R@5": ms["R@5"], "S2T_R@10": ms["R@10"], "S2T_MedR": ms["MedR"], "S2T_MRR": ms["MRR"],
        "N_ts": float(Zt.size(0)),
        "N_txt": float(Zx.size(0)),
    }
    return out

def collate_hsa_train(
    batch,
    *,
    patch_size: int,
    max_local_per_sample: int,
    max_global_texts_per_sample: int,
    positive_key: str,
    random_crop: bool,
    crop_prob: float,
    crop_lengths,
    strip_numbers_on_crop: bool,
    seed: int,
):
    return hsa_collate_fn(
        batch,
        patch_size=patch_size,
        max_local_per_sample=max_local_per_sample,
        max_global_texts_per_sample=max_global_texts_per_sample,
        positive_key=positive_key,
        random_crop=random_crop,
        crop_prob=crop_prob,
        crop_lengths=crop_lengths,
        strip_numbers_on_crop=strip_numbers_on_crop,
        seed=seed,
    )


def collate_hsa_val(
    batch,
    *,
    patch_size: int,
    max_global_texts_per_sample: int,
    positive_key: str,
    seed: int,
):
    return hsa_collate_fn(
        batch,
        patch_size=patch_size,
        max_local_per_sample=0,  # val retrieval 不需要 locals
        max_global_texts_per_sample=max_global_texts_per_sample,
        positive_key=positive_key,
        random_crop=False,
        seed=seed,
    )


def main():
    p = argparse.ArgumentParser("Train HSA-CLIP v2 (TS ↔ Text)")

    # data
    p.add_argument("--train_jsonl", required=True)
    p.add_argument("--val_jsonl", default=None)
    p.add_argument("--global_captions", default="global_zh", help="comma list, e.g. global_zh,domain_zh,caption_base")
    p.add_argument("--local_caption", default="local_zh")
    p.add_argument("--non_numeric_local", type=int, default=0)
    p.add_argument("--local_types", default="", help="comma list types to keep; empty=all")
    p.add_argument("--max_train_records", type=int, default=None)
    p.add_argument("--max_val_records", type=int, default=2048)
    p.add_argument("--num_workers", type=int, default=4)

    # collate / multi-positive
    p.add_argument("--max_global_texts_per_sample", type=int, default=1, help="1=standard CLIP; >1 enables real multi-positive")
    p.add_argument("--positive_key", default="instance", choices=["instance", "label"], help="instance recommended")
    p.add_argument("--max_local_per_sample", type=int, default=4)

    # random crop aug
    p.add_argument("--random_crop", type=int, default=0)
    p.add_argument("--crop_prob", type=float, default=1.0)
    p.add_argument("--crop_lengths", default="", help="comma list lengths, e.g. 96,128,192,256,384,512")
    p.add_argument("--strip_numbers_on_crop", type=int, default=0)

    # model: common
    p.add_argument("--patch_size", type=int, default=16)
    p.add_argument("--d_model", type=int, default=256)
    p.add_argument("--time_layers", type=int, default=6)
    p.add_argument("--time_heads", type=int, default=8)
    p.add_argument("--d_embed", type=int, default=256)
    p.add_argument("--text_model", default="sentence-transformers/all-MiniLM-L6-v2")
    p.add_argument("--freeze_text", type=int, default=1)
    p.add_argument("--dropout", type=float, default=0.1)

    # model: backbone switch (路线A)
    p.add_argument("--time_backbone", default="patch", choices=["patch", "chronos2", "hybrid"])
    p.add_argument("--chronos2_model", default="autogluon/chronos-2")
    p.add_argument("--chronos2_device_map", default="cuda")
    p.add_argument("--chronos2_dtype", default="bfloat16", help="bfloat16/float16/float32")
    p.add_argument("--fine_tune_chronos2", type=int, default=0)
    p.add_argument("--chronos2_channel_pool", default="first", choices=["first", "mean"])

    # hierarchical pooling
    p.add_argument("--hier_pool", type=int, default=0)
    p.add_argument("--hier_stride", type=int, default=4)
    p.add_argument("--hier_pool_for_global", type=int, default=1)

    # training
    p.add_argument("--out_dir", default="runs/hsa_clip_v2")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch_size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--weight_decay", type=float, default=1e-4)
    p.add_argument("--warmup_ratio", type=float, default=0.1)
    p.add_argument("--min_lr_ratio", type=float, default=0.01)
    p.add_argument("--grad_clip", type=float, default=1.0)
    p.add_argument("--lambda_local", type=float, default=0.5)
    p.add_argument("--lambda_loc", type=float, default=0.5)
    p.add_argument("--amp", type=int, default=1)
    p.add_argument("--seed", type=int, default=0)

    args = p.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    set_global_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] device={device}")

    global_captions = _parse_csv(args.global_captions)
    if not global_captions:
        global_captions = ["global_zh"]

    crop_lengths = [int(x) for x in _parse_csv(args.crop_lengths)] if args.crop_lengths else None
    local_types = _parse_csv(args.local_types) if args.local_types else None

    # --- Datasets ---
    train_ds = TSCapJSONLDataset(
        args.train_jsonl,
        max_records=args.max_train_records,
        seed=args.seed,
        global_caption=global_captions,       # list => multi-caption candidates
        local_caption=args.local_caption,
        non_numeric_local=bool(args.non_numeric_local),
        local_types=local_types,
    )
    in_channels = int(train_ds[0]["x"].shape[0])

    # Collate: train can use random crop; val should not (default).
    collate_train = partial(
        collate_hsa_train,
        patch_size=args.patch_size,
        max_local_per_sample=args.max_local_per_sample,
        max_global_texts_per_sample=args.max_global_texts_per_sample,
        positive_key=args.positive_key,
        random_crop=bool(args.random_crop),
        crop_prob=float(args.crop_prob),
        crop_lengths=crop_lengths,
        strip_numbers_on_crop=bool(args.strip_numbers_on_crop),
        seed=args.seed,
    )

    collate_val = partial(
        collate_hsa_val,
        patch_size=args.patch_size,
        max_global_texts_per_sample=args.max_global_texts_per_sample,
        positive_key=args.positive_key,
        seed=args.seed + 123,
    )


    g = torch.Generator()
    g.manual_seed(args.seed)

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=collate_train,
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
            seed=args.seed + 999,
            global_caption=global_captions,
            local_caption=args.local_caption,
            non_numeric_local=bool(args.non_numeric_local),
            local_types=local_types,
        )
        val_loader = DataLoader(
            val_ds,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            collate_fn=collate_val,
            drop_last=False,
            worker_init_fn=worker_init_fn,
            generator=g,
            persistent_workers=(args.num_workers > 0),
        )

    # --- Model ---
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

        time_backbone=args.time_backbone,
        chronos2_model=args.chronos2_model,
        chronos2_device_map=args.chronos2_device_map,
        chronos2_dtype=args.chronos2_dtype,
        fine_tune_chronos2=bool(args.fine_tune_chronos2),
        chronos2_channel_pool=args.chronos2_channel_pool,

        hier_pool=bool(args.hier_pool),
        hier_stride=int(args.hier_stride),
        hier_pool_for_global=bool(args.hier_pool_for_global),
    ).to(device)

    # Only optimize trainable params (important when Chronos2 is large & frozen)
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    print(f"[INFO] trainable params: {sum(p.numel() for p in trainable_params)/1e6:.2f}M")

    opt = torch.optim.AdamW(trainable_params, lr=args.lr, weight_decay=args.weight_decay)
    total_steps = len(train_loader) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    sched = get_cosine_schedule_with_warmup(opt, warmup_steps, total_steps, min_lr_ratio=args.min_lr_ratio)

    scaler = torch.amp.GradScaler("cuda", enabled=(args.amp == 1 and device.type == "cuda"))
    autocast_dev = "cuda" if device.type == "cuda" else "cpu"

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

            # global texts: flattened captions
            global_texts: List[str] = batch["global_texts"]
            group_ids_ts = batch["group_ids_ts"].to(device)   # per-batch ids OK for training
            group_ids_txt = batch["group_ids_txt"].to(device)

            local_texts: List[str] = batch["local_texts"]

            with torch.amp.autocast(autocast_dev, enabled=scaler.is_enabled()):
                enc = model.encode_time(x, lengths)
                z_ts_g = enc["z_global"]                 # [B,E]
                z_txt_g = model.encode_text(global_texts)  # [M,E]
                scale = model.get_scale()

                # --- Global multi-positive CLIP loss ---
                loss_g = clip_infonce_multipos(
                    z_ts=z_ts_g,
                    z_txt=z_txt_g,
                    logit_scale=scale,
                    group_ids_ts=group_ids_ts,
                    group_ids_txt=group_ids_txt,
                )

                # --- Local losses only if patch tokens exist ---
                loss_l = torch.zeros((), device=device)
                loss_loc = torch.zeros((), device=device)

                if ("z_patch" in enc) and ("patch_mask" in enc) and (len(local_texts) > 0):
                    z_patch = enc["z_patch"]            # [B,N,E]
                    patch_mask = enc["patch_mask"]      # [B,N]
                    z_q = model.encode_text(local_texts)  # [Mloc,E]

                    bidx = batch["local_batch_idx"].to(device)
                    ps = batch["local_ps"].to(device)
                    pe = batch["local_pe"].to(device)

                    # pooled local TS embeddings in GT span
                    z_ts_local = model.pool_local_spans(z_patch, patch_mask, bidx, ps, pe)
                    if z_ts_local.numel() > 0:
                        z_ts_local = torch.nn.functional.normalize(z_ts_local, dim=-1)
                        loss_l = local_clip_infonce(z_ts_local, z_q, logit_scale=scale)
                        loss_loc = span_localization_loss(
                            z_patch=z_patch,
                            patch_mask=patch_mask,
                            z_query=z_q,
                            local_batch_idx=bidx,
                            local_ps=ps,
                            local_pe=pe,
                            logit_scale=scale,
                        )

                loss = loss_g + args.lambda_local * loss_l + args.lambda_loc * loss_loc

            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            if args.grad_clip > 0:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=float(args.grad_clip))
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
                "Mtxt": len(global_texts),
            })

        # --- Eval + Save ---
        metrics = {}
        if val_loader is not None:
            metrics = evaluate_retrieval_multipos(model, val_loader, device)
            r1 = float(metrics.get("T2S_R@1", 0.0))
            print(
                "[VAL] "
                + ", ".join(
                    [f"{k}={v:.4f}" for k, v in metrics.items() if k in ("T2S_R@1", "T2S_R@5", "T2S_R@10", "T2S_MRR", "S2T_R@1", "S2T_MRR")]
                )
                + f" (N_ts={int(metrics.get('N_ts', 0))}, N_txt={int(metrics.get('N_txt', 0))})"
            )

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
        print("[INFO] saved latest.pt")

    print("[DONE]")


if __name__ == "__main__":
    import torch.multiprocessing as mp
    mp.set_start_method("spawn", force=True)
    main()
