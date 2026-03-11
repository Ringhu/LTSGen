from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

@dataclass
class WrapperConfig:
    """所有 Wrapper 通用的配置参数"""
    # 基础配置
    input_path: str
    dataset_name: str
    task: str = "forecasting"
    
    # 列配置 (LTSF/Forecasting 常用)
    time_col: Optional[str] = None
    series_cols: Optional[List[str]] = None
    target_col: Optional[str] = None
    
    # [新增] 指定处理第几个序列 (0-based index)
    # 如果为 None 且 target_col 也没指定，则默认遍历该样本下的所有序列
    target_series_index: Optional[int] = None
    
    # 窗口/切片配置
    window_mode: str = "sliding"  # sliding / full
    window_len: int = 512
    stride: int = 256
    max_windows: Optional[int] = None

    # UCR 特有
    ucr_name: Optional[str] = None
    ucr_split: str = "test"
    ucr_label_semantics: str = "readme"
    
    # LLM 相关 (用于 Wrapper 内部推断 Label 含义等)
    llm_enabled: bool = False


class BaseWrapper(ABC):
    """
    统一数据源接口。
    核心契约：调用方只需要 for sample in wrapper: 即可。
    """
    
    def __init__(self, cfg: WrapperConfig):
        self.cfg = cfg

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """允许直接 for x in wrapper"""
        return self.iter_samples()

    @abstractmethod
    def iter_samples(self) -> Iterator[Dict[str, Any]]:
        """
        核心生成器。
        Yields:
            Dict: {
                "timestamps": List[str],      # [T]
                "values": List[List[float]],  # [T, D]
                "series_cols": List[str],     # [D]
                "target_col": str,
                "label": Any,                 # Classification/Anomaly label
                "variables_meta": List[Dict], # 变量含义
                "domain_context": Dict,       # 领域背景
                "series_key": str,            # 唯一标识
                "indices": Tuple[int, int],   # (start, end)
            }
        """
        pass