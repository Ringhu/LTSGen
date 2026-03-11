# anomaly_detection_wrapper.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Union

import json
import numpy as np
import pandas as pd


Timestamp = pd.Timestamp
Window = Tuple[Timestamp, Timestamp]


@dataclass
class AnomalySeries:
    """
    Unified in-memory representation for anomaly detection datasets.

    - df: time-indexed DataFrame. index must be datetime-like and sorted ascending.
    - windows: anomaly windows [(start_ts, end_ts), ...] if available
    - point_labels: optional 0/1 array aligned with df.index (len == len(df))
    """
    series_id: str
    df: pd.DataFrame
    windows: List[Window] = field(default_factory=list)
    point_labels: Optional[np.ndarray] = None
    meta: Dict[str, object] = field(default_factory=dict)


class BaseAnomalyAdapter:
    """Minimal interface you can standardize across NAB/Yahoo/SMD/SMAP/SWaT/..."""

    def iter_series(self) -> Iterator[str]:
        raise NotImplementedError

    def load_series(self, series_id: str, with_point_labels: bool = True) -> AnomalySeries:
        raise NotImplementedError

    # --- helpers for your existing pipeline (often needed by your base adapter) ---
    def default_target_col(self) -> str:
        """Name of default target column for single-target logic."""
        raise NotImplementedError

    def default_time_col(self) -> Optional[str]:
        """If underlying file is not indexed by time, this can be used by parsers."""
        return None


class NABAdapter(BaseAnomalyAdapter):
    """
    Wrapper for Numenta Anomaly Benchmark (NAB).

    Expected layout (typical):
      <nab_root>/
        data/<subset>/*.csv
        labels/combined_windows.json

    Each CSV is typically 2 columns: timestamp,value (header may vary).
    Windows JSON maps file path -> [[start,end], ...] timestamps.
    """

    def __init__(
        self,
        nab_root: Union[str, Path],
        windows_json_path: Optional[Union[str, Path]] = None,
        data_dir: Optional[Union[str, Path]] = None,
        value_col: str = "value",
        timestamp_col: str = "timestamp",
    ):
        self.nab_root = Path(nab_root).expanduser().resolve()
        self.data_dir = Path(data_dir).expanduser().resolve() if data_dir else self._infer_data_dir(self.nab_root)

        if windows_json_path is None:
            # common default: <nab_root>/labels/combined_windows.json
            guess = self.nab_root / "labels" / "combined_windows.json"
            if not guess.exists():
                raise FileNotFoundError(
                    f"combined_windows.json not found. "
                    f"Pass windows_json_path explicitly or ensure it exists at: {guess}"
                )
            self.windows_json_path = guess
        else:
            self.windows_json_path = Path(windows_json_path).expanduser().resolve()

        self.value_col = value_col
        self.timestamp_col = timestamp_col

        self._windows_map = self._load_windows_map(self.windows_json_path)

        # Build an index: series_id -> csv_path
        self._series = self._discover_csv_files(self.data_dir)

    def default_target_col(self) -> str:
        return self.value_col

    def iter_series(self) -> Iterator[str]:
        # series_id is a POSIX-like relative path from data_dir, e.g. "realKnownCause/nyc_taxi.csv"
        yield from self._series.keys()

    def load_series(self, series_id: str, with_point_labels: bool = True) -> AnomalySeries:
        if series_id not in self._series:
            raise KeyError(f"Unknown series_id: {series_id}")

        csv_path = self._series[series_id]
        df = self._read_nab_csv(csv_path)

        windows = self._get_windows_for_csv(csv_path)

        point_labels = None
        if with_point_labels:
            point_labels = self._windows_to_point_labels(df.index, windows)

        return AnomalySeries(
            series_id=series_id,
            df=df,
            windows=windows,
            point_labels=point_labels,
            meta={
                "dataset": "NAB",
                "csv_path": str(csv_path),
                "windows_json_path": str(self.windows_json_path),
            },
        )

    # ---------------- internal ----------------

    @staticmethod
    def _infer_data_dir(nab_root: Path) -> Path:
        # allow passing either repo root or directly data directory
        if (nab_root / "data").exists():
            return (nab_root / "data").resolve()
        return nab_root.resolve()

    @staticmethod
    def _discover_csv_files(data_dir: Path) -> Dict[str, Path]:
        if not data_dir.exists():
            raise FileNotFoundError(f"data_dir does not exist: {data_dir}")
        out: Dict[str, Path] = {}
        for p in data_dir.rglob("*.csv"):
            if p.is_file():
                series_id = p.relative_to(data_dir).as_posix()
                out[series_id] = p
        if not out:
            raise FileNotFoundError(f"No .csv files found under: {data_dir}")
        return out

    @staticmethod
    def _load_windows_map(windows_json_path: Path) -> Dict[str, List[List[str]]]:
        with windows_json_path.open("r", encoding="utf-8") as f:
            m = json.load(f)
        if not isinstance(m, dict):
            raise ValueError(f"Invalid windows json: root is not dict: {windows_json_path}")
        return m

    def _read_nab_csv(self, csv_path: Path) -> pd.DataFrame:
        df = pd.read_csv(csv_path)

        # robust column handling
        cols = list(df.columns)
        if self.timestamp_col not in df.columns or self.value_col not in df.columns:
            # fallback: use first 2 columns as (timestamp, value)
            if len(cols) < 2:
                raise ValueError(f"NAB csv must have >=2 columns, got {cols} in {csv_path}")
            ts_col, val_col = cols[0], cols[1]
        else:
            ts_col, val_col = self.timestamp_col, self.value_col

        ts = pd.to_datetime(df[ts_col], errors="raise", utc=False)
        values = pd.to_numeric(df[val_col], errors="coerce")

        out = pd.DataFrame({self.value_col: values.values}, index=ts)
        out.index.name = self.timestamp_col
        out = out.sort_index()

        # You can decide your missing-value policy here.
        # I keep NaN; downstream can impute/drop.
        return out

    def _get_windows_for_csv(self, csv_path: Path) -> List[Window]:
        """
        NAB windows JSON keys sometimes look like:
          "realKnownCause/nyc_taxi.csv" OR "data/realKnownCause/nyc_taxi.csv"
        so we try multiple normalized keys.
        """
        rel_from_data = csv_path.relative_to(self.data_dir).as_posix()
        rel_from_root = csv_path.relative_to(self.nab_root).as_posix() if self._is_under(csv_path, self.nab_root) else rel_from_data

        # common variants
        candidates = [
            rel_from_data,
            rel_from_root,
            f"data/{rel_from_data}",
            f"data/{rel_from_root}",
        ]

        raw = None
        for k in candidates:
            if k in self._windows_map:
                raw = self._windows_map[k]
                break

        if raw is None:
            # no windows for this series -> treat as empty
            return []

        windows: List[Window] = []
        for pair in raw:
            if not (isinstance(pair, list) and len(pair) == 2):
                continue
            start = pd.to_datetime(pair[0], errors="raise")
            end = pd.to_datetime(pair[1], errors="raise")
            # ensure start <= end
            if end < start:
                start, end = end, start
            windows.append((start, end))
        return windows

    @staticmethod
    def _is_under(p: Path, root: Path) -> bool:
        try:
            p.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _windows_to_point_labels(index: pd.DatetimeIndex, windows: List[Window]) -> np.ndarray:
        """
        Convert anomaly windows to point-wise labels aligned to `index`.
        Label rule: index[t] in [start, end] => 1 else 0.
        """
        y = np.zeros(len(index), dtype=np.int8)
        if len(index) == 0 or not windows:
            return y

        # index must be sorted
        idx = index.values

        for start, end in windows:
            s = np.searchsorted(idx, np.datetime64(start.to_datetime64()), side="left")
            e = np.searchsorted(idx, np.datetime64(end.to_datetime64()), side="right")
            if e > s:
                y[s:e] = 1
        return y


# Optional: a tiny dispatcher (you can extend later)
def get_anomaly_adapter(name: str, **kwargs) -> BaseAnomalyAdapter:
    name = name.lower()
    if name in {"nab", "numenta"}:
        return NABAdapter(**kwargs)
    raise ValueError(f"Unknown anomaly dataset: {name}")


if __name__ == "__main__":
    # quick smoke test
    # python anomaly_detection_wrapper.py /path/to/NAB
    import sys

    root = sys.argv[1]
    adapter = NABAdapter(nab_root=root)
    first_id = next(adapter.iter_series())
    s = adapter.load_series(first_id, with_point_labels=True)
    print(first_id, s.df.shape, len(s.windows), None if s.point_labels is None else s.point_labels.sum())
