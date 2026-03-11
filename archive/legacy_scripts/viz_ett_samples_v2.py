
import json
from pathlib import Path
import argparse
import textwrap

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 设置字体路径为 Noto Sans CJK 字体（根据实际路径修改）
FONT_PATH = "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc"  # 确保路径是正确的
cn_font = font_manager.FontProperties(fname=FONT_PATH)

# 配置 Matplotlib 使用该字体
matplotlib.rcParams["font.sans-serif"] = [cn_font.get_name()]  # 设置为 Noto Sans CJK
matplotlib.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

def load_sample_from_jsonl(jsonl_path: str, sample_index: int | None = None, sample_id: str | None = None):
    """
    从 JSONL 文件里读取一个样本。
    - 如果给出 sample_id，则按 id 精确匹配。
    - 否则用 sample_index（第几行，从 0 开始）。
    """
    jsonl_path = Path(jsonl_path)
    assert jsonl_path.exists(), f"{jsonl_path} 不存在"

    if sample_id is not None:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                if obj.get("id") == sample_id:
                    return obj
        raise ValueError(f"在 {jsonl_path} 中未找到 id={sample_id} 的样本")

    if sample_index is None:
        sample_index = 0

    with jsonl_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == sample_index:
                return json.loads(line)

    raise IndexError(f"sample_index={sample_index} 超出范围")


def sample_to_dataframe(sample: dict) -> pd.DataFrame:
    """
    将一个 sample 转成 pandas DataFrame，index 为时间戳，columns 为 feature_names。
    """
    times = pd.to_datetime(sample["time"])
    feature_names = sample["feature_names"]
    values = sample["values"]

    df = pd.DataFrame(values, columns=feature_names, index=times)
    return df


def plot_sample_with_description(
    sample: dict,
    feature: str = "OT",
    wrap_width: int = 32,
    show_events: bool = True,
):
    """
    在同一张图中：
    - 左侧子图：画出指定 feature 的时间序列（默认 OT）
    - 右侧子图：展示该窗口的中文描述（descriptions[0]）
    可选：在曲线上标出 z-score 检测到的异常事件区域。
    """
    df = sample_to_dataframe(sample)

    if feature not in df.columns:
        raise ValueError(f"feature '{feature}' 不在 sample['feature_names'] 中：{df.columns.tolist()}")

    desc_list = sample.get("descriptions", [])
    description = desc_list[0] if desc_list else "(样本中没有 descriptions 字段)"
    features_struct = sample.get("features", {})

    # 准备画布：左 2/3 画曲线，右 1/3 显示文本
    fig = plt.figure(figsize=(14, 6))
    gs = fig.add_gridspec(1, 3, width_ratios=[2.2, 2.2, 1.6])

    # ----- 左侧：时间序列 -----
    ax_ts = fig.add_subplot(gs[:, :2])
    ax_ts.plot(df.index, df[feature])
    ax_ts.set_title(f"{sample.get('id', '')}  |  {feature}", fontsize=12)
    ax_ts.set_xlabel("Time")
    ax_ts.set_ylabel(feature)
    ax_ts.grid(True, alpha=0.3)

    # 可选：标出异常事件（z-score）
    if show_events and "events" in features_struct:
        events = features_struct["events"]
        if events:
            times = df.index.to_list()
            for ev in events[:5]:  # 最多标前 5 个
                s = ev["start"]
                e = ev["end"]
                s = max(0, min(s, len(times) - 1))
                e = max(0, min(e, len(times) - 1))
                ax_ts.axvspan(times[s], times[e], alpha=0.15)

    # ----- 右侧：文本描述 -----
    ax_txt = fig.add_subplot(gs[:, 2])
    ax_txt.axis("off")

    wrapped_text = textwrap.fill(description, width=wrap_width)
    ax_txt.text(
        0.0,
        1.0,
        wrapped_text,
        ha="left",
        va="top",
        fontsize=10,
        wrap=True,
        fontproperties=cn_font,   # 这里指定字体
    )
    ax_txt.set_title("自动生成的中文描述", loc="left", fontsize=11)

    plt.tight_layout()
    plt.savefig('output_viz_v2.png')


def main():
    parser = argparse.ArgumentParser(
        description="可视化 ETTh1 描述样本：画出时间序列 + 中文描述，方便肉眼检查描述是否准确。"
    )
    parser.add_argument("--jsonl_path", type=str, required=True, help="生成的 JSONL 样本文件路径")
    parser.add_argument(
        "--sample_index",
        type=int,
        default=0,
        help="要可视化的样本行号（从 0 开始）。与 --sample_id 二选一，如果两者都给则优先 sample_id。",
    )
    parser.add_argument(
        "--sample_id",
        type=str,
        default=None,
        help="要可视化的样本 id，例如 etth1_L512_start0",
    )
    parser.add_argument(
        "--feature",
        type=str,
        default="OT",
        help="要绘制的特征名，默认 OT",
    )
    parser.add_argument(
        "--no_events",
        action="store_true",
        help="不在图中高亮 z-score 检测到的异常事件区域",
    )

    args = parser.parse_args()

    sample = load_sample_from_jsonl(
        jsonl_path=args.jsonl_path,
        sample_index=None if args.sample_id is not None else args.sample_index,
        sample_id=args.sample_id,
    )

    plot_sample_with_description(
        sample,
        feature=args.feature,
        show_events=not args.no_events,
    )


if __name__ == "__main__":
    main()
