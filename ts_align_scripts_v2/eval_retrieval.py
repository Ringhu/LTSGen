# ts_align_scripts/eval_retrieval_v2.py
from __future__ import annotations

import argparse
from typing import Dict, List

import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from ts_align.data import TSCapJSONLDataset, hsa_collate_fn
from ts_align.models import HSAClipModel
from ts_align.utils import load_checkpoint, worker_init_fn


def _stable_group_ids_from_keys(keys: List[str]) -> torch.Tensor:
    key2id: Dict[str, int] = {}
    ids: List[int] = []
    for k in keys:
        if k not in key2id:
            key2id[k] = len(key2id)
        ids.append(key2id[k])
    return torch.tensor(ids, dtype=torch.long)


@torch.no_grad()
def compute_embeddings_and_keys(model: HSAClipModel, loader: DataLoader, device: torch.device):
    model.eval()

    Z_ts = []
    keys_ts_all: List[str] = []

    Z_txt = []
    keys_txt_all: List[str] = []

    for batch in tqdm(loader, desc="Embedding"):
        if not batch:
            continue
        x = batch["x"].to(device)
        lengths = batch["lengths"].to(device)

        enc = model.encode_time(x, lengths)
        z_ts = enc["z_global"]  # [B,E]
        Z_ts.append(z_ts.cpu())

        keys_ts = batch.get("group_keys_ts", None)
        if keys_ts is None:
            raise RuntimeError("collate_fn must return group_keys_ts")
        keys_ts = [str(k) for k in keys_ts]
        keys_ts_all.extend(keys_ts)

        texts: List[str] = batch["global_texts"]
        z_txt = model.encode_text(texts)  # [M,E]
        Z_txt.append(z_txt.cpu())

        gbidx = batch["global_batch_idx"].tolist()
        keys_txt = [keys_ts[i] for i in gbidx]
        keys_txt_all.extend(keys_txt)

    if not Z_ts or not Z_txt:
        return None

    Zt = torch.cat(Z_ts, dim=0)   # [N,E]
    Zx = torch.cat(Z_txt, dim=0)  # [M,E]

    # global ids by keys (shared mapping)
    all_keys = keys_ts_all + keys_txt_all
    all_ids = _stable_group_ids_from_keys(all_keys)
    ids_ts = all_ids[: len(keys_ts_all)]
    ids_txt = all_ids[len(keys_ts_all):]

    return Zt, Zx, ids_ts, ids_txt


def ranks_from_sim_multipos(sim: torch.Tensor, ids_q: torch.Tensor, ids_c: torch.Tensor) -> torch.Tensor:
    order = torch.argsort(sim, dim=1, descending=True)
    cand_ids = ids_c[order]
    match = (cand_ids == ids_q[:, None])
    ranks = torch.full((sim.size(0),), fill_value=sim.size(1) + 1, dtype=torch.long)
    has = match.any(dim=1)
    if has.any():
        idx = torch.argmax(match.to(torch.int32), dim=1)
        ranks[has] = idx[has] + 1
    return ranks


def summarize_ranks(ranks: torch.Tensor) -> Dict[str, float]:
    import numpy as np
    r = ranks.detach().cpu().numpy()
    out = {}
    for k in (1, 5, 10):
        out[f"R@{k}"] = float((r <= k).mean())
    out["MedR"] = float(np.median(r))
    out["MeanR"] = float(np.mean(r))
    out["MRR"] = float((1.0 / r.astype(np.float32)).mean())
    return out


def main():
    p = argparse.ArgumentParser("Evaluate retrieval v2 (multi-positive)")
    p.add_argument("--jsonl", required=True)
    p.add_argument("--ckpt", required=True)
    p.add_argument("--batch_size", type=int, default=128)
    p.add_argument("--num_workers", type=int, default=4)
    p.add_argument("--max_records", type=int, default=None)
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
            max_local_per_sample=0,
            max_global_texts_per_sample=int(train_args.get("max_global_texts_per_sample", 1)),
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

    out = compute_embeddings_and_keys(model, loader, device)
    if out is None:
        print("[WARN] Empty embeddings.")
        return
    Zt, Zx, ids_ts, ids_txt = out

    sim_t2s = Zx @ Zt.t()   # [M,N]
    sim_s2t = Zt @ Zx.t()   # [N,M]

    ranks_t2s = ranks_from_sim_multipos(sim_t2s, ids_txt, ids_ts)
    ranks_s2t = ranks_from_sim_multipos(sim_s2t, ids_ts, ids_txt)

    m_t2s = summarize_ranks(ranks_t2s)
    m_s2t = summarize_ranks(ranks_s2t)

    print(f"\n[INFO] N_ts={Zt.size(0)}, N_txt={Zx.size(0)}")
    print("\n=== Text → TimeSeries (multi-positive) ===")
    for k, v in m_t2s.items():
        print(f"{k}: {v:.4f}" if "R@" in k or k == "MRR" else f"{k}: {v:.2f}")

    print("\n=== TimeSeries → Text (multi-positive) ===")
    for k, v in m_s2t.items():
        print(f"{k}: {v:.4f}" if "R@" in k or k == "MRR" else f"{k}: {v:.2f}")


if __name__ == "__main__":
    main()
