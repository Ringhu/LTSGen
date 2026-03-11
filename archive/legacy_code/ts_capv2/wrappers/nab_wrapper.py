# ts_capv2/wrappers/nab_wrapper.py
from __future__ import annotations

import csv
import json
import os
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .base import BaseWrapper, WrapperConfig
from .windowing import iter_windows

logger = logging.getLogger(__name__)

# --- Legacy Helper Functions ---

def _parse_dt(s: str) -> datetime:
    s = str(s).strip()
    if s.endswith("Z"):
        s = s[:-1]
    return datetime.fromisoformat(s)

def _list_csv_files(data_dir: str) -> List[str]:
    out: List[str] = []
    for root, _, files in os.walk(data_dir):
        for fn in files:
            if fn.lower().endswith(".csv"):
                out.append(os.path.join(root, fn))
    out.sort()
    return out

def _norm_rel_key(path: str) -> str:
    return path.replace("\\", "/")

@dataclass
class _Series:
    series_id: str
    timestamps_str: List[str]
    timestamps_dt: List[datetime]
    values: List[List[float]] # Improved typing
    point_labels: Optional[List[int]]


class _LegacyNABIterWrapper:
    def __init__(
        self,
        *,
        nab_root: str,
        time_col: Optional[str],
        series_cols: Optional[List[str]],
        target_col: Optional[str],
        task: str,
        **_: Any,
    ):
        self.nab_root = nab_root
        self.data_dir = os.path.join(nab_root, "data")
        if not os.path.isdir(self.data_dir):
            self.data_dir = nab_root

        self.labels_dir = os.path.join(nab_root, "labels")
        self.windows_json = os.path.join(self.labels_dir, "combined_windows.json")
        self.points_json = os.path.join(self.labels_dir, "combined_labels.json")

        self.time_col = (time_col or "timestamp")
        self.value_col = (target_col or "value")
        self.series_cols = series_cols or [self.value_col]
        self.target_col = self.value_col
        self.task = task

        self._windows_map: Dict[str, List[Tuple[datetime, datetime]]] = {}
        self._points_map: Dict[str, List[datetime]] = {}
        self._load_labels()

    def _load_labels(self) -> None:
        if os.path.isfile(self.windows_json):
            try:
                with open(self.windows_json, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for k, win_list in raw.items():
                    key = _norm_rel_key(str(k))
                    intervals: List[Tuple[datetime, datetime]] = []
                    for item in win_list:
                        if not item or len(item) != 2:
                            continue
                        try:
                            intervals.append((_parse_dt(item[0]), _parse_dt(item[1])))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"[NAB] Invalid window timestamp in JSON for {key}: {e}")
                            continue
                    intervals.sort(key=lambda x: x[0])
                    self._windows_map[key] = intervals
                return
            except json.JSONDecodeError:
                logger.error(f"[NAB] Failed to decode JSON: {self.windows_json}")

        if os.path.isfile(self.points_json):
            try:
                with open(self.points_json, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for k, ts_list in raw.items():
                    key = _norm_rel_key(str(k))
                    pts: List[datetime] = []
                    for t in ts_list:
                        try:
                            pts.append(_parse_dt(t))
                        except (ValueError, TypeError):
                            continue
                    pts.sort()
                    self._points_map[key] = pts
            except json.JSONDecodeError:
                logger.error(f"[NAB] Failed to decode JSON: {self.points_json}")

    def domain_context(self) -> str:
        return "Numenta Anomaly Benchmark (NAB) anomaly detection."

    def _load_one_series(self, csv_path: str) -> _Series:
        rel = os.path.relpath(csv_path, self.data_dir)
        series_id = _norm_rel_key(rel)

        ts_str: List[str] = []
        ts_dt: List[datetime] = []
        vals: List[List[float]] = []

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    logger.warning(f"[NAB] Skipping empty/headerless CSV: {csv_path}")
                    return _Series(series_id, [], [], [], None)

                for line_num, row in enumerate(reader, 1):
                    t = row.get(self.time_col)
                    v = row.get(self.value_col)
                    
                    # Fallback logic
                    if t is None: t = row.get(reader.fieldnames[0])
                    if v is None and len(reader.fieldnames) > 1: v = row.get(reader.fieldnames[1])
                    
                    if not t or not v:
                        continue
                        
                    t, v = str(t).strip(), str(v).strip()
                    if not t or not v:
                        continue

                    # *** Explicit Error Handling ***
                    try:
                        dt = _parse_dt(t)
                        fv = float(v)
                    except (ValueError, TypeError) as e:
                        # Log but continue, don't crash the whole dataset
                        if line_num < 5: # Only log first few errors to avoid spam
                             logger.debug(f"[NAB] Parse error in {series_id} line {line_num}: {e}")
                        continue

                    ts_str.append(t)
                    ts_dt.append(dt)
                    vals.append([fv])
                    
        except OSError as e:
            logger.error(f"[NAB] IO Error reading {csv_path}: {e}")
            return _Series(series_id, [], [], [], None)

        # Build labels
        pl: Optional[List[int]] = None
        if series_id in self._windows_map and ts_dt:
            intervals = self._windows_map[series_id]
            pl = [0] * len(ts_dt)
            j = 0
            for i, cur in enumerate(ts_dt):
                while j < len(intervals) and cur > intervals[j][1]:
                    j += 1
                if j < len(intervals) and intervals[j][0] <= cur <= intervals[j][1]:
                    pl[i] = 1
        elif series_id in self._points_map and ts_dt:
            pts = set(self._points_map[series_id])
            pl = [1 if t in pts else 0 for t in ts_dt]

        return _Series(series_id=series_id, timestamps_str=ts_str, timestamps_dt=ts_dt, values=vals, point_labels=pl)

    def iter_samples(
        self,
        *,
        window_mode: str = "sliding",
        window_len: int = 512,
        stride: int = 256,
        max_windows: Optional[int] = None,
        **__: Any,
    ) -> Iterator[Dict[str, Any]]:
        produced = 0
        for csv_path in _list_csv_files(self.data_dir):
            s = self._load_one_series(csv_path)
            
            # Skip empty series
            if not s.timestamps_str:
                continue

            for meta, t_win, v_win in iter_windows(
                timestamps=s.timestamps_str,
                values=s.values,
                window_mode=window_mode,
                window_len=window_len,
                stride=stride,
                max_windows=None,
            ):
                label = None
                if s.point_labels is not None:
                    gs, ge = meta.global_start_idx, meta.global_end_idx
                    label = int(any(s.point_labels[gs:ge]))

                yield {
                    "timestamps": t_win,
                    "values": v_win,
                    "series_cols": self.series_cols,
                    "target_col": self.target_col,
                    "variables_meta": None,
                    "domain_context": self.domain_context(),
                    "label": label,
                    "series_key": s.series_id,
                    "indices": (meta.global_start_idx, meta.global_end_idx),
                }

                produced += 1
                if max_windows is not None and produced >= max_windows:
                    return

class NABWrapper(BaseWrapper):
    def __init__(self, cfg: WrapperConfig):
        super().__init__(cfg)
        self._impl = _LegacyNABIterWrapper(
            nab_root=cfg.input_path,
            time_col=cfg.time_col,
            series_cols=cfg.series_cols,
            target_col=cfg.target_col,
            task=cfg.task
        )

    def iter_samples(self) -> Iterator[Dict[str, Any]]:
        return self._impl.iter_samples(
            window_mode=self.cfg.window_mode,
            window_len=self.cfg.window_len,
            stride=self.cfg.stride,
            max_windows=self.cfg.max_windows
        )