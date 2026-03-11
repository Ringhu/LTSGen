# ts_caption/config.py
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class RunConfig:
    dataset_type: str                 # "ett" / "generic_csv" / "weather_example" / 自己新写的
    csv_path: str
    output_jsonl: str
    dataset_name: str
    task: str = "forecasting"         # forecasting / anomaly_detection / classification / etc.

    # windowing
    window_len: int = 512
    stride: int = 256
    max_windows: Optional[int] = None

    # columns
    time_col: Optional[str] = None    # generic_csv 用
    target_col: str = "OT"
    series_cols: Optional[List[str]] = None

    # labels (optional)
    label_col: Optional[str] = None
    label_mode: str = "none"          # none / any / majority / first / constant
    constant_class: Optional[str] = None

    # claim + caption
    language: str = "zh"
    enforce_claims: bool = True       # True: 失败 claim 会被删/降级
