# ts_capv2/wrappers/windowing.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple, Union

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


@dataclass
class WindowMeta:
    global_start_idx: int
    global_end_idx: int
    length: int


def iter_windows(
    timestamps: List[str],
    values: Union[List[List[float]], np.ndarray],
    window_mode: str,
    window_len: int,
    stride: int,
    max_windows: Optional[int] = None,
) -> Iterator[Tuple[WindowMeta, List[str], List[List[float]]]]:
    """
    使用 numpy sliding_window_view 实现高性能切片。
    """
    # 1. 确保输入是 numpy array
    # values shape: (N, D) -- 推荐, 或者 (N,)
    arr_values = np.asarray(values)
    arr_timestamps = np.asarray(timestamps)

    n = len(arr_timestamps)
    if n == 0:
        return

    # --- 模式 A: 全量窗口 ---
    if window_mode == "full":
        yield WindowMeta(0, n - 1, n), timestamps, arr_values.tolist()
        return

    if window_mode != "sliding":
        raise ValueError(f"Unknown window_mode={window_mode}, expected 'sliding' or 'full'.")

    wl = int(window_len)
    st = int(stride)
    
    # 容错：如果窗口比数据长，回退到 full
    if wl <= 0 or wl > n:
        yield WindowMeta(0, n - 1, n), timestamps, arr_values.tolist()
        return

    # --- 模式 B: 滑动窗口 (Vectorized) ---
    try:
        # sliding_window_view(x, window_shape, axis=0)
        # 行为注意：它会将窗口维度(W)放到最后！
        # 如果输入是 (N, D)，结果是 (Num_Wins, D, W) <-- 这是一个坑
        # 如果输入是 (N,)，结果是 (Num_Wins, W)
        
        # 1. 值的处理
        v_view = sliding_window_view(arr_values, window_shape=wl, axis=0)[::st]
        
        # 修正维度顺序：
        if arr_values.ndim == 2:
            # v_view shape: (Num, D, W)
            # 我们需要: (Num, W, D)
            # 对应的轴置换是 (0, 2, 1)
            v_wins = v_view.transpose(0, 2, 1)
        else:
            # arr_values.ndim == 1 -> v_view shape: (Num, W)
            # 这种情况下我们需要手动升维成 (Num, W, 1) 以满足 core 的 2D 要求，
            # 或者保持 (Num, W) 让 core 去 unsqueeze。
            # 但为了统一性，我们在 yield 前处理。
            v_wins = v_view 

        # 2. 时间戳的处理 (timestamps 永远是 1D)
        # t_view shape: (Num, W)
        t_wins = sliding_window_view(arr_timestamps, window_shape=wl, axis=0)[::st]

    except Exception:
        # Fallback (兼容旧版 numpy 或特殊情况)
        idxs = np.arange(0, n - wl + 1, st)
        # 注意：这里 list slice 行为是正常的 (W, D)
        v_wins = [arr_values[i : i + wl] for i in idxs]
        t_wins = [arr_timestamps[i : i + wl] for i in idxs]

    produced = 0
    num_windows = len(v_wins)

    for i in range(num_windows):
        if max_windows is not None and produced >= int(max_windows):
            break
        
        start_idx = i * st
        end_idx = start_idx + wl - 1
        
        # 处理 v_win 的具体数据
        current_v_arr = v_wins[i]
        
        # 容错：如果输入是 1D (N,)，切片后是 (W,)
        # core 要求 values 必须是 2D (T, D)。如果是 (W,) 需要变成 (W, 1)
        if current_v_arr.ndim == 1:
            current_v_arr = current_v_arr[:, np.newaxis] # (W, 1)

        current_t = t_wins[i].tolist()
        current_v = current_v_arr.tolist()

        yield WindowMeta(start_idx, end_idx, wl), current_t, current_v
        produced += 1