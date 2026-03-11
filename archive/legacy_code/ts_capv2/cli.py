# cli.py
from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ts_capv2.core.sample import generate_sample
from ts_capv2.wrappers.registry import get_wrapper
from ts_capv2.utils.openai_chat import LLMConfig, configure_global_client

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("tscap.cli")


# -----------------------------------------------------------------------------
# Pydantic Configuration Models
# -----------------------------------------------------------------------------

class DatasetConfig(BaseModel):
    dataset: str
    input: str
    task: str = "forecasting"
    
    # 新增字段
    target_series_index: Optional[int] = None
    
    # Forecasting specific
    time_col: Optional[str] = None
    series_cols: Optional[Union[str, List[str]]] = None
    target_col: Optional[str] = None
    single_col: Optional[str] = None
    
    # Windowing
    window_mode: str = "sliding"
    window_len: int = 512
    stride: int = 256
    max_windows: Optional[int] = None
    
    # UCR specific
    ucr_name: Optional[str] = None
    ucr_split: str = "test"
    ucr_label_semantics: str = "readme"

    def get_series_cols_list(self) -> Optional[List[str]]:
        if self.series_cols is None: return None
        if isinstance(self.series_cols, list): return self.series_cols
        return [x.strip() for x in self.series_cols.split(",") if x.strip()]


class GenerationConfig(BaseModel):
    output: str
    no_enforce_claims: bool = False
    caption_lang: str = "zh"
    caption_style: str = "human"
    
    # LLM Switches
    llm_enabled: bool = False
    llm_caption_enabled: bool = False
    llm_label_enabled: bool = False
    llm_hook: Optional[str] = None


class CLIConfig(BaseModel):
    dataset: DatasetConfig
    generation: GenerationConfig
    llm: LLMConfig


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def import_hook(path: str) -> Callable[[Dict[str, Any]], str]:
    """path format: 'module.sub:func'"""
    if ":" not in path:
        raise ValueError("llm_hook must be like 'myhooks:enhance'")
    mod, fn = path.split(":", 1)
    try:
        m = importlib.import_module(mod)
        f = getattr(m, fn, None)
    except ImportError as e:
        raise ValueError(f"Could not import module '{mod}': {e}")
        
    if not callable(f):
        raise ValueError(f"Function '{fn}' not found or not callable in module '{mod}'")
    return f

def load_config_from_file(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    # Basic JSON loader (can replace with yaml.safe_load if pyyaml is installed)
    if p.suffix in (".json",):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Fallback or error
        raise ValueError("Only .json config files are supported natively. Install PyYAML for yaml support.")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser("tscap: unified wrapper -> core -> jsonl")
    
    # Config file argument
    p.add_argument("--config_file", help="Path to JSON config file to override arguments")

    # --- Flattened Args for CLI convenience ---
    p.add_argument("--dataset", choices=["fred", "ett", "electricity", "traffic", "exchange_rate", "illness", "weather", "ucr2018", "nab"])
    p.add_argument("--input", help="CSV path or Root dir")
    p.add_argument("--output", help="output jsonl path")
    p.add_argument("--task", default="forecasting")

    # Forecasting options
    p.add_argument("--time_col")
    p.add_argument("--series_cols", help="comma separated")
    p.add_argument("--target_col")
    p.add_argument("--single_col", help="Shortcut: set series_cols & target_col to this col name.")
    # 新增参数
    p.add_argument("--target_series_index", type=int, help="Index of series to describe (0-based). Default: all.")

    # Windowing options
    p.add_argument("--window_mode", default="sliding", choices=["sliding", "full"])
    p.add_argument("--window_len", type=int, default=512)
    p.add_argument("--stride", type=int, default=256)
    p.add_argument("--max_windows", type=int)

    p.add_argument("--no_enforce_claims", action="store_true")

    # UCR options
    p.add_argument("--ucr_name")
    p.add_argument("--ucr_split", default="test", choices=["train", "test", "both"])
    p.add_argument("--ucr_label_semantics", default="readme", choices=["readme", "llm", "none"])

    # LLM options
    p.add_argument("--llm_enabled", action="store_true")
    p.add_argument("--llm_caption_enabled", action="store_true")
    p.add_argument("--llm_label_enabled", action="store_true")

    p.add_argument("--llm_hook")
    p.add_argument("--llm_provider", default="openai")
    p.add_argument("--llm_model")
    p.add_argument("--llm_base_url")
    p.add_argument("--llm_api_key") 
    p.add_argument("--llm_timeout", type=int, default=180)
    p.add_argument("--llm_max_retries", type=int, default=10)
    p.add_argument("--llm_temperature", type=float, default=0.0)

    p.add_argument("--caption_lang", default="zh", choices=["zh"])
    p.add_argument("--caption_style", default="human", choices=["human"])

    args = p.parse_args()

    # 1. Build Config Dictionary (File + CLI overrides)
    raw_cfg = {}
    if args.config_file:
        raw_cfg = load_config_from_file(args.config_file)
    
    # Helper to merge CLI arg if present (not None/False)
    def _merge(section, key, val):
        if val is None: return
        # Handle boolean flags that are False by default in argparse
        if isinstance(val, bool) and val is False and section in raw_cfg and key in raw_cfg[section]:
             return 
        if section not in raw_cfg: raw_cfg[section] = {}
        raw_cfg[section][key] = val

    # Map CLI args to Config Structure
    # Dataset
    if args.dataset: _merge("dataset", "dataset", args.dataset)
    if args.input: _merge("dataset", "input", args.input)
    if args.task: _merge("dataset", "task", args.task)
    if args.time_col: _merge("dataset", "time_col", args.time_col)
    if args.series_cols: _merge("dataset", "series_cols", args.series_cols)
    if args.target_col: _merge("dataset", "target_col", args.target_col)
    if args.single_col: _merge("dataset", "single_col", args.single_col)
    if args.window_mode: _merge("dataset", "window_mode", args.window_mode)
    if args.window_len: _merge("dataset", "window_len", args.window_len)
    if args.stride: _merge("dataset", "stride", args.stride)
    if args.max_windows: _merge("dataset", "max_windows", args.max_windows)
    if args.ucr_name: _merge("dataset", "ucr_name", args.ucr_name)
    if args.ucr_split: _merge("dataset", "ucr_split", args.ucr_split)
    if args.ucr_label_semantics: _merge("dataset", "ucr_label_semantics", args.ucr_label_semantics)
    # ... Config Merge Logic ...
    if args.target_series_index is not None: 
        _merge("dataset", "target_series_index", args.target_series_index)
    
    # Generation
    if args.output: _merge("generation", "output", args.output)
    if args.no_enforce_claims: _merge("generation", "no_enforce_claims", args.no_enforce_claims)
    if args.caption_lang: _merge("generation", "caption_lang", args.caption_lang)
    if args.llm_hook: _merge("generation", "llm_hook", args.llm_hook)
    
    # LLM Flags Logic
    # Backward compatibility
    llm_gen = getattr(args, "llm_enabled", False)
    cap_en = getattr(args, "llm_caption_enabled", False)
    lbl_en = getattr(args, "llm_label_enabled", False)
    
    if llm_gen and not cap_en and not lbl_en:
        cap_en = True
        
    if llm_gen: _merge("generation", "llm_enabled", True)
    if cap_en: _merge("generation", "llm_caption_enabled", True)
    if lbl_en: _merge("generation", "llm_label_enabled", True)

    # LLM Config
    if args.llm_provider: _merge("llm", "provider", args.llm_provider)
    if args.llm_model: _merge("llm", "model", args.llm_model)
    if args.llm_base_url: _merge("llm", "base_url", args.llm_base_url)
    if args.llm_api_key: _merge("llm", "api_key", args.llm_api_key)
    if args.llm_timeout: _merge("llm", "timeout", args.llm_timeout)
    if args.llm_temperature: _merge("llm", "temperature", args.llm_temperature)

    # Validate with Pydantic
    try:
        config = CLIConfig(**raw_cfg)
    except Exception as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)

    ds_cfg = config.dataset
    gen_cfg = config.generation
    llm_cfg = config.llm

    # Effective LLM Switches
    eff_llm_caption = gen_cfg.llm_caption_enabled or gen_cfg.llm_enabled
    eff_llm_label = gen_cfg.llm_label_enabled

    # Configure Global LLM
    if eff_llm_caption or eff_llm_label:
        configure_global_client(llm_cfg)

    # Single column shortcut
    eff_series_cols = ds_cfg.get_series_cols_list()
    eff_target_col = ds_cfg.target_col
    
    if ds_cfg.single_col and ds_cfg.single_col.strip():
        single = ds_cfg.single_col.strip()
        logger.info(f"Using --single_col='{single}', overriding series/target cols.")
        eff_series_cols = [single]
        eff_target_col = single

    # 1. Get Unified Wrapper
    wrapper = get_wrapper(
        dataset=ds_cfg.dataset,
        input_path=ds_cfg.input,
        # Flatten dataset config to kwargs
        # 传递新参数
        target_series_index=ds_cfg.target_series_index,
        time_col=ds_cfg.time_col,
        series_cols=eff_series_cols,
        target_col=eff_target_col,
        task=ds_cfg.task,
        window_mode=ds_cfg.window_mode,
        window_len=ds_cfg.window_len,
        stride=ds_cfg.stride,
        max_windows=ds_cfg.max_windows,
        ucr_name=ds_cfg.ucr_name,
        ucr_split=ds_cfg.ucr_split,
        ucr_label_semantics=ds_cfg.ucr_label_semantics,
        llm_enabled=eff_llm_label,
    )

    # 2. Setup Hook
    if eff_llm_caption:
        hook_path = gen_cfg.llm_hook or "ts_capv2.utils.openai_chat:enhance_caption_hook"
        llm_hook_fn = import_hook(hook_path)
    else:
        llm_hook_fn = None

    records: List[Dict[str, Any]] = []

    # 3. Unified Loop
    logger.info(f"Start processing dataset: {ds_cfg.dataset}")
    count = 0
    
    try:
        for sample in wrapper:
            rec = generate_sample(
                timestamps=sample["timestamps"],
                values=sample["values"],
                series_cols=sample["series_cols"],
                target_col=sample["target_col"],
                dataset_name=ds_cfg.dataset,
                task=ds_cfg.task,
                series_key=sample.get("series_key", "series_0"),
                indices=sample.get("indices"),
                variables_meta=sample.get("variables_meta"),
                label=sample.get("label"),
                domain_context=sample.get("domain_context", {}),
                enforce_claims=(not gen_cfg.no_enforce_claims),
                caption_lang=gen_cfg.caption_lang,
                caption_style=gen_cfg.caption_style,
                llm_hook=llm_hook_fn,
                llm_enabled=eff_llm_caption,
                seed=None,
            )
            records.append(rec)
            count += 1
            if count % 100 == 0:
                print(f"Processed {count} samples...", end="\r", file=sys.stderr)
                
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user. Saving progress...")

    logger.info(f"Finished. Total samples: {len(records)}")

    # 4. Write Output
    try:
        with open(gen_cfg.output, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        logger.info(f"Saved to {gen_cfg.output}")
    except OSError as e:
        logger.error(f"Failed to write output file: {e}")

if __name__ == "__main__":
    main()