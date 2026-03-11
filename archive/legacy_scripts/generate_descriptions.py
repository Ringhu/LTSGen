
#Usage
# python generate_etth1_descriptions.py --csv_path /path/to/ETTh1.csv --output_path etth1_descriptions.jsonl

import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_etth1(csv_path: str) -> pd.DataFrame:
    """
    读取 ETTh1 数据集，返回以 datetime 为索引、按标准列顺序排列的 DataFrame。
    期望列名：date, HUFL, HULL, MUFL, MULL, LUFL, LULL, OT
    """
    df = pd.read_csv(csv_path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    feature_cols = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
    # 有些文件可能已经去掉 date 这一列，这里做个兼容：
    available_cols = [c for c in feature_cols if c in df.columns]
    df = df[available_cols]
    return df


def sliding_window_indices(n: int, window: int, step: int):
    """生成滑动窗口的起始下标。"""
    i = 0
    while i + window <= n:
        yield i
        i += step


def classify_global_trend(x: np.ndarray):
    """
    用简单线性回归 + 归一化斜率，判断整体趋势类型。
    返回 (label, slope_norm)
    label ∈ {'strong_up', 'weak_up', 'flat', 'weak_down', 'strong_down'}
    """
    L = len(x)
    t = np.arange(L, dtype=float)
    # 防止全常数的情况
    if np.allclose(x, x[0]):
        return "flat", 0.0
    coef = np.polyfit(t, x, 1)
    slope = coef[0]
    # 归一化：把整个窗口的线性变化幅度 / (max-min)，得到一个大致的“相对变化比例”
    x_min, x_max = float(x.min()), float(x.max())
    denom = (x_max - x_min) if x_max != x_min else max(abs(x_min), 1.0)
    slope_norm = (slope * L) / denom
    # 阈值可以按经验微调
    if slope_norm >= 0.3:
        label = "strong_up"
    elif slope_norm >= 0.1:
        label = "weak_up"
    elif slope_norm <= -0.3:
        label = "strong_down"
    elif slope_norm <= -0.1:
        label = "weak_down"
    else:
        label = "flat"
    return label, float(slope_norm)


def classify_volatility(std: float, mean: float, eps: float = 1e-6):
    """
    根据 相对波动率 = std / (|mean| + eps) 粗略划分波动等级。
    返回 (level, rel_value)，level ∈ {'low','medium','high'}
    """
    rel = std / (abs(mean) + eps)
    if rel < 0.05:
        lvl = "low"
    elif rel < 0.15:
        lvl = "medium"
    else:
        lvl = "high"
    return lvl, float(rel)


def estimate_period(x: np.ndarray, max_lag: int | None = None):
    """
    利用自相关估计主周期。
    返回 (best_lag, best_corr)，如果没有明显周期，best_lag 也可能较小、相关系数很低。
    """
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    n = len(x)
    if max_lag is None:
        max_lag = min(n // 2, 200)
    if max_lag < 2:
        return 0, 0.0
    # 自相关（未严格归一化形式，但后面会除以 acf[0]）
    acf_full = np.correlate(x, x, mode="full")
    acf = acf_full[n - 1 : n + max_lag]
    if acf[0] == 0:
        return 0, 0.0
    acf = acf / acf[0]
    # 忽略 lag=0
    acf[0] = 0.0
    lags = np.arange(0, max_lag + 1)
    best_lag = int(lags[np.argmax(acf)])
    best_corr = float(acf[best_lag])
    return best_lag, best_corr


def segment_features(x: np.ndarray, num_segments: int, global_std: float):
    """
    把序列均匀切成 num_segments 段，计算每段的均值/标准差/趋势等。
    返回一个 list，每个元素是字典：
    {
      'idx': k,
      'start': start,
      'end': end,   # inclusive
      'mean': ...,
      'std': ...,
      'vol_level': 'low'/'medium'/'high'（相对全局 std）,
      'trend_label': ...
    }
    """
    L = len(x)
    seg_len = L // num_segments
    segments = []
    start = 0
    for k in range(num_segments):
        end = (k + 1) * seg_len if k < num_segments - 1 else L
        seg = x[start:end]
        if len(seg) < 2:
            break
        seg_mean = float(seg.mean())
        seg_std = float(seg.std())
        # 相对全局 std
        if global_std <= 0:
            vol_level = "low"
        else:
            ratio = seg_std / global_std
            if ratio < 0.7:
                vol_level = "low"
            elif ratio < 1.3:
                vol_level = "medium"
            else:
                vol_level = "high"
        seg_trend_label, _ = classify_global_trend(seg)
        segments.append(
            {
                "idx": k,
                "start": int(start),
                "end": int(end - 1),
                "len": int(end - start),
                "mean": seg_mean,
                "std": seg_std,
                "vol_level": vol_level,
                "trend_label": seg_trend_label,
            }
        )
        start = end
    return segments


def detect_zscore_events(x: np.ndarray, z_thr: float = 2.5):
    """
    用简单 Z-score 检测“尖峰/极端值事件”，返回：
    events: list[dict]，每个 dict 包含 start/end/peak_idx/peak_value/z_max 等。
    """
    x = np.asarray(x, dtype=float)
    mu = x.mean()
    sigma = x.std()
    if sigma <= 0:
        return []
    z = (x - mu) / sigma
    idxs = np.where(np.abs(z) >= z_thr)[0]
    if len(idxs) == 0:
        return []
    events = []
    start = idxs[0]
    prev = idxs[0]
    for i in idxs[1:]:
        if i == prev + 1:
            prev = i
        else:
            events.append((start, prev))
            start = i
            prev = i
    events.append((start, prev))
    # 转成更丰富的结构
    event_dicts = []
    for (s, e) in events:
        seg = x[s : e + 1]
        seg_z = z[s : e + 1]
        peak_rel = int(np.argmax(np.abs(seg_z)))
        peak_idx = s + peak_rel
        event_dicts.append(
            {
                "start": int(s),
                "end": int(e),
                "peak_idx": int(peak_idx),
                "peak_value": float(x[peak_idx]),
                "z_max": float(seg_z[peak_rel]),
            }
        )
    # 按 |z_max| 从大到小排序
    event_dicts.sort(key=lambda d: abs(d["z_max"]), reverse=True)
    return event_dicts


def describe_window_etth1(win_df: pd.DataFrame) -> tuple[str, dict]:
    """
    对 ETTh1 的一个窗口（多变量，含 OT）生成中文描述和结构化特征。
    win_df: index 为时间戳，columns 至少包含 'OT' 及若干负载变量。
    返回: (description_text, features_dict)
    """
    assert "OT" in win_df.columns, "ETTh1 窗口必须包含 OT 列"
    target = win_df["OT"].to_numpy(dtype=float)
    L = len(target)
    t0 = win_df.index[0]
    t1 = win_df.index[-1]

    g_min, g_max = float(target.min()), float(target.max())
    g_mean = float(target.mean())
    g_std = float(target.std())
    vol_level, vol_ratio = classify_volatility(g_std, g_mean)
    trend_label, slope_norm = classify_global_trend(target)
    best_lag, best_corr = estimate_period(target)

    segments = segment_features(target, num_segments=4, global_std=g_std)
    events = detect_zscore_events(target, z_thr=2.5)

    # 多变量相关性：OT vs 其他
    corr_info = []
    if win_df.shape[1] > 1:
        corr_mat = win_df.corr()
        if "OT" in corr_mat.columns:
            corrs = corr_mat["OT"].drop(labels=["OT"])
            for var, rho in corrs.items():
                corr_info.append({"var": var, "rho": float(rho)})
            # 按绝对相关度排序
            corr_info.sort(key=lambda d: abs(d["rho"]), reverse=True)

    # ---------- 下面开始拼接中文描述（5 段式框架 + 多变量） ----------

    lines = []

    # 1) 整体范围 + 水平 + 全局波动
    line1 = (
        f"这段时间序列窗口覆盖的时间大约从 {t0} 到 {t1}，"
        f"长度约为 {L} 个时间点，OT 的数值整体分布在 {g_min:.1f} 到 {g_max:.1f} 之间，"
        f"平均水平大约在 {g_mean:.1f} 左右。"
    )
    if vol_level == "low":
        line1 += " 整体波动幅度较小，大部分时间围绕平均值附近小幅起伏。"
    elif vol_level == "medium":
        line1 += " 整体波动程度中等，既存在一定的上下波动，也不会过于剧烈。"
    else:
        line1 += " 整体波动较为剧烈，数值在高低水平之间频繁切换。"
    lines.append(line1)

    # 2) 全局趋势（全局走向）
    start_val, end_val = float(target[0]), float(target[-1])
    if trend_label == "strong_up":
        line2 = (
            f"从开头到结尾，OT 整体呈现比较明显的上升趋势，"
            f"起始时大约为 {start_val:.1f}，在窗口末尾上升到接近 {end_val:.1f}。"
        )
    elif trend_label == "weak_up":
        line2 = (
            f"从整体来看，OT 略有上升，"
            f"虽然中间存在一些波动，但末尾水平略高于开头（由约 {start_val:.1f} 变化到 {end_val:.1f} 左右）。"
        )
    elif trend_label == "strong_down":
        line2 = (
            f"在这一窗口中，OT 整体呈现较明显的下降趋势，"
            f"从开头的约 {start_val:.1f} 逐步降低到末尾的 {end_val:.1f} 左右。"
        )
    elif trend_label == "weak_down":
        line2 = (
            f"整体而言，OT 稍有回落，末尾水平略低于开头，"
            f"大致由 {start_val:.1f} 下降到 {end_val:.1f} 附近。"
        )
    else:
        line2 = (
            f"在这段时间内，OT 没有特别明显的单向上升或下降趋势，"
            f"更多是在某一较稳定水平附近上下波动。"
        )
    lines.append(line2)

    # 3) 周期性 / 重复模式
    if best_lag >= 4 and best_corr >= 0.6:
        line3 = (
            f"从自相关分析来看，OT 在这一窗口中存在较为明显的周期性波动，"
            f"大约每隔 {best_lag} 个时间点会出现一次相似的起伏模式（自相关系数约为 {best_corr:.2f}）。"
        )
    elif best_lag >= 4 and best_corr >= 0.3:
        line3 = (
            f"从自相关结果看，OT 在这一窗口内存在一定周期结构，"
            f"大致每隔 {best_lag} 个时间点会重复出现类似的形状（相关程度中等，自相关系数约为 {best_corr:.2f}）。"
        )
    else:
        line3 = (
            "在这一窗口内，OT 的波动模式相对不规则，没有特别显著的固定周期结构。"
        )
    lines.append(line3)

    # 4) 按阶段描述（前段 / 高波动段 / 末段）
    if segments:
        # 起始阶段
        seg0 = segments[0]
        descr0 = f"在序列的起始阶段（大约前 {seg0['len']} 个时间点），OT 主要围绕 {seg0['mean']:.1f} 波动"
        if seg0["trend_label"] in ("strong_up", "weak_up"):
            descr0 += "，整体略有上升"
        elif seg0["trend_label"] in ("strong_down", "weak_down"):
            descr0 += "，整体略有下降"
        else:
            descr0 += "，整体较为平稳"
        if seg0["vol_level"] == "high":
            descr0 += "，但局部波动相对较大。"
        elif seg0["vol_level"] == "medium":
            descr0 += "，波动程度中等。"
        else:
            descr0 += "，波动幅度较小。"
        lines.append(descr0)

        # 选一个“波动最大的阶段”
        seg_high = max(segments, key=lambda s: s["std"])
        if seg_high["idx"] not in (0, len(segments) - 1):
            descr_mid = (
                f"在中间阶段（约第 {seg_high['start']}–{seg_high['end']} 个时间点），"
                f"OT 的均值大约为 {seg_high['mean']:.1f}，"
            )
            if seg_high["trend_label"] in ("strong_up", "weak_up"):
                descr_mid += "并呈现一定上升趋势，"
            elif seg_high["trend_label"] in ("strong_down", "weak_down"):
                descr_mid += "并呈现一定下降趋势，"
            else:
                descr_mid += "整体水平变化不大，"
            if seg_high["vol_level"] == "high":
                descr_mid += "在这一段中波动最为剧烈，峰谷差明显增大。"
            elif seg_high["vol_level"] == "medium":
                descr_mid += "波动程度中等。"
            else:
                descr_mid += "波动相对较小。"
            lines.append(descr_mid)

        # 末段
        seg_last = segments[-1]
        descr_last = (
            f"到了序列的最后阶段（约第 {seg_last['start']}–{seg_last['end']} 个时间点），"
            f"OT 主要徘徊在 {seg_last['mean']:.1f} 附近"
        )
        if seg_last["trend_label"] in ("strong_up", "weak_up"):
            descr_last += "，在这一小段内仍有继续上升的趋势"
        elif seg_last["trend_label"] in ("strong_down", "weak_down"):
            descr_last += "，在这一小段内呈现回落趋势"
        else:
            descr_last += "，整体较为平稳"
        if seg_last["vol_level"] == "high":
            descr_last += "，但波动依然较大。"
        elif seg_last["vol_level"] == "medium":
            descr_last += "，波动程度适中。"
        else:
            descr_last += "，波动幅度不大。"
        lines.append(descr_last)

    # 5) 关键事件 / 局部异常
    if events:
        # 只挑最显著的前 2–3 个事件
        max_events = min(3, len(events))
        for i in range(max_events):
            ev = events[i]
            s, e, p = ev["start"], ev["end"], ev["peak_idx"]
            v = ev["peak_value"]
            z = ev["z_max"]
            # 简单判断是“突增”还是“突降”
            if z >= 0:
                ev_type = "向上异常（尖峰）"
            else:
                ev_type = "向下异常（跌落）"
            # 前后对比值
            prev_idx = max(0, s - 5)
            prev_mean = float(target[prev_idx:s].mean()) if s > 0 else g_mean
            delta = v - prev_mean
            line_ev = (
                f"在大约第 {s}–{e} 个时间点附近，OT 出现一次{ev_type}，"
                f"局部峰值约为 {v:.1f}，相较此前一小段时间（平均约 {prev_mean:.1f}）"
                f"{'明显升高' if delta >= 0 else '明显降低'}，"
                f"对应的标准化偏离（|z-score|）约为 {abs(z):.1f}。"
            )
            lines.append(line_ev)
    else:
        lines.append("在这一窗口内，没有检测到非常突出的极端尖峰或跌落事件，局部形态总体较为平滑。")

    # 6) 多变量之间的关系（针对 ETTh1 负载 vs OT）
    if corr_info:
        # 选出绝对相关度最高的 1–2 个变量
        strong_corrs = [c for c in corr_info if abs(c["rho"]) >= 0.5]
        if strong_corrs:
            strong_corrs = strong_corrs[:2]
            parts = []
            for c in strong_corrs:
                var, rho = c["var"], c["rho"]
                if rho >= 0:
                    part = (
                        f"当 {var} 较高时，OT 通常也偏高，两者呈现较强的正相关（相关系数约为 {rho:.2f}）"
                    )
                else:
                    part = (
                        f"当 {var} 升高时，OT 往往偏低，二者表现出一定程度的反向变化关系（相关系数约为 {rho:.2f}）"
                    )
                parts.append(part)
            line_corr = "从多变量角度来看，" + "；".join(parts) + "。"
            lines.append(line_corr)
        else:
            lines.append(
                "从这一窗口内的线性相关性来看，OT 与其他负载变量之间的相关程度中等，没有特别突出的强相关或强反向关系。"
            )

    description = "\n".join(lines)

    # 结构化特征，方便后续做 QA / LLM 改写
    features = {
        "global": {
            "length": L,
            "min": g_min,
            "max": g_max,
            "mean": g_mean,
            "std": g_std,
            "vol_level": vol_level,
            "vol_ratio": vol_ratio,
            "trend_label": trend_label,
            "slope_norm": slope_norm,
        },
        "periodicity": {
            "best_lag": best_lag,
            "best_corr": best_corr,
        },
        "segments": segments,
        "events": events,
        "correlations": corr_info,
    }

    return description, features


def generate_etth1_jsonl(
    csv_path: str,
    output_path: str,
    window_lengths=(512, 1024),
    step_ratio: float = 0.5,
    max_samples: int | None = None,
):
    """
    主函数：读取 etth1.csv，按给定窗口长度滑动切片，对每个窗口生成描述，
    并将样本以一行一个 JSON 的形式写入 output_path（JSONL 格式）。
    """
    df = load_etth1(csv_path)
    n = len(df)
    feature_names = list(df.columns)

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sample_count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for L in window_lengths:
            step = max(1, int(L * step_ratio))
            for start in sliding_window_indices(n, L, step):
                end = start + L
                win_df = df.iloc[start:end]
                desc, feat = describe_window_etth1(win_df)

                sample = {
                    "id": f"etth1_L{L}_start{start}",
                    "dataset": "ETTh1",
                    "task": "forecasting",
                    "window_length": L,
                    "start_index": int(start),
                    "end_index": int(end - 1),
                    "start_time": str(win_df.index[0]),
                    "end_time": str(win_df.index[-1]),
                    "time": [str(t) for t in win_df.index],
                    "feature_names": feature_names,
                    "values": win_df.to_numpy().tolist(),  # 形状 L x C
                    "features": feat,                      # 结构化特征
                    "descriptions": [desc],                # 目前每个窗口 1 条描述，你可以后续扩展多条
                }

                f.write(json.dumps(sample, ensure_ascii=False))
                f.write("\n")

                sample_count += 1
                if max_samples is not None and sample_count >= max_samples:
                    print(f"达到 max_samples={max_samples}，提前停止。")
                    return

    print(f"已生成 {sample_count} 个样本，保存在 {out_path}。")


if __name__ == "__main__":
    # 示例用法：
    #   python generate_etth1_descriptions.py --csv_path ETTh1.csv --output_path etth1_desc.jsonl
    import argparse

    parser = argparse.ArgumentParser(description="生成 ETTh1 长时间序列的中文文本描述（JSONL 格式）。")
    parser.add_argument("--csv_path", type=str, required=True, help="ETTh1.csv 的路径")
    parser.add_argument("--output_path", type=str, default="etth1_descriptions.jsonl", help="输出 jsonl 路径")
    parser.add_argument(
        "--window_lengths",
        type=int,
        nargs="+",
        default=[512, 1024],
        help="窗口长度列表，例如 512 1024",
    )
    parser.add_argument(
        "--step_ratio",
        type=float,
        default=0.5,
        help="滑动步长相对窗口长度的比例，默认 0.5 表示步长 = window_length*0.5",
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        default=None,
        help="最多生成多少个样本，默认不限制",
    )

    args = parser.parse_args()
    generate_etth1_jsonl(
        csv_path=args.csv_path,
        output_path=args.output_path,
        window_lengths=args.window_lengths,
        step_ratio=args.step_ratio,
        max_samples=args.max_samples,
    )
