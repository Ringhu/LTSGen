# ts_caption/datasets/weather_example.py
from __future__ import annotations
import pandas as pd
from typing import Dict
from .base import DatasetAdapter, VariableInfo

VAR_INFO_WEATHER: Dict[str, VariableInfo] = {
    "temp": VariableInfo("温度", "°C"),
    "humidity": VariableInfo("湿度", "%"),
    "pressure": VariableInfo("气压", "hPa"),
}

class WeatherExampleAdapter(DatasetAdapter):
    def load_dataframe(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        if "timestamp" not in df.columns:
            raise ValueError("Weather CSV must have 'timestamp'.")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def time_col(self) -> str:
        return "timestamp"

    def default_target_col(self) -> str:
        return "temp"

    def get_variable_info(self):
        return VAR_INFO_WEATHER
