# ts_caption/datasets/generic_csv.py
from __future__ import annotations
import pandas as pd
from typing import Optional, Dict
from .base import DatasetAdapter, VariableInfo

class GenericCSVAdapter(DatasetAdapter):
    def __init__(self, time_col: str, variable_info: Optional[Dict[str, VariableInfo]] = None, default_target: str = "target"):
        self._time_col = time_col
        self._var_info = variable_info or {}
        self._default_target = default_target

    def load_dataframe(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        if self._time_col not in df.columns:
            raise ValueError(f"CSV must have time_col='{self._time_col}'.")
        df[self._time_col] = pd.to_datetime(df[self._time_col])
        return df

    def time_col(self) -> str:
        return self._time_col

    def default_target_col(self) -> str:
        return self._default_target

    def get_variable_info(self):
        return self._var_info
