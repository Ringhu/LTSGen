# task_global_ts_data.py
# -*- coding: utf-8 -*-

"""
生成 4 个“全局时间序列分析”任务的数据：

2A: special_value_quantile
    - 单变量序列
    - 随机选一个点用 >>> <<< 标出
    - 问这个点在整段序列中是“明显偏大 / 中等 / 明显偏小”
    - target: "A" (高 25%), "B" (中间 50%), "C" (低 25%)

3A: long_up_run
    - 单变量序列（随机游走）
    - 问是否存在长度 >= K 的连续上升片段
    - target: "yes" / "no"

4A: threshold_event_order
    - 单变量序列（随机游走）
    - 两个阈值 T_high, T_low
    - 事件 A: 第一次 x > T_high
      事件 B: 第一次 x < T_low
    - 问哪个事件先发生（或都没发生）
    - target: "A" / "B" / "none"

5A: best_linear_correlation
    - 多变量序列：x1, x2, x3, y
    - 每个样本随机选一个 driver 变量 x_i，使 y = a * x_i + 噪声
    - 问：y 与哪个变量线性关系最强？
    - target: "A" (x1) / "B" (x2) / "C" (x3)

输出 jsonl，每行一个样本：
{
  "id": "...",
  "task": "<task_name>",
  "length": L,
  "series": ...,
  "prompt": "给模型的问题（含时间序列文本）",
  "target": "<标准答案>",
  "meta": {...}
}

用法示例：
python task_global_ts_data.py \
  --out_dir ./task_global_data \
  --lengths 64 128 256 512 1024 2048 \
  --n_samples 200 \
  --seed 42
"""

import os
import json
import argparse
from typing import Dict, Any, List

import numpy as np


# ========= 通用工具 =========

def set_random_seed(seed: int = 42):
    np.random.seed(seed)


def series_to_text(x: np.ndarray) -> str:
    """
    将单变量序列转换为纯数值文本，一行一个值。
    不出现 t=1, t=2 等索引信息。
    """
    return "\n".join(f"{v:.4f}" for v in x)


# ========= 任务 2A: special_value_quantile =========

def create_special_value_quantile_sample(
    sample_idx: int,
    L: int,
    low_q: float = 0.25,
    high_q: float = 0.75,
) -> Dict[str, Any]:
    """
    在长度为 L 的 N(0,1) 序列中随机选一个点加标记，
    判断该点在整段的分布中是：
      A: 明显偏大 (>= high_q 分位)
      B: 中等 (在 low_q ~ high_q 之间)
      C: 明显偏小 (<= low_q 分位)
    """
    x = np.random.normal(loc=0.0, scale=1.0, size=L)
    k = np.random.randint(0, L)  # 0-based index
    special_val = x[k]

    q_low = float(np.quantile(x, low_q))
    q_high = float(np.quantile(x, high_q))

    if special_val >= q_high:
        label = "A"
    elif special_val <= q_low:
        label = "C"
    else:
        label = "B"

    # 文本中用 >>> <<< 标记特殊点
    lines = []
    for i, v in enumerate(x):
        if i == k:
            lines.append(f">>> {v:.4f} <<<")
        else:
            lines.append(f"{v:.4f}")
    series_text = "\n".join(lines)

    prompt = f"""下面是一段长度为 {L} 的单变量时间序列，从上到下依次为连续观测到的数值，其中有一个数值用符号 “>>> <<<” 做了标记：

{series_text}

我们关注的是这个被标记的数值，相对于整段序列中所有数值的大小，大致处在什么水平？请在下面三种描述中选择最合适的一种：

A. 明显偏大（大致属于整个序列中最高的 25%）
B. 中等水平（大致属于中间的 50%）
C. 明显偏小（大致属于整个序列中最低的 25%）

请只回答一个字母，并严格按照以下格式作答（不要输出其它内容）：
Answer: A
或
Answer: B
或
Answer: C
"""

    sample_id = f"special_value_quantile_L{L}_{sample_idx}"
    return {
        "id": sample_id,
        "task": "special_value_quantile",
        "length": L,
        "series": x.tolist(),
        "prompt": prompt,
        "target": label,
        "meta": {
            "special_index_1based": k + 1,
            "special_value": float(special_val),
            "q_low": q_low,
            "q_high": q_high,
        },
    }


# ========= 任务 3A: long_up_run =========

def longest_up_run_length(x: np.ndarray) -> int:
    """
    计算 x 中连续上升 (x[t] > x[t-1]) 的最长长度（以“步数”为单位）。
    例如: x=[1,2,3,1] -> 上升 run 长度序列 [1,1] 最大为 2（2->3 是一段，3->1 不是）。
    这里我们返回连续上升的“步数长度”，对应 diff>0 的连续段长度的最大值。
    """
    if len(x) < 2:
        return 0
    diffs = np.diff(x)
    up_mask = diffs > 0

    max_run = 0
    cur_run = 0
    for flag in up_mask:
        if flag:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0
    return int(max_run)


def create_long_up_run_sample(
    sample_idx: int,
    L: int,
    sigma: float = 1.0,
    K: int = 5,
) -> Dict[str, Any]:
    """
    生成随机游走序列，问是否存在长度 >= K 的连续上升片段。
    - x[0] = 0
    - x[t] = x[t-1] + N(0, sigma^2)

    target: "yes" / "no"
    """
    x = np.zeros(L, dtype=float)
    for t in range(1, L):
        x[t] = x[t - 1] + np.random.normal(loc=0.0, scale=sigma)

    max_run = longest_up_run_length(x)
    label = "yes" if max_run >= K else "no"

    series_text = series_to_text(x)

    prompt = f"""下面是一段长度为 {L} 的单变量时间序列，从上到下依次为连续观测到的数值。

{series_text}
  
我们把相邻的两个数进行比较，如果后一个比前一个大，就记为“上升一步”。

在这整段时间里，我们关心是否存在一个“连续上升”的片段：也就是说，从某个位置开始，之后每一步都比前一步大，连续上升至少 {K} 步。

问题：在这段序列中，是否存在长度不少于 {K} 步的连续上升片段？

请只回答下面两个单词之一，并严格按照以下格式作答（不要输出其它内容）：
Answer: yes
或
Answer: no
"""

    sample_id = f"long_up_run_L{L}_{sample_idx}"
    return {
        "id": sample_id,
        "task": "long_up_run",
        "length": L,
        "series": x.tolist(),
        "prompt": prompt,
        "target": label,
        "meta": {
            "max_up_run_length": max_run,
            "K": K,
        },
    }


# ========= 任务 4A: threshold_event_order =========

def create_threshold_event_order_sample(
    sample_idx: int,
    L: int,
    sigma: float = 1.0,
    T_high: float = 1.0,
    T_low: float = -1.0,
) -> Dict[str, Any]:
    """
    随机游走 + 两个阈值：
    - 事件 A: 第一次 x > T_high
    - 事件 B: 第一次 x < T_low
    target:
      A: 事件 A 先发生（或只有 A 发生）
      B: 事件 B 先发生（或只有 B 发生）
      none: 两个事件都未发生
    """
    x = np.zeros(L, dtype=float)
    for t in range(1, L):
        x[t] = x[t - 1] + np.random.normal(loc=0.0, scale=sigma)

    t_high = None
    t_low = None
    for t in range(L):
        if t_high is None and x[t] > T_high:
            t_high = t
        if t_low is None and x[t] < T_low:
            t_low = t
        if t_high is not None and t_low is not None:
            break

    if t_high is None and t_low is None:
        label = "none"
    elif t_high is not None and (t_low is None or t_high < t_low):
        label = "A"
    elif t_low is not None and (t_high is None or t_low < t_high):
        label = "B"
    else:
        label = "none"  # 理论上不太会到这里

    series_text = series_to_text(x)

    prompt = f"""下面是一段长度为 {L} 的单变量时间序列，从上到下依次为连续观测到的数值。
    
{series_text}

我们关心它与两个固定阈值的关系：

- 阈值 H（较高的阈值），例如 {T_high:.1f}
- 阈值 L（较低的阈值），例如 {T_low:.1f}

定义两个事件：
- 事件 A：在某个时刻，数值第一次明显高于阈值 H（例如超过 {T_high:.1f}）
- 事件 B：在某个时刻，数值第一次明显低于阈值 L（例如低于 {T_low:.1f}）

问题：在这整段序列中，下面三种情况哪一种描述是正确的？

A. 事件 A 比事件 B 更早发生（或者只发生了事件 A）
B. 事件 B 比事件 A 更早发生（或者只发生了事件 B）
none. 这两个事件在整段序列中都没有发生

请只回答下面三种答案之一，并严格按照以下格式作答（不要输出其它内容）：
Answer: A
或
Answer: B
或
Answer: none
"""

    sample_id = f"threshold_event_order_L{L}_{sample_idx}"
    return {
        "id": sample_id,
        "task": "threshold_event_order",
        "length": L,
        "series": x.tolist(),
        "prompt": prompt,
        "target": label,
        "meta": {
            "T_high": T_high,
            "T_low": T_low,
            "t_high_index_1based": None if t_high is None else t_high + 1,
            "t_low_index_1based": None if t_low is None else t_low + 1,
        },
    }


# ========= 任务 5A: best_linear_correlation =========

def create_best_linear_correlation_sample(
    sample_idx: int,
    L: int,
    a: float = 2.0,
    noise_std: float = 0.5,
    max_resample: int = 5,
) -> Dict[str, Any]:
    """
    多变量线性相关任务：
    - x1, x2, x3 ~ N(0,1)
    - 随机选一个 driver ∈ {1,2,3}
    - y = a * x_driver + eps
    - 问：y 和哪个变量线性相关性最强？
      A: x1, B: x2, C: x3

    为了减少偶然情况下相关性顺序反转的可能，会检查一次相关系数，
    如果发现 argmax(|corr(y,x_i)|) != driver，则最多重新采样 max_resample 次。
    """
    for _ in range(max_resample):
        x1 = np.random.normal(loc=0.0, scale=1.0, size=L)
        x2 = np.random.normal(loc=0.0, scale=1.0, size=L)
        x3 = np.random.normal(loc=0.0, scale=1.0, size=L)

        driver = np.random.choice([1, 2, 3])
        driver = int(driver)  # ⭐ 关键：转成 Python int，避免 numpy.int64

        if driver == 1:
            y = a * x1 + np.random.normal(loc=0.0, scale=noise_std, size=L)
        elif driver == 2:
            y = a * x2 + np.random.normal(loc=0.0, scale=noise_std, size=L)
        else:
            y = a * x3 + np.random.normal(loc=0.0, scale=noise_std, size=L)

        def corr(u, v):
            c = np.corrcoef(u, v)
            return float(c[0, 1])  # 已经转成 Python float

        c1 = corr(y, x1)
        c2 = corr(y, x2)
        c3 = corr(y, x3)

        corrs = np.array([abs(c1), abs(c2), abs(c3)], dtype=float)
        argmax_idx = int(np.argmax(corrs)) + 1  # 1,2,3

        if argmax_idx == driver:
            break

    # 最终 label
    if driver == 1:
        label = "A"
    elif driver == 2:
        label = "B"
    else:
        label = "C"

    # 构造文本：每行 x1,x2,x3,y
    lines = []
    for t in range(L):
        lines.append(
            f"x1={x1[t]:.4f}, x2={x2[t]:.4f}, x3={x3[t]:.4f}, y={y[t]:.4f}"
        )
    series_text = "\n".join(lines)

    prompt = f"""下面是一段多变量时间序列，每一行表示同一时刻下的多组观测值，其中：
- x1, x2, x3 可以看作三个不同的输入特征
- y 可以看作一个结果变量

具体数据如下（从上到下是连续的时间）：

{series_text}

我们关心的是：在这整段时间内，y 与哪一个变量的数值变化关系最为紧密、最接近线性相关？

请从下面三个选项中选择一个你认为最合适的答案：
A. x1
B. x2
C. x3

请只回答一个字母，并严格按照以下格式作答（不要输出其它内容）：
Answer: A
或
Answer: B
或
Answer: C
"""

    sample_id = f"best_linear_correlation_L{L}_{sample_idx}"
    return {
        "id": sample_id,
        "task": "best_linear_correlation",
        "length": L,
        "series": {
            "x1": x1.tolist(),
            "x2": x2.tolist(),
            "x3": x3.tolist(),
            "y": y.tolist(),
        },
        "prompt": prompt,
        "target": label,
        "meta": {
            "driver": int(driver),          # 再保险也可以再 int 一次
            "corr_x1_y": float(c1),
            "corr_x2_y": float(c2),
            "corr_x3_y": float(c3),
        },
    }



# ========= 生成主流程 =========

TASK_CREATORS = {
    # "special_value_quantile": create_special_value_quantile_sample,
    "long_up_run": create_long_up_run_sample,
    "threshold_event_order": create_threshold_event_order_sample,
    # "best_linear_correlation": create_best_linear_correlation_sample,
}


def generate_all_tasks(
    out_dir: str,
    lengths: List[int],
    n_samples_per_task: int,
    seed: int = 42,
):
    os.makedirs(out_dir, exist_ok=True)
    set_random_seed(seed)

    for task_name, creator_fn in TASK_CREATORS.items():
        for L in lengths:
            out_path = os.path.join(out_dir, f"{task_name}_L{L}.jsonl")
            print(f"[INFO] Generating task={task_name}, L={L}, n={n_samples_per_task} -> {out_path}")
            count = 0
            with open(out_path, "w", encoding="utf-8") as f:
                while count < n_samples_per_task:
                    sample = creator_fn(count, L)
                    if sample is None:
                        continue
                    f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                    count += 1
            print(f"[INFO] Done: task={task_name}, L={L}, samples={count}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic datasets for global TS tasks (2A,3A,4A,5A)."
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
        help="时间序列长度列表",
    )
    parser.add_argument(
        "--n_samples",
        type=int,
        default=100,
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
    generate_all_tasks(
        out_dir=args.out_dir,
        lengths=args.lengths,
        n_samples_per_task=args.n_samples,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
