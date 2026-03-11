from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple


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

    # 指定处理第几个序列 (0-based index)
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
                "label": Any,
                "variables_meta": List[Dict],
                "domain_context": Dict,
                "series_key": str,            # 原始序列唯一标识（例如 Adiac/test/000001）
                "indices": Tuple[int, int],   # (start, end) 窗口范围（用于 windowing）
            }
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Resume / Cursor support (new)
    # -------------------------------------------------------------------------
    @staticmethod
    def cursor_key(sample_or_cursor: Dict[str, Any]) -> Tuple[str, int, int]:
        """
        将样本（或 cursor dict）转成可比较的 key。
        默认采用 (series_key, start_idx, end_idx)。

        约束：
        - series_key 必须存在
        - indices 必须可解析为 (start, end)
        """
        series_key = str(sample_or_cursor.get("series_key", ""))
        indices = sample_or_cursor.get("indices", None)

        if indices is None or not isinstance(indices, (list, tuple)) or len(indices) != 2:
            raise ValueError(f"Invalid indices in sample/cursor: {indices}")

        s = int(indices[0])
        e = int(indices[1])
        return (series_key, s, e)

    def iter_samples_from_cursor(self, start_after: Dict[str, Any]) -> Optional[Iterator[Dict[str, Any]]]:
        """
        可选的“快速 seek”扩展点：
        - 如果某个 wrapper 能根据 (series_key, indices) 直接定位到 start_after 之后，
          可以覆盖此方法并返回一个 iterator。
        - 默认返回 None 表示不支持快速 seek，将走 BaseWrapper 的线性 fallback。

        注意：start_after 表示“从它之后开始”，即跳过与其 key 相同的样本本身。
        """
        return None

    def iter_resume(
        self,
        *,
        start_after: Optional[Dict[str, Any]] = None,
        start_index: int = 0,
    ) -> Iterator[Dict[str, Any]]:
        """
        通用可恢复迭代器：
        - start_index：按序号跳过（弱语义，但快）
        - start_after：按 (series_key, indices) 跳过到该样本之后（强语义）
          两者同时给定时：先按 start_index，然后再按 start_after 校准。

        典型用法：
            cursor = {"series_key": last_series_key, "indices": last_indices}
            it = wrapper.iter_resume(start_after=cursor)
        """
        it = self.iter_samples()

        # 1) 先做 index-based skip（可选）
        if start_index and start_index > 0:
            for _ in range(start_index):
                try:
                    next(it)
                except StopIteration:
                    return

        if not start_after:
            yield from it
            return

        # 2) 优先走 wrapper 自己的快速 seek（如果实现了）
        fast_it = self.iter_samples_from_cursor(start_after)
        if fast_it is not None:
            yield from fast_it
            return

        # 3) fallback：线性扫描到 start_after，然后从其后继续
        target_key = self.cursor_key(start_after)
        found = False

        for sample in it:
            try:
                k = self.cursor_key(sample)
            except Exception:
                # 若某些 wrapper 产出异常样本，不建议 silent skip，这里直接继续扫描
                continue

            if k == target_key:
                found = True
                break

        if not found:
            # 没找到，保守策略：从头继续会导致重复；这里选择“直接结束”，交给调用方处理
            return

        # 继续 yield 剩余样本（从 target 之后）
        yield from it
