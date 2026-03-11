# ts_caption/datasets/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd

@dataclass
class VariableInfo:
    meaning_zh: str
    unit: Optional[str] = None

class DatasetAdapter(ABC):
    """
    负责把任意数据集统一成：
      - DataFrame: [time_col] + series_cols (+ label_col optional)
      - time_col 必须能转为 datetime
      - series_cols 全是数值列
    """

    @abstractmethod
    def load_dataframe(self, csv_path: str) -> pd.DataFrame:
        ...

    @abstractmethod
    def time_col(self) -> str:
        ...

    @abstractmethod
    def default_target_col(self) -> str:
        ...

    def get_variable_info(self) -> Dict[str, VariableInfo]:
        return {}

    def build_label(self, win_df: pd.DataFrame, label_col: Optional[str], label_mode: str, constant_class: Optional[str]) -> Dict[str, Any]:
        """
        可复用的通用窗口 label 汇聚逻辑：
        - anomaly_detection: label_col 是 0/1 或 bool -> anomaly = any/majority/first
        - classification: label_col 是 class id/string -> class = any/majority/first/constant
        """
        if label_mode == "none" or label_col is None or label_col not in win_df.columns:
            return {"anomaly": False, "class": None}

        s = win_df[label_col]

        if label_mode == "constant":
            return {"anomaly": False, "class": constant_class}

        # boolean / numeric anomaly
        if s.dtype.kind in "biu" or s.dtype == bool:
            vals = s.astype(int).to_numpy()
            if label_mode == "any":
                return {"anomaly": bool(vals.max() > 0), "class": None}
            if label_mode == "majority":
                return {"anomaly": bool(vals.mean() >= 0.5), "class": None}
            if label_mode == "first":
                return {"anomaly": bool(vals[0] > 0), "class": None}
            return {"anomaly": False, "class": None}

        # categorical class
        vals = s.astype(str).to_list()
        if label_mode == "first":
            return {"anomaly": False, "class": vals[0]}
        if label_mode in ("any", "majority"):
            # majority for class: 频次最高
            from collections import Counter
            c = Counter(vals)
            cls = c.most_common(1)[0][0] if c else None
            return {"anomaly": False, "class": cls}

        return {"anomaly": False, "class": None}
