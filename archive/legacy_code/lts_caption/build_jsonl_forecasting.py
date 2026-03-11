# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Optional

from forecasting_wrappers import WRAPPER_REGISTRY
from ts_caption_core import core_build_record, LLMFn


def build_jsonl_forecasting(
    dataset: str,
    csv_path: str,
    output_jsonl: str,
    dataset_name: str,
    series_key: str = "series_0",
    target_col: Optional[str] = None,
    series_cols: Optional[list[str]] = None,
    window_len: Optional[int] = 512,
    stride: Optional[int] = 256,
    max_samples: Optional[int] = None,
    use_llm: bool = False,
    llm_fn: Optional[LLMFn] = None,
    enforce_claims: bool = True,
    **wrapper_kwargs,
) -> None:
    dataset = dataset.strip().lower()
    if dataset not in WRAPPER_REGISTRY:
        raise ValueError(f"Unknown dataset='{dataset}'. Choose from {list(WRAPPER_REGISTRY.keys())}")

    it = WRAPPER_REGISTRY[dataset](
        csv_path=csv_path,
        dataset_name=dataset_name,
        series_key=series_key,
        target_col=target_col if target_col is not None else (None if dataset != "ett" else "OT"),
        series_cols=series_cols,
        window_len=window_len,
        stride=stride,
        max_samples=max_samples,
        **wrapper_kwargs,
    )

    n = 0
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for sample in it:
            rec = core_build_record(
                sample=sample,
                enforce_claims=enforce_claims,
                use_llm=use_llm,
                llm_fn=llm_fn,
            )
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1

    print(f"[OK] wrote {n} samples to {output_jsonl}")


# optional dummy LLM hook for smoke test
def dummy_llm_fn(base_caption: str, domain_context_zh: str, record: dict) -> str:
    return f"{domain_context_zh} {base_caption}"
