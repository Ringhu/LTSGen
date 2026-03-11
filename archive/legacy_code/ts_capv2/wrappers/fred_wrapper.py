# ts_capv2/wrappers/fred_wrapper.py
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterator, List

import numpy as np

from .base import BaseWrapper
from .windowing import iter_windows

logger = logging.getLogger(__name__)

class FREDWrapper(BaseWrapper):
    """
    Wrapper for FRED JSONL.
    Features:
    1. Supports row-level varying columns.
    2. Supports 'target_series_index' to pick specific series (e.g., 0).
    3. If no target specified, iterates ALL series in the row as separate samples.
    """

    def iter_samples(self) -> Iterator[Dict[str, Any]]:
        with open(self.cfg.input_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line: continue
                
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(f"[FRED] JSON decode error line {line_idx}: {e}")
                    continue

                # 1. Parse Basics
                cols_names = row.get("cols", [])
                timestamps = row.get("timestamp", [])
                message = row.get("message", "")
                idx_key = str(row.get("index", line_idx))

                if not cols_names or not timestamps:
                    continue

                # 2. Extract ALL series data into a matrix
                # We load ALL data so correlations can be computed later
                series_data_cols = []
                valid_cols_names = []
                
                # FRED data is usually timeseries1, timeseries2...
                # We strictly follow the length of 'cols_names'
                for i, c_name in enumerate(cols_names):
                    key = f"timeseries{i+1}"
                    vals = row.get(key)
                    if vals is None:
                        # Fallback: maybe keys are just 0, 1, 2? or strict names?
                        # Assume standard structure for now.
                        logger.debug(f"[FRED] Missing {key} for {c_name}, filling zeros.")
                        vals = [0.0] * len(timestamps)
                    
                    # Ensure numeric
                    try:
                        # Handle potential nulls
                        vals = [float(v) if v is not None else 0.0 for v in vals]
                    except ValueError:
                        vals = [0.0] * len(timestamps)
                        
                    series_data_cols.append(vals)
                    valid_cols_names.append(c_name)

                if not series_data_cols:
                    continue

                # Transpose to (T, D)
                try:
                    arr_t_d = np.array(series_data_cols, dtype=float).T
                    values_list = arr_t_d.tolist()
                except Exception as e:
                    logger.warning(f"[FRED] Shape mismatch line {line_idx}: {e}")
                    continue

                # 3. Determine Targets (Which columns to describe?)
                target_indices = []

                # Priority 1: Specified Index via CLI (e.g., --target_series_index 0)
                if self.cfg.target_series_index is not None:
                    idx = self.cfg.target_series_index
                    if 0 <= idx < len(valid_cols_names):
                        target_indices.append(idx)
                    else:
                        logger.debug(f"[FRED] Line {line_idx}: target_index {idx} out of bounds (len={len(valid_cols_names)}). Skipping.")

                # Priority 2: Specified Name via CLI (e.g., --target_col "GDP")
                elif self.cfg.target_col is not None:
                    try:
                        idx = valid_cols_names.index(self.cfg.target_col)
                        target_indices.append(idx)
                    except ValueError:
                        # Specified name not in this row, skip or fallback?
                        # Usually skip is safer for heterogeneous data
                        pass

                # Priority 3: Default -> Iterate ALL columns
                else:
                    target_indices = list(range(len(valid_cols_names)))

                # 4. Generate Samples
                # One row in JSONL might yield N samples if we iterate all columns
                for t_idx in target_indices:
                    target_name = valid_cols_names[t_idx]
                    
                    # Construct Variable Meta (Highlight current target)
                    variables_meta = []
                    for i, name in enumerate(valid_cols_names):
                        variables_meta.append({
                            "name": name,
                            "index": i,
                            "role": "target" if i == t_idx else "feature",
                            "meaning_zh": name, # Or use translation map if available
                            "unit": None
                        })

                    domain_context = {
                        "dataset": "FRED",
                        "original_analysis": message,
                        "description": "Economic data from FRED."
                    }

                    # Windowing
                    iterator = iter_windows(
                        timestamps=timestamps,
                        values=values_list,
                        window_mode=self.cfg.window_mode,
                        window_len=self.cfg.window_len,
                        stride=self.cfg.stride,
                        max_windows=self.cfg.max_windows
                    )

                    for meta, t_win, v_win in iterator:
                        yield {
                            "timestamps": t_win,
                            "values": v_win,
                            "series_cols": valid_cols_names,
                            "target_col": target_name, # Current focus
                            "variables_meta": variables_meta,
                            "domain_context": domain_context,
                            "label": None,
                            # Unique key: RowIndex_TargetIndex_WindowIndex
                            "series_key": f"fred_{idx_key}_var{t_idx}", 
                            "indices": (meta.global_start_idx, meta.global_end_idx),
                        }