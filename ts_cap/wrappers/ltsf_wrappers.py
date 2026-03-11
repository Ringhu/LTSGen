from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd

from .base import BaseWrapper, WrapperConfig
from .windowing import iter_windows


@dataclass
class VarInfo:
    meaning_zh: str
    unit: Optional[str] = None


# --------- dataset domain context ----------
DOMAIN_CONTEXT_ZH: Dict[str, str] = {
    "ett": "ETT 变压器数据：date 为时间戳；HUFL/HULL/MUFL/MULL/LUFL/LULL 为不同负载；OT 为油温（常作为预测目标）。",
    "electricity": "ElectricityLoadDiagrams：date 为时间戳；其余列通常每列对应一个用户/站点的用电量序列（多节点）。",
    "traffic": "Traffic：date 为时间戳；其余列通常每列对应一个道路传感器的占有率（occupancy rate）序列（多传感器）。",
    "exchange_rate": "Exchange Rate：常见为 8 个国家/地区的日度汇率多变量序列；部分打包版可能无 date 列，用行号隐含时间。",
    "illness": "National Illness（ILI）：周频；包含 wILI、分年龄段计数、机构数量等；用于预测流感样病例相关指标。",
    "weather": "Jena 气象站：10 分钟级多变量气象量（气温、气压、湿度、风速风向等），用于多变量预测。",
}


# --------- variable info maps ----------
VAR_INFO_ETT: Dict[str, VarInfo] = {
    "OT": VarInfo("油温"),
    "HUFL": VarInfo("高负荷有用负载"),
    "HULL": VarInfo("高负荷无用负载"),
    "MUFL": VarInfo("中负荷有用负载"),
    "MULL": VarInfo("中负荷无用负载"),
    "LUFL": VarInfo("低负荷有用负载"),
    "LULL": VarInfo("低负荷无用负载"),
}

VAR_INFO_ILLNESS: Dict[str, VarInfo] = {
    "% WEIGHTED ILI": VarInfo("加权 ILI 就诊占比（wILI）", "%"),
    "%UNWEIGHTED ILI": VarInfo("未加权 ILI 就诊占比", "%"),
    "AGE 0-4": VarInfo("0–4 岁相关计数"),
    "AGE 5-24": VarInfo("5–24 岁相关计数"),
    "ILITOTAL": VarInfo("ILI 总计数"),
    "NUM. OF PROVIDERS": VarInfo("上报医疗机构数量"),
    "OT": VarInfo("预测目标（部分打包版会重命名为 OT）"),
}

VAR_INFO_WEATHER: Dict[str, VarInfo] = {
    "T (degC)": VarInfo("气温", "°C"),
    "p (mbar)": VarInfo("气压", "mbar"),
    "rh (%)": VarInfo("相对湿度", "%"),
    "wv (m/s)": VarInfo("风速", "m/s"),
    "max. wv (m/s)": VarInfo("最大风速", "m/s"),
    "wd (deg)": VarInfo("风向角", "deg"),
    "Tpot (K)": VarInfo("位温", "K"),
    "Tdew (degC)": VarInfo("露点温度", "°C"),
    "temp": VarInfo("温度", "°C"),
    "humidity": VarInfo("湿度", "%"),
    "pressure": VarInfo("气压", "hPa"),
    "OT": VarInfo("预测目标（很多基准会把目标列统一命名为 OT）"),
}


def _auto_time_format(dt: pd.Series) -> List[str]:
    return pd.to_datetime(dt, errors="coerce").dt.strftime("%Y-%m-%d %H:%M").fillna("").tolist()


def _guess_time_col(df: pd.DataFrame, preferred: List[str]) -> Optional[str]:
    cols = {c.strip(): c for c in df.columns}
    for p in preferred:
        if p in cols:
            return cols[p]
    if len(df.columns) >= 1:
        return df.columns[0]
    return None


def _pick_numeric_cols(df: pd.DataFrame, time_col: str) -> List[str]:
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    return [c for c in num_cols if c != time_col]


def _build_variables_meta(series_cols: List[str], target_col: str, var_info: Dict[str, VarInfo]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, c in enumerate(series_cols):
        info = var_info.get(c)
        meaning = info.meaning_zh if info else c
        unit = info.unit if info else None
        out.append(
            {
                "name": c,
                "index": i,
                "role": "target" if c == target_col else "feature",
                "meaning_zh": meaning,
                "unit": unit,
            }
        )
    return out


def _make_default_varinfo_for_many_cols(kind: str, cols: List[str]) -> Dict[str, VarInfo]:
    out: Dict[str, VarInfo] = {}
    for c in cols:
        if kind == "electricity":
            out[c] = VarInfo(f"用电量（节点/用户 {c}）")
        elif kind == "traffic":
            out[c] = VarInfo(f"道路占有率（传感器 {c}）")
        else:
            out[c] = VarInfo(f"变量 {c}")
    return out


class LTSFWrapper(BaseWrapper):
    """
    通用长序列预测数据 Wrapper。
    负责：读取 CSV -> 处理列 -> 滑动窗口切片 -> Yield Sample
    """

    def iter_samples(self) -> Iterator[Dict[str, Any]]:
        # 1. 读取与预处理
        df = pd.read_csv(self.cfg.input_path)
        df.columns = [c.strip() for c in df.columns]

        # Time col
        if self.cfg.dataset_name == "weather":
            guessed = _guess_time_col(df, ["date", "Date Time", "datetime", "timestamp"])
        else:
            guessed = _guess_time_col(df, ["date", "Date", "datetime", "timestamp", "time"])
        time_col = self.cfg.time_col or guessed

        if time_col is None or time_col not in df.columns:
            timestamps = [f"idx_{i}" for i in range(len(df))]
        else:
            timestamps = _auto_time_format(df[time_col])

        # Numeric cols
        if self.cfg.series_cols:
            cols = [c for c in self.cfg.series_cols if c in df.columns and c != time_col]
        else:
            cols = _pick_numeric_cols(df, time_col) if (time_col and time_col in df.columns) else df.select_dtypes(include=["number"]).columns.tolist()

        if not cols:
            raise ValueError(f"No numeric series cols found in {self.cfg.input_path}")

        # Target col
        target = self.cfg.target_col or (cols[0] if self.cfg.dataset_name in ("electricity", "traffic") else (cols[-1]))
        if target not in cols:
            cols = [target] + cols if target in df.columns else cols
        if target not in cols:
            raise ValueError(f"target_col='{target}' not found among selected cols={cols}")

        # Var info
        if self.cfg.dataset_name == "ett":
            var_info = VAR_INFO_ETT
        elif self.cfg.dataset_name == "illness":
            var_info = VAR_INFO_ILLNESS
        elif self.cfg.dataset_name == "weather":
            var_info = VAR_INFO_WEATHER
        elif self.cfg.dataset_name in ("electricity", "traffic"):
            var_info = _make_default_varinfo_for_many_cols(self.cfg.dataset_name, cols)
        else:
            # exchange_rate or others
            if len(cols) == 8 and self.cfg.dataset_name == "exchange_rate":
                countries = ["Australia", "Britain", "Canada", "Switzerland", "China", "Japan", "New Zealand", "Singapore"]
                var_info = {c: VarInfo(f"汇率（{countries[i]}）") for i, c in enumerate(cols)}
            else:
                var_info = {c: VarInfo(f"变量 {c}") for c in cols}

        # Values
        values = df[cols].astype("float64", errors="ignore")
        values = (
            values.apply(pd.to_numeric, errors="coerce")
            .ffill()
            .bfill()
            .fillna(0.0)
        )
        v_list = values.to_numpy(dtype=float).tolist()
        variables_meta = _build_variables_meta(cols, target, var_info)
        
        domain_context = {
            "background_zh": DOMAIN_CONTEXT_ZH.get(self.cfg.dataset_name, ""), 
            "dataset_kind": self.cfg.dataset_name
        }

        # 2. 切片逻辑 (Windowing)
        iterator = iter_windows(
            timestamps=timestamps,
            values=v_list,
            window_mode=self.cfg.window_mode,
            window_len=self.cfg.window_len,
            stride=self.cfg.stride,
            max_windows=self.cfg.max_windows
        )

        for meta, t_win, v_win in iterator:
            yield {
                "timestamps": t_win,
                "values": v_win,
                "series_cols": cols,
                "target_col": target,
                "variables_meta": variables_meta,
                "domain_context": domain_context,
                "label": None,
                "series_key": "series_0",
                "indices": (meta.global_start_idx, meta.global_end_idx),
            }