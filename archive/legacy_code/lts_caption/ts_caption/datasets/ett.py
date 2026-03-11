# ts_caption/datasets/ett.py
from __future__ import annotations
import pandas as pd
from typing import Dict
from .base import DatasetAdapter, VariableInfo

VAR_INFO_ETT: Dict[str, VariableInfo] = {
    "OT":   VariableInfo("油温"),
    "HUFL": VariableInfo("高负荷有用负载"),
    "HULL": VariableInfo("高负荷无用负载"),
    "MUFL": VariableInfo("中负荷有用负载"),
    "MULL": VariableInfo("中负荷无用负载"),
    "LUFL": VariableInfo("低负荷有用负载"),
    "LULL": VariableInfo("低负荷无用负载"),
}

class ETTAdapter(DatasetAdapter):
    def load_dataframe(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        if "date" not in df.columns:
            raise ValueError("ETT CSV must have a 'date' column.")
        df["date"] = pd.to_datetime(df["date"])
        return df

    def time_col(self) -> str:
        return "date"

    def default_target_col(self) -> str:
        return "OT"

    def get_variable_info(self):
        return VAR_INFO_ETT
