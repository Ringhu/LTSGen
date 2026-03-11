# ts_caption/datasets/nab.py
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, Any

import pandas as pd


from ts_caption.datasets.base import DatasetAdapter, VariableInfo


def _parse_ts(s: str) -> pd.Timestamp:
    # NAB 时间戳有时带微秒 "....000000"
    return pd.to_datetime(s, errors="coerce")


@dataclass
class NABSeriesDesc:
    key: str                # e.g. realKnownCause/nyc_taxi.csv
    filename: str           # nyc_taxi.csv
    group: str              # realKnownCause
    stem: str               # nyc_taxi
    meaning_zh: str         # 你给的中文语义
    unit: Optional[str] = None


class NABAdapter(DatasetAdapter):
    """
    NAB:
      - 每个 CSV: timestamp,value 两列（单变量）
      - labels: 推荐 combined_windows.json（异常窗口）
    """

    def __init__(
        self,
        windows_json_path: str,
        time_col: str = "timestamp",
        value_col: str = "value",
    ) -> None:
        self._time_col = time_col
        self._value_col = value_col
        self._windows = self._load_windows(windows_json_path)

    def time_col(self) -> str:
        return self._time_col

    def load_dataframe(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        # 兼容没有 header 或列名不一致的情况
        if df.shape[1] >= 2:
            df = df.iloc[:, :2].copy()
            df.columns = [self._time_col, self._value_col]
        else:
            raise ValueError(f"NAB csv expects 2 cols (timestamp,value), got {df.shape}")

        df[self._time_col] = pd.to_datetime(df[self._time_col], errors="coerce")
        df = df.dropna(subset=[self._time_col]).reset_index(drop=True)

        df[self._value_col] = pd.to_numeric(df[self._value_col], errors="coerce")
        df = df.dropna(subset=[self._value_col]).reset_index(drop=True)
        return df

    def get_variable_info(self) -> Dict[str, VariableInfo]:
        # 默认（会被 run.py 里按“每个文件的语义”覆盖）
        return {self._value_col: VariableInfo(meaning_zh="指标值", unit=None)}

    # ---------- NAB 多文件：目录 -> 逐个 series ----------
    def iter_series(self, data_path: str) -> Iterator[Tuple[str, pd.DataFrame]]:
        """
        输入可以是：
          - .../NAB/data/realKnownCause     -> key = realKnownCause/xxx.csv
          - .../NAB/data                   -> key = realKnownCause/xxx.csv (不带 data/)
          - 单个 csv 文件路径              -> key = <parent>/<file>.csv  (尽量贴近 labels key)
        """
        p = Path(data_path)

        if p.is_file() and p.suffix.lower() == ".csv":
            key = self._make_key_from_file(p)
            yield key, self.load_dataframe(str(p))
            return

        if not p.is_dir():
            raise ValueError(f"data_path must be a NAB folder or a csv file, got: {data_path}")

        # 如果传入的是 NAB/data，则 key 以 data 下的相对路径为准（不包含 "data/"）
        is_data_root = (p.name.lower() == "data")
        for csv in sorted(p.rglob("*.csv")):
            if is_data_root:
                rel = csv.relative_to(p).as_posix()  # realKnownCause/xxx.csv
                key = rel
            else:
                # 传的是 .../realKnownCause，则 key=realKnownCause/xxx.csv
                key = f"{p.name}/{csv.name}"
            yield key, self.load_dataframe(str(csv))

    def describe_series(self, series_key: str) -> NABSeriesDesc:
        series_key = series_key.replace("\\", "/")
        group = series_key.split("/", 1)[0] if "/" in series_key else "unknown"
        filename = series_key.split("/")[-1]
        stem = Path(filename).stem

        meaning = self._infer_meaning_zh(group, stem)
        return NABSeriesDesc(
            key=series_key,
            filename=filename,
            group=group,
            stem=stem,
            meaning_zh=meaning,
            unit=None,
        )
    def default_target_col(self) -> str:
        # 这里返回你认为的默认目标列
        return self._value_col

    # ---------- 标签：窗口与当前 win_df 是否相交 ----------
    def build_label(
        self,
        win_df: pd.DataFrame,
        label_col: Optional[str] = None,
        label_mode: str = "none",
        constant_class: Optional[str] = None,
        series_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        返回：
          {
            "anomaly": bool,
            "class": "anomaly"/None,
            "segments": [{"t_start":..., "t_end":..., "start":i, "end":j}, ...]
          }
        """
        if series_key is None:
            # 如果没传 key，就只能不给真值窗口（仍能生成 caption）
            return {"anomaly": False, "class": None, "segments": []}

        time_col = self._time_col
        if time_col not in win_df.columns:
            return {"anomaly": False, "class": None, "segments": []}

        w_start = win_df[time_col].iloc[0]
        w_end = win_df[time_col].iloc[-1]

        windows = self._windows.get(series_key, [])
        segs: List[Dict[str, Any]] = []
        for (a, b) in windows:
            # 相交判断
            if b < w_start or a > w_end:
                continue
            # 取窗口内的交集索引段（近似：找落入区间的点）
            mask = (win_df[time_col] >= a) & (win_df[time_col] <= b)
            idx = win_df.index[mask]
            if len(idx) == 0:
                continue
            segs.append({
                "t_start": str(a),
                "t_end": str(b),
                "start": int(idx.min()),
                "end": int(idx.max()),
            })

        is_anom = len(segs) > 0
        return {
            "anomaly": bool(is_anom),
            "class": "anomaly" if is_anom else None,
            "segments": segs,
        }

    # ---------------- internal helpers ----------------
    def _load_windows(self, windows_json_path: str) -> Dict[str, List[Tuple[pd.Timestamp, pd.Timestamp]]]:
        """
        兼容 combined_windows.json 的结构：
          { "realKnownCause/xxx.csv": [["start","end"], ["start","end"], ...], ... }
        :contentReference[oaicite:1]{index=1}
        """
        with open(windows_json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        out: Dict[str, List[Tuple[pd.Timestamp, pd.Timestamp]]] = {}
        for k, arr in raw.items():
            k2 = k.replace("\\", "/")
            wins: List[Tuple[pd.Timestamp, pd.Timestamp]] = []
            for w in arr:
                if not isinstance(w, list) or len(w) != 2:
                    continue
                a = _parse_ts(w[0])
                b = _parse_ts(w[1])
                if pd.isna(a) or pd.isna(b):
                    continue
                wins.append((a, b))
            out[k2] = wins
        return out

    def _make_key_from_file(self, csv: Path) -> str:
        # 尽量生成像 labels 里的 key
        parts = csv.parts
        # 找 data 之后的路径
        if "data" in [p.lower() for p in parts]:
            i = [p.lower() for p in parts].index("data")
            rel = Path(*parts[i + 1:]).as_posix()
            return rel
        # 否则就用 parent/file
        return f"{csv.parent.name}/{csv.name}"

    def _infer_meaning_zh(self, group: str, stem: str) -> str:
        # A) realKnownCause（你给的“最语义明确”）
        if group == "realKnownCause":
            m = {
                "ambient_temperature_system_failure": "办公环境温度（系统故障相关）",
                "cpu_utilization_asg_misconfiguration": "AWS 集群平均 CPU 使用率（ASG 配置问题导致异常）",
                "ec2_request_latency_system_failure": "AWS 东海岸服务器请求延迟/系统性故障相关指标",
                "machine_temperature_system_failure": "工业机器内部部件温度（计划停机/难检测异常/最终故障）",
                "nyc_taxi": "纽约出租车乘客量（30 分钟聚合；马拉松/节假日/暴风雪等事件异常）",
                "rogue_agent_key_hold": "键盘按键按住时长（用户变化相关）",
                "rogue_agent_key_updown": "击键节奏/上下行击键频率（用户变化相关）",
            }
            return m.get(stem, f"NAB realKnownCause 指标：{stem}")

        # B) realAWSCloudwatch（按文件名前缀解析）
        if group == "realAWSCloudwatch":
            if stem.startswith("ec2_cpu_utilization"):
                return "EC2 CPU 使用率（CloudWatch）"
            if stem.startswith("ec2_disk_write_bytes"):
                return "EC2 磁盘写入字节数（CloudWatch）"
            if stem.startswith("ec2_disk_read_bytes"):
                return "EC2 磁盘读取字节数（CloudWatch）"
            if stem.startswith("ec2_network_in"):
                return "EC2 网络流入字节数（CloudWatch）"
            if stem.startswith("ec2_network_out"):
                return "EC2 网络流出字节数（CloudWatch）"
            if stem.startswith("elb_request_count"):
                return "ELB 请求量（CloudWatch）"
            if stem.startswith("rds_cpu_utilization"):
                return "RDS CPU 使用率（CloudWatch）"
            if stem.startswith("grok_asg_anomaly"):
                return "Auto Scaling Group（ASG）相关异常示例指标"
            return f"AWS CloudWatch 指标：{stem}"

        # C) realAdExchange
        if group == "realAdExchange":
            m = re.match(r"exchange-(\d+)_cpc_results", stem)
            if m:
                return f"在线广告交换场景 {m.group(1)}：CPC（cost per click）"
            m = re.match(r"exchange-(\d+)_cpm_results", stem)
            if m:
                return f"在线广告交换场景 {m.group(1)}：CPM（cost per mille）"
            return f"在线广告指标：{stem}"

        # D) realTraffic
        if group == "realTraffic":
            if stem.lower().startswith("occupancy_") or stem.lower().startswith("occupancy"):
                return f"交通占有率（{stem.replace('occupancy_', '')}）"
            if stem.lower().startswith("speed_") or stem.lower().startswith("speed"):
                return f"交通速度（{stem.replace('speed_', '')}）"
            if stem.lower().startswith("traveltime"):
                return f"交通行程时间（{stem.replace('TravelTime_', '')}）"
            return f"交通指标：{stem}"

        # E) realTweets
        if group == "realTweets":
            m = re.match(r"Twitter_volume_(.+)", stem)
            if m:
                return f"Twitter 提及量：{m.group(1)}（每 5 分钟一个点）"
            return f"Twitter 指标：{stem}"

        return f"NAB 指标：{group}/{stem}"
