# ts_caption/pipeline/windowing.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple
import pandas as pd

@dataclass
class WindowMeta:
    series_id: int
    global_start_idx: int
    global_end_idx: int
    start_time: str
    end_time: str
    length: int

def generate_windows(df: pd.DataFrame, time_col: str, window_len: int, stride: int, max_windows: Optional[int] = None) -> Iterator[Tuple[WindowMeta, pd.DataFrame]]:
    n = len(df)
    produced = 0
    for start in range(0, n - window_len + 1, stride):
        end = start + window_len
        if max_windows is not None and produced >= max_windows:
            break
        win = df.iloc[start:end].reset_index(drop=True)
        meta = WindowMeta(
            series_id=0,
            global_start_idx=start,
            global_end_idx=end - 1,
            start_time=win[time_col].iloc[0].strftime("%Y-%m-%d %H:%M"),
            end_time=win[time_col].iloc[-1].strftime("%Y-%m-%d %H:%M"),
            length=window_len,
        )
        yield meta, win
        produced += 1
