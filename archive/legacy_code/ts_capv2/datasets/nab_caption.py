# ts_capv2/datasets/nab_caption.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterator, Optional

import numpy as np
import pandas as pd

from ts_capv2.wrappers.anomaly_detection_wrapper import NABAdapter  # 或者改成相对导入你放置的位置


@dataclass
class WindowSample:
    sample_id: str
    values: np.ndarray                 # (L,)
    timestamps: Optional[pd.DatetimeIndex]  # (L,) or None
    label: Optional[int]               # 0/1 (是否异常)
    meta: Dict[str, object]


class NABCaptionWindowAdapter:
    """
    将 NAB 的“整条序列”转换为“滑窗样本流”，用于你现有的 claims/caption pipeline。
    """

    def __init__(
        self,
        nab_root: str,
        windows_json_path: str | None = None,
        data_dir: str | None = None,
        window_len: int = 256,
        stride: int = 64,
        dropna: bool = True,
        with_timestamps: bool = True,
    ):
        self.raw = NABAdapter(
            nab_root=nab_root,
            windows_json_path=windows_json_path,
            data_dir=data_dir,
            value_col="value",
            timestamp_col="timestamp",
        )
        self.window_len = int(window_len)
        self.stride = int(stride)
        self.dropna = dropna
        self.with_timestamps = with_timestamps

    def iter_samples(self) -> Iterator[WindowSample]:
        L = self.window_len
        S = self.stride

        for series_id in self.raw.iter_series():
            s = self.raw.load_series(series_id, with_point_labels=True)
            df = s.df

            # 取 value
            v = df[self.raw.default_target_col()].to_numpy(dtype=np.float32)
            ts = df.index

            # 可选处理 NaN（建议先 drop，避免 claim 计算炸）
            if self.dropna:
                mask = ~np.isnan(v)
                v = v[mask]
                ts = ts[mask]
                y = s.point_labels[mask] if s.point_labels is not None else None
            else:
                y = s.point_labels

            if len(v) < L:
                continue

            for start in range(0, len(v) - L + 1, S):
                end = start + L
                wv = v[start:end]
                wts = ts[start:end] if self.with_timestamps else None

                # window label：只要窗口内出现过点标签 1 就算异常
                wlabel = None
                if y is not None:
                    wlabel = int(np.any(y[start:end] == 1))

                sample_id = f"{series_id}#{start}:{end}"

                yield WindowSample(
                    sample_id=sample_id,
                    values=wv,
                    timestamps=wts,
                    label=wlabel,
                    meta={
                        "dataset": "NAB",
                        "series_id": series_id,
                        "start": start,
                        "end": end,
                        "anomaly_windows": [(str(a), str(b)) for a, b in s.windows],
                    },
                )
