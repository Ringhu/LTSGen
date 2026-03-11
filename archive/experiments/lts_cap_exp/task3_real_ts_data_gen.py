# task3_real_ts_data.py
# -*- coding: utf-8 -*-

"""
Task 3: 真实时间序列理解 QA 数据（基于 ETTh1）

包含四个子任务（都基于 OT 列）：
1）real_trend_class
    - 对每个窗口进行线性回归，判断整体趋势：
      A: 上升 / B: 下降 / C: 波动
    - target: "A" / "B" / "C"

2）real_max_segment
    - 将窗口均分为 4 段，找出 OT 最大值出现在第几段（1~4）
    - target: "1" / "2" / "3" / "4"

3）real_volatility_half
    - 比较前半段和后半段 OT 的标准差，哪个更“波动剧烈”
    - target: "first" / "second"
    - 若两个 std 太接近，则跳过该窗口

4）real_forecast_direction
    - 窗口长度为 L，取下一步 t=L+1 的真实 OT 值，
      若相对当前最后一个点明显上升 -> "up"
      若明显下降 -> "down"
      若变化太小 -> 跳过（避免标签不确定）
    - target: "up" / "down"

输出：
    out_dir 下每个任务 × 每个长度一份 jsonl:
        real_trend_class_L64.jsonl
        real_max_segment_L64.jsonl
        real_volatility_half_L64.jsonl
        real_forecast_direction_L64.jsonl
        ...
    每行格式：
    {
        "id": "...",
        "dataset": "ETTh1",
        "task": "real_trend_class",
        "length": L,
        "start_idx": 起始下标（0-based，在原 OT 序列中的位置）,
        "series": [float, ...],   # 当前窗口 OT 序列
        "prompt": "给 LLM 的中文问题",
        "target": "标准答案 token",
        "meta": {...}             # 一些用于调试的统计量
    }

用法示例：
python task3_real_ts_data.py \
    --data_csv /path/to/ETTh1.csv \
    --out_dir ./task3_data \
    --lengths 64 128 256 512 1024 2048 \
    --stride 16 \
    --n_samples 500 \
    --seed 42
"""

import os
import json
import argparse
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd


# ============== 工具函数 ==============

def set_random_seed(seed: int = 42):
    np.random.seed(seed)


def series_to_text(x: np.ndarray) -> str:
    """
    将数值序列转换为统一文本格式：
      t=1: 0.1234
      t=2: -0.4567
    ...
    """
    lines = [f"t={i + 1}: {v:.4f}" for i, v in enumerate(x)]
    return "\n".join(lines)

def series_to_text_notimestamp(x: np.ndarray) -> str:
    """
    将数值序列转换为纯数值文本格式：
      0.1234
      -0.4567
      ...
    """
    return "\n".join(f"{v:.4f}" for v in x)

# ============== 子任务 1：整体趋势分类 ==============

def create_real_trend_class_sample(
    dataset_name: str,
    L: int,
    sample_idx: int,
    start_idx: int,
    window: np.ndarray,
    slope_factor: float = 0.001,
) -> Dict[str, Any]:
    """
    对窗口做线性拟合，判断整体趋势：
    - slope > +tau -> A (上升)
    - slope < -tau -> B (下降)
    - 其他        -> C (波动)

    tau = slope_factor * (max(x) - min(x) + 1e-6)
    target: "A" / "B" / "C"
    """
    x = window
    t = np.arange(len(x), dtype=float)
    # polyfit 一次线性回归
    slope, intercept = np.polyfit(t, x, 1)
    value_range = float(np.max(x) - np.min(x) + 1e-6)
    tau = slope_factor * value_range

    if slope > tau:
        target = "A"
    elif slope < -tau:
        target = "B"
    else:
        target = "C"

    series_text = series_to_text_notimestamp(x)

    prompt = f"""下面是来自 {dataset_name} 数据集中 OT（Oil Temperature，油温）的一段时间序列，共 {L} 个连续时间步，单位为摄氏度（数值已经过标准化处理）：

{series_text}

我们关心这段时间内 OT 的整体变化趋势。请在下面三种描述中选择最合适的一种：

A. 整体单调上升为主（随着时间推移数值大致变大）
B. 整体单调下降为主（随着时间推移数值大致变小）
C. 上下波动，没有明显升高或降低趋势

问题：该时间序列整体趋势更接近哪一种？

请只回答一个字母，并严格按照以下格式作答（不要输出其它内容）：
Answer: A
或
Answer: B
或
Answer: C
"""

    sample_id = f"real_trend_class_L{L}_{sample_idx}"
    return {
        "id": sample_id,
        "dataset": dataset_name,
        "task": "real_trend_class",
        "length": L,
        "start_idx": start_idx,
        "series": x.tolist(),
        "prompt": prompt,
        "target": target,
        "meta": {
            "slope": float(slope),
            "value_range": value_range,
            "tau": tau,
        },
    }


# ============== 子任务 2：最大值所在四分段 ==============

def create_real_max_segment_sample(
    dataset_name: str,
    L: int,
    sample_idx: int,
    start_idx: int,
    window: np.ndarray,
    num_segments: int = 4,
) -> Dict[str, Any]:
    """
    将窗口在时间轴上平均划分为 num_segments 段，
    找出 OT 最大值所在的段索引（1-based）。
    target: "1" / "2" / "3" / "4"
    """
    x = window
    L = len(x)
    max_idx = int(np.argmax(x))  # 0-based

    seg_len = L // num_segments
    # 最后一段包含剩余所有点
    for k in range(num_segments):
        start = k * seg_len
        end = L if k == num_segments - 1 else (k + 1) * seg_len
        if start <= max_idx < end:
            seg_id = k + 1
            break
    else:
        seg_id = num_segments  # 理论上不会到这里

    target = str(seg_id)
    series_text = series_to_text_notimestamp(x)

    prompt = f"""下面是来自 {dataset_name} 数据集中 OT（Oil Temperature，油温）的一段时间序列，共 {L} 个连续时间步：

{series_text}

我们将这段时间按顺序平均划分为 {num_segments} 段：
1. 第 1 段：大约为前 {100 // num_segments}% 的时间
2. 第 2 段：紧接着的 {100 // num_segments}% 的时间
3. 第 3 段：再接着的 {100 // num_segments}% 的时间
4. 第 4 段：最后 {100 // num_segments}% 的时间

问题：在这段时间中，OT 的**最大值**更可能出现在哪一段？

请只回答 1/2/3/4 中的一个数字，并严格按照以下格式作答（不要输出其它内容）：
Answer: 1
或
Answer: 2
或
Answer: 3
或
Answer: 4
"""

    sample_id = f"real_max_segment_L{L}_{sample_idx}"
    return {
        "id": sample_id,
        "dataset": dataset_name,
        "task": "real_max_segment",
        "length": L,
        "start_idx": start_idx,
        "series": x.tolist(),
        "prompt": prompt,
        "target": target,
        "meta": {
            "max_index_in_window_1based": max_idx + 1,
            "segment_id": seg_id,
            "num_segments": num_segments,
        },
    }


# ============== 子任务 3：波动更剧烈的半段 ==============

def create_real_volatility_half_sample(
    dataset_name: str,
    L: int,
    sample_idx: int,
    start_idx: int,
    window: np.ndarray,
    min_std_diff_factor: float = 0.05,
) -> Dict[str, Any] | None:
    """
    比较前半段 vs 后半段的标准差，哪个更“波动剧烈”。

    - 若 |std1 - std2| < min_std_diff_factor * max(std1, std2)，认为差别不明显，返回 None（跳过）
    - target: "first" / "second"
    """
    x = window
    L = len(x)
    mid = L // 2
    first = x[:mid]
    second = x[mid:]

    std1 = float(np.std(first))
    std2 = float(np.std(second))
    max_std = max(std1, std2, 1e-6)
    diff = abs(std1 - std2)

    if diff < min_std_diff_factor * max_std:
        # 差异不明显，跳过
        return None

    target = "first" if std1 > std2 else "second"
    series_text = series_to_text_notimestamp(x)

    prompt = f"""下面是来自 {dataset_name} 数据集中 OT（Oil Temperature，油温）的一段时间序列，共 {L} 个连续时间步：

{series_text}

我们将这段时间划分为两部分：
- 前半段：t = 1 .. {mid}
- 后半段：t = {mid + 1} .. {L}

问题：哪一半的 OT 数值波动更剧烈（也就是变化幅度更大）？

请只回答下面两个英文单词之一，并严格按照以下格式作答（不要输出其它内容）：
Answer: first   （如果前半段波动更大）
Answer: second  （如果后半段波动更大）
"""

    sample_id = f"real_volatility_half_L{L}_{sample_idx}"
    return {
        "id": sample_id,
        "dataset": dataset_name,
        "task": "real_volatility_half",
        "length": L,
        "start_idx": start_idx,
        "series": x.tolist(),
        "prompt": prompt,
        "target": target,
        "meta": {
            "std_first": std1,
            "std_second": std2,
            "std_diff": diff,
        },
    }


# ============== 子任务 4：下一步上升/下降预测 ==============

def create_real_forecast_direction_sample(
    dataset_name: str,
    L: int,
    sample_idx: int,
    start_idx: int,
    window: np.ndarray,
    next_value: float,
    diff_factor: float = 0.1,
) -> Dict[str, Any] | None:
    """
    基于窗口 [t=1..L] 的 OT 序列，预测下一时刻 t=L+1 相比 t=L 是上升还是下降。

    - 若 |next_value - x[-1]| < diff_factor * std(x) -> 认为变化不明显，跳过（返回 None）
    - target: "up" / "down"
    """
    x = window
    last = float(x[-1])
    diff = float(next_value - last)
    std_x = float(np.std(x)) + 1e-6
    tau = diff_factor * std_x

    if abs(diff) < tau:
        # 变化过小，标签不确定，跳过
        return None

    target = "up" if diff > 0 else "down"
    series_text = series_to_text_notimestamp(x)

    prompt = f"""下面是来自 {dataset_name} 数据集中 OT（Oil Temperature，油温）的一段时间序列，共 {L} 个连续观测值，从上到下依次为这段时间内连续观测到的油温：

    {series_text}

    现在假设你只能根据这段历史数据来判断**下一时刻**的走势：
    - 序列中最后一个观测值可以看作当前时刻的油温。
    - 下一时刻的油温是紧接在这段序列后面的一个真实观测值（对你来说是未知的）。

    问题：你认为下一时刻的 OT 相比当前这最后一个观测值：
    - 是上涨（数值变大）还是下跌（数值变小）？

    请只回答下面两个英文单词之一，并严格按照以下格式作答（不要输出其它内容）：
    Answer: up
    或
    Answer: down
    """


    sample_id = f"real_forecast_direction_L{L}_{sample_idx}"
    return {
        "id": sample_id,
        "dataset": dataset_name,
        "task": "real_forecast_direction",
        "length": L,
        "start_idx": start_idx,
        "series": x.tolist(),
        "prompt": prompt,
        "target": target,
        "meta": {
            "last_value": last,
            "next_value": float(next_value),
            "diff": diff,
            "tau": tau,
        },
    }


# ============== 数据集生成主流程 ==============

TASK_CREATORS = {
    "real_trend_class": create_real_trend_class_sample,
    "real_max_segment": create_real_max_segment_sample,
    "real_volatility_half": create_real_volatility_half_sample,
    "real_forecast_direction": create_real_forecast_direction_sample,
}


def generate_task3_datasets(
    data_csv: str,
    out_dir: str,
    lengths: List[int],
    stride: int,
    n_samples_per_task: int,
    seed: int = 42,
):
    os.makedirs(out_dir, exist_ok=True)
    set_random_seed(seed)

    # 读取 ETTh1.csv
    df = pd.read_csv(data_csv)
    dataset_name = "ETTh1"
    if "OT" not in df.columns:
        raise ValueError(f"CSV 文件中找不到 OT 列，实际列为: {list(df.columns)}")

    ot_values = df["OT"].to_numpy(dtype=float)
    N = len(ot_values)
    print(f"[INFO] Loaded {dataset_name} from {data_csv}, total length = {N}")

    # forecast 任务需要 L+1，有效长度要减 1
    forecast_horizon = 1

    for task_name, creator_fn in TASK_CREATORS.items():
        for L in lengths:
            out_path = os.path.join(out_dir, f"{task_name}_L{L}.jsonl")
            print(f"[INFO] Generating {task_name}, L={L}, stride={stride}, "
                  f"max_samples={n_samples_per_task} -> {out_path}")

            count = 0
            with open(out_path, "w", encoding="utf-8") as f:
                # 统一用能够支持 forecast 的最大起点，
                # 这样不同任务的窗口来源比较一致
                max_start = N - (L + forecast_horizon)
                if max_start <= 0:
                    print(f"[WARN] L={L} too long for dataset length N={N}, skip.")
                    continue

                for start_idx in range(0, max_start + 1, stride):
                    window = ot_values[start_idx:start_idx + L]

                    if task_name == "real_forecast_direction":
                        next_value = ot_values[start_idx + L]
                        sample = creator_fn(
                            dataset_name, L, count, start_idx, window, next_value
                        )
                    else:
                        sample = creator_fn(
                            dataset_name, L, count, start_idx, window
                        )

                    if sample is None:
                        # 某些窗口可能因为标签不确定被跳过
                        continue

                    f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                    count += 1

                    if count >= n_samples_per_task:
                        break

            print(f"[INFO] {task_name}, L={L}: actually generated {count} samples.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate real TS QA datasets for Task 3 (ETTh1)."
    )
    parser.add_argument(
        "--data_csv",
        type=str,
        required=True,
        help="ETTh1.csv 的路径（包含 OT 列）",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        required=True,
        help="输出 JSONL 数据集的目录",
    )
    parser.add_argument(
        "--lengths",
        type=int,
        nargs="+",
        default=[64, 128, 256, 512, 1024, 2048],
        help="时间序列窗口长度列表",
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=64,
        help="滑动窗口步长（起点之间的间隔）",
    )
    parser.add_argument(
        "--n_samples",
        type=int,
        default=500,
        help="每个任务 × 每个长度 最多生成多少样本",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    generate_task3_datasets(
        data_csv=args.data_csv,
        out_dir=args.out_dir,
        lengths=args.lengths,
        stride=args.stride,
        n_samples_per_task=args.n_samples,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
