# task2_needle_ts_data.py
# -*- coding: utf-8 -*-

"""
Task 2: 长上下文记忆 / needle-in-a-haystack 时间序列数据生成脚本

包含两个任务：
1）needle_argmax
    - 构造一个长度为 L 的随机序列，大部分值在 [-1, 1] 之间
    - 随机选一个时间步 t*，在该位置插入一个很大的值（比如 5~10）
    - 问题：最大值出现在第几个时间步？（t 从 1 到 L）
    - target: "t*"（字符串）

2）needle_query_value
    - 构造一个长度为 L 的随机序列，值在 [-1, 1] 之间
    - 随机选一个时间步 k
    - 问题：t = k 时的数值是多少？（四舍五入保留两位小数）
    - target: "{value:.2f}"（字符串）

输出格式（每行一个 JSON）：
{
    "id": "...",
    "task": "needle_argmax" 或 "needle_query_value",
    "length": L,
    "series": [float, ...],
    "prompt": "给 LLM 的完整输入",
    "target": "标准答案字符串",
    "meta": {...}  # 方便调试
}

用法示例：
python task2_needle_ts_data.py \
    --out_dir ./task2_data \
    --lengths 64 128 256 512 1024 2048 \
    --n_samples 500 \
    --seed 42
"""

import os
import json
import argparse
from typing import Dict, Any, List, Tuple

import numpy as np


# ============== 基础工具 ==============

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

# ============== 任务 1：needle_argmax ==============

def generate_needle_series_for_argmax(
    L: int,
    spike_range: Tuple[float, float] = (5.0, 10.0),
) -> Dict[str, Any]:
    """
    生成一个长度为 L 的随机序列，其中：
    - 大部分值 ~ U(-1, 1)
    - 随机选一个位置 t*，插入一个很大的值（spike），保证该位置是唯一最大值

    返回：
    {
        "series": np.ndarray shape=(L,),
        "needle_index": int  # 1-based
        "needle_value": float
    }
    """
    x = np.random.uniform(-1.0, 1.0, size=L)

    idx = np.random.randint(0, L)  # 0-based
    spike = np.random.uniform(spike_range[0], spike_range[1])
    x[idx] = spike

    return {
        "series": x,
        "needle_index": idx + 1,  # 转为 1-based
        "needle_value": spike,
    }


def create_needle_argmax_sample(
    sample_idx: int,
    L: int,
) -> Dict[str, Any]:
    """
    任务：给定序列，问“数值最大的位置是第几个时间步（1..L）？”
    target: "1" / "2" / ... / str(L)
    """
    gen = generate_needle_series_for_argmax(L)
    x = gen["series"]
    needle_index = gen["needle_index"]
    needle_value = gen["needle_value"]

    series_text = series_to_text_notimestamp(x)

    prompt = f"""下面是一段长度为 {L} 的单变量时间序列（单位为任意数值），从上到下按顺序给出了这一段时间内连续观测到的数值：

    {series_text}

    问题：在这段序列中，哪一个位置上的数值最大？请给出这个最大值在序列中的位置编号。
    约定：从上到下、从左到右依次编号为第 1 个、第 2 个、...、一直到第 {L} 个。

    请严格按照以下格式作答（不要输出其它内容）：
    Answer: <整数>
    例如：Answer: 123
    """


    sample_id = f"needle_argmax_L{L}_{sample_idx}"
    sample = {
        "id": sample_id,
        "task": "needle_argmax",
        "length": L,
        "series": x.tolist(),
        "prompt": prompt,
        "target": str(needle_index),
        "meta": {
            "needle_index": needle_index,
            "needle_value": float(needle_value),
        },
    }
    return sample


# ============== 任务 2：needle_query_value ==============

def generate_uniform_series(
    L: int,
    value_range: Tuple[float, float] = (-1.0, 1.0),
) -> np.ndarray:
    """
    生成一个简单的随机序列：均匀分布 U(value_range[0], value_range[1])
    """
    return np.random.uniform(value_range[0], value_range[1], size=L)


def create_needle_query_value_sample(
    sample_idx: int,
    L: int,
) -> Dict[str, Any]:
    """
    任务：给定序列，问“t = k 时的数值是多少？（保留两位小数）”

    target: "{value:.2f}"，比如 "-0.37"
    评估时会对数值差异设定容忍度（比如 0.05 以内视为正确）。
    """
    x = generate_uniform_series(L)
    # 随机选择一个查询位置 k（1..L）
    k = np.random.randint(1, L + 1)
    true_value = float(x[k - 1])

    series_text = series_to_text_notimestamp(x)
    target_str = f"{true_value:.2f}"

    prompt = f"""下面是一段长度为 {L} 的单变量时间序列（单位为任意数值），从上到下按顺序给出了这一段时间内连续观测到的数值：

    {series_text}

    问题：假设从上到下依次编号为第 1 个、第 2 个、...、第 {L} 个。请给出**第 {k} 个**数值的大小，并四舍五入保留两位小数。

    请严格按照以下格式作答（不要输出其它内容）：
    Answer: <数值>
    例如：Answer: -0.37
    """


    sample_id = f"needle_query_value_L{L}_{sample_idx}"
    sample = {
        "id": sample_id,
        "task": "needle_query_value",
        "length": L,
        "series": x.tolist(),
        "prompt": prompt,
        "target": target_str,
        "meta": {
            "query_index": k,
            "true_value": true_value,
        },
    }
    return sample


# ============== 主生成流程 ==============

TASK_GENERATORS = {
    "needle_argmax": create_needle_argmax_sample,
    "needle_query_value": create_needle_query_value_sample,
}


def generate_task2_datasets(
    out_dir: str,
    lengths: List[int],
    n_samples: int,
    seed: int = 42,
):
    os.makedirs(out_dir, exist_ok=True)
    set_random_seed(seed)

    for task_name, gen_fn in TASK_GENERATORS.items():
        for L in lengths:
            out_path = os.path.join(out_dir, f"{task_name}_L{L}.jsonl")
            print(f"[INFO] Generating {task_name}, L={L}, n_samples={n_samples} -> {out_path}")
            with open(out_path, "w", encoding="utf-8") as f:
                for i in range(n_samples):
                    sample = gen_fn(sample_idx=i, L=L)
                    f.write(json.dumps(sample, ensure_ascii=False) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic time-series datasets for Task 2 (needle-in-a-haystack)."
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        required=True,
        help="输出 JSONL 数据集目录",
    )
    parser.add_argument(
        "--lengths",
        type=int,
        nargs="+",
        default=[64, 128, 256, 512, 1024, 2048],
        help="要生成的时间序列长度列表",
    )
    parser.add_argument(
        "--n_samples",
        type=int,
        default=500,
        help="每个任务 × 每个长度的样本数",
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
    generate_task2_datasets(
        out_dir=args.out_dir,
        lengths=args.lengths,
        n_samples=args.n_samples,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
