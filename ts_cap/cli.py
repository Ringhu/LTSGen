# ts_cap/cli.py
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from itertools import islice

from tqdm import tqdm

from ts_cap.core.samples import generate_sample
from ts_cap.wrappers.registry import get_wrapper
from ts_cap.utils.openai_chat import (
    LLMConfig,
    configure_global_client,
    configure_global_concurrency,
    get_thread_local_client,
)

logger = logging.getLogger("tscap")


# -----------------------------------------------------------------------------
# Logging (tqdm-friendly)
# -----------------------------------------------------------------------------
class _TqdmLoggingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            tqdm.write(msg)
        except Exception:
            pass


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    lvl = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(lvl)

    ch = _TqdmLoggingHandler()
    ch.setLevel(lvl)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S"))
    root.addHandler(ch)

    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(lvl)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        root.addHandler(fh)

    logging.getLogger("openai").setLevel(max(lvl, logging.WARNING))
    logging.getLogger("httpx").setLevel(max(lvl, logging.WARNING))


def load_config_from_file(path: str) -> Dict[str, Any]:
    p = Path(path)
    if p.exists() and p.suffix == ".json":
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# -----------------------------------------------------------------------------
# Worker Function
# -----------------------------------------------------------------------------
def _process_single_sample(args_pack: Tuple) -> Optional[str]:
    idx, sample, config = args_pack
    
    try:
        llm_client = None
        # 如果启用了 LLM，获取 client
        if not config["disable_llm"]:
            llm_client = get_thread_local_client()

        rec = generate_sample(
            timestamps=sample["timestamps"],
            values=sample["values"],
            series_cols=sample["series_cols"],
            target_col=sample["target_col"],
            dataset_name=config["dataset"],
            task=config["task"],
            series_key=sample.get("series_key", "0"),
            indices=sample.get("indices", (0, 0)),
            variables_meta=sample.get("variables_meta"),
            label=sample.get("label"),
            domain_context=sample.get("domain_context"),
            enforce_claims=(not config["no_enforce_claims"]),
            llm_enabled=(not config["disable_llm"]),
            llm_client=llm_client,
        )

        # [新增兜底逻辑]
        # 如果启用了 LLM，但生成的 global description 是空的，说明 LLM 彻底挂了。
        # 此时返回 None，主线程 loop 会自动跳过写入，从而实现“跳过该样本”。
        if not config["disable_llm"]:
            # generate_sample 失败时会返回空字符串 ""
            global_desc = rec.get("descriptions", [""])[0] 
            if not global_desc: 
                logger.error(f"Sample {idx} skipped: LLM generation failed completely.")
                return None

        return json.dumps(rec, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error processing sample index {idx}: {e}", exc_info=True)
        return None

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser("TS-Cap v2 CLI (Auto-Resume)")

    # --- Config File ---
    parser.add_argument("--config_file", help="Path to JSON config file")

    # --- Basic Configs ---
    parser.add_argument("--dataset", help="Dataset name")
    parser.add_argument("--input", help="Path to input data")
    parser.add_argument("--output", help="Path to output .jsonl")
    parser.add_argument("--task", default="forecasting")

    # --- Wrapper Configs ---
    parser.add_argument("--target_col")
    parser.add_argument("--series_cols")
    parser.add_argument("--time_col")
    parser.add_argument("--single_col", help="Shortcut: set series_cols & target_col to this col name.")
    parser.add_argument("--target_series_index", type=int)
    parser.add_argument("--window_mode", default="sliding", choices=["sliding", "full"])
    parser.add_argument("--window_len", type=int, default=512)
    parser.add_argument("--stride", type=int, default=256)
    parser.add_argument("--max_windows", type=int)
    parser.add_argument("--no_enforce_claims", action="store_true")
    
    # --- UCR Specific ---
    parser.add_argument("--ucr_name")
    parser.add_argument("--ucr_split", default="test")
    parser.add_argument("--ucr_label_semantics", default="readme")

    # --- LLM Configs ---
    parser.add_argument("--llm_provider", default="linkapi")
    parser.add_argument("--llm_model", default=None)
    parser.add_argument("--api_key", default=None)
    parser.add_argument("--base_url", default=None)
    parser.add_argument("--llm_timeout", type=int, default=120)
    parser.add_argument("--llm_max_retries", type=int, default=5)
    parser.add_argument("--llm_temperature", type=float, default=0.1)
    parser.add_argument("--disable_llm", action="store_true")

    # --- Performance ---
    parser.add_argument("--num_workers", type=int, default=2, help="Number of threads")
    parser.add_argument("--llm_concurrency", type=int, default=None, help="Global API concurrency limit")

    # --- Resume ---
    parser.add_argument("--resume", action="store_true", help="(Deprecated) Auto-resume is now default.")
    parser.add_argument("--overwrite", action="store_true", help="Force overwrite output file")
    parser.add_argument("--log_level", default="INFO")
    parser.add_argument("--log_file", default=None)

    args = parser.parse_args()
    setup_logging(level=args.log_level, log_file=args.log_file)

    # 1. Load Config
    file_cfg = load_config_from_file(args.config_file) if args.config_file else {}

    def get_val(key: str, default: Any = None) -> Any:
        v = getattr(args, key, None)
        if v is not None: return v
        for section in [None, "dataset", "generation", "llm"]:
            if section:
                if section in file_cfg and key in file_cfg[section]:
                    return file_cfg[section][key]
            elif key in file_cfg:
                return file_cfg[key]
        return default

    dataset = get_val("dataset")
    input_path = get_val("input")
    output_path = get_val("output")
    task = get_val("task", "forecasting")

    if not dataset or not input_path or not output_path:
        logger.error("Missing required arguments: --dataset, --input, or --output")
        sys.exit(1)

    series_cols_str = get_val("series_cols")
    single_col = get_val("single_col")
    target_col = get_val("target_col")
    s_cols_list = [x.strip() for x in series_cols_str.split(",")] if series_cols_str else None
    
    if single_col:
        s_cols_list = [single_col]
        target_col = single_col

    # 2. Setup LLM
    llm_cfg = LLMConfig(
        provider=get_val("llm_provider", "linkapi"),
        model=get_val("llm_model"),
        api_key=get_val("api_key"),
        base_url=get_val("base_url"),
        timeout=int(get_val("llm_timeout", 120)),
        max_retries=int(get_val("llm_max_retries", 5)),
        temperature=float(get_val("llm_temperature", 0.1)),
    )
    configure_global_client(llm_cfg)
    
    llm_conc = args.llm_concurrency if args.llm_concurrency is not None else args.num_workers
    configure_global_concurrency(max(1, int(llm_conc)))

    # 3. Get Wrapper
    wrapper = get_wrapper(
        dataset=dataset,
        input_path=input_path,
        target_col=target_col,
        series_cols=s_cols_list,
        time_col=get_val("time_col"),
        target_series_index=get_val("target_series_index"),
        window_mode=get_val("window_mode", "sliding"),
        window_len=int(get_val("window_len", 512)),
        stride=int(get_val("stride", 256)),
        max_windows=get_val("max_windows"),
        ucr_name=get_val("ucr_name"),
        ucr_split=get_val("ucr_split", "test"),
        ucr_label_semantics=get_val("ucr_label_semantics", "readme"),
        llm_enabled=not args.disable_llm,
        task=task,
    )

    # ==============================================================
    # 4. [修改后] 智能续传逻辑 (Auto-Resume Logic)
    # ==============================================================
    out_p = Path(output_path)
    done_count = 0
    mode = "w"

    # 逻辑：
    # 1. 如果用户显式指定了 --overwrite，则删除旧文件，重头开始。
    # 2. 如果文件存在 (且没说要overwrite)，默认认为是续传 (Auto-Resume)，不管有没有加 --resume 参数。
    # 3. 如果文件不存在，自然是新建。

    if args.overwrite:
        if out_p.exists():
            logger.warning(f"[OVERWRITE] Flag is set. Deleting existing file: {out_p}")
            out_p.unlink()
            mode = "w"
    elif out_p.exists():
        # 文件存在 -> 自动尝试续传
        try:
            # 快速计算行数
            with open(out_p, "rb") as f:
                done_count = sum(1 for _ in f)
            
            if done_count > 0:
                logger.info(f"[AUTO-RESUME] File exists. Resuming from record #{done_count}")
                mode = "a"
            else:
                logger.info("[AUTO-RESUME] File exists but is empty. Starting from scratch.")
                mode = "w"
        except Exception as e:
            logger.error(f"Failed to read existing file for resume: {e}")
            sys.exit(1)
    else:
        # 文件不存在
        logger.info(f"Output file does not exist. Creating new: {out_p}")
        mode = "w"

    # 确保父目录存在
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # 5. Config for workers
    worker_config = {
        "dataset": dataset,
        "task": task,
        "disable_llm": bool(args.disable_llm),
        "no_enforce_claims": bool(args.no_enforce_claims),
    }

    # 6. Iterator Setup (Skip Logic)
    full_iterator = iter(wrapper)
    max_win_arg = get_val("max_windows")
    total_limit = int(max_win_arg) if max_win_arg is not None else None
    
    if total_limit is not None and done_count >= total_limit:
        logger.info(f"Target max_windows={total_limit} reached. Already done {done_count}. Exiting.")
        return

    # islice(迭代器, 跳过的数量, 停止的位置)
    if done_count > 0:
        # 如果 total_limit 是 None，islice 不会停止；如果是数字，它代表停止索引
        # 注意：islice 的 stop 参数是绝对索引，不是相对数量
        stop_idx = total_limit if total_limit is not None else None
        pending_iterator = islice(full_iterator, done_count, stop_idx)
    else:
        stop_idx = total_limit if total_limit is not None else None
        pending_iterator = islice(full_iterator, 0, stop_idx)

    # 组装任务
    work_items = (
        (i, sample, worker_config) 
        for i, sample in enumerate(pending_iterator, start=done_count)
    )

    # 7. Execution
    num_workers = max(1, int(args.num_workers))
    logger.info(f"Start processing. Workers={num_workers}, Skip={done_count}, Mode='{mode}'")

    try:
        # bufsize=1 (line buffered) 可能对 jsonl 不生效，但 encoding 指定 utf-8 很重要
        with open(out_p, mode, encoding="utf-8") as f_out:
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # map 保证顺序
                results = executor.map(_process_single_sample, work_items)
                
                # 进度条
                pbar_total = total_limit if total_limit else None
                # 注意：initial=done_count 让进度条显示我们是从哪里开始的
                pbar = tqdm(results, initial=done_count, total=pbar_total, unit="sample")
                
                for line in pbar:
                    if line:
                        f_out.write(line + "\n")
                        f_out.flush() # 强制落盘，防止断电丢数据

    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Progress saved.")
    
    logger.info(f"Finished. Output saved to: {output_path}")


if __name__ == "__main__":
    main()