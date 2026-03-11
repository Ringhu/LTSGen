# ts_caption/cli.py

#Usage
#ETT
# python -m ts_caption.cli \
#   --dataset_type ett \
#   --csv_path /path/ETTh1.csv \
#   --dataset_name ETTh1 \
#   --task forecasting \
#   --output etth1_desc.jsonl \
#   --window_len 512 --stride 256 \
#   --target_col OT \
#   --series_cols OT,HUFL,MUFL
#
#通用 CSV（比如 weather）
# python -m ts_caption.cli \
#   --dataset_type generic_csv \
#   --time_col timestamp \
#   --csv_path /path/weather.csv \
#   --dataset_name weather \
#   --task forecasting \
#   --output weather_desc.jsonl \
#   --window_len 512 --stride 256 \
#   --target_col temp \
#   --series_cols temp,humidity,pressure

#异常检测
# python -m ts_caption.cli \
#   --dataset_type generic_csv \
#   --time_col time \
#   --csv_path /path/anom.csv \
#   --dataset_name anomset \
#   --task anomaly_detection \
#   --output anom_desc.jsonl \
#   --target_col value \
#   --series_cols value \
#   --label_col anomaly --label_mode any


from __future__ import annotations
import argparse
from typing import List, Optional

from ts_caption.datasets.ett import ETTAdapter
from ts_caption.datasets.generic_csv import GenericCSVAdapter
from ts_caption.datasets.weather import WeatherExampleAdapter
from ts_caption.pipeline.run import run_pipeline
from ts_caption.datasets.nab import NABAdapter

def parse_list(s: Optional[str]) -> Optional[List[str]]:
    if s is None or s.strip() == "":
        return None
    return [x.strip() for x in s.split(",") if x.strip()]

def main():
    p = argparse.ArgumentParser("ts_caption: dataset -> claims -> caption -> jsonl")

    p.add_argument("--dataset_type", type=str, required=True, help="ett / generic_csv / weather_example / nab")
    p.add_argument("--csv_path", type=str, required=True)
    p.add_argument("--dataset_name", type=str, required=True)
    p.add_argument("--task", type=str, default="forecasting")
    p.add_argument("--output", type=str, required=True)

    p.add_argument("--window_len", type=int, default=512)
    p.add_argument("--stride", type=int, default=256)
    p.add_argument("--max_windows", type=int, default=None)

    p.add_argument("--time_col", type=str, default=None, help="only for generic_csv")
    p.add_argument("--target_col", type=str, default=None)
    p.add_argument("--series_cols", type=str, default=None, help="comma separated, include target or not")

    p.add_argument("--label_col", type=str, default=None)
    p.add_argument("--label_mode", type=str, default="none", help="none/any/majority/first/constant")
    p.add_argument("--constant_class", type=str, default=None)

    p.add_argument("--no_enforce_claims", action="store_true")
    
    p.add_argument("--nab_windows_json", type=str, default=None, help="NAB labels/combined_windows.json path")


    p.add_argument(
        "--caption_style",
        type=str,
        default="human",
        choices=["human", "full"],
        help="human: 自然叙事不输出z/ρ/lag/strength/Δ%；full: 输出更统计化的版本"
    )

    args = p.parse_args()

    # choose adapter
    if args.dataset_type == "ett":
        adapter = ETTAdapter()
        time_col = adapter.time_col()
        default_target = adapter.default_target_col()
    elif args.dataset_type == "weather_example":
        adapter = WeatherExampleAdapter()
        time_col = adapter.time_col()
        default_target = adapter.default_target_col()
    elif args.dataset_type == "generic_csv":
        if not args.time_col:
            raise ValueError("--time_col is required for generic_csv")
        adapter = GenericCSVAdapter(time_col=args.time_col, default_target=args.target_col or "target")
        time_col = adapter.time_col()
        default_target = adapter.default_target_col()
    elif args.dataset_type == "nab":
        if not args.nab_windows_json:
            raise ValueError("--nab_windows_json is required for nab")
        adapter = NABAdapter(windows_json_path=args.nab_windows_json)
        time_col = adapter.time_col()
        default_target = adapter.default_target_col()
    else:
        raise ValueError(f"Unknown dataset_type={args.dataset_type}")

    target_col = args.target_col or default_target
    cols = parse_list(args.series_cols)
    if cols is None:
        cols = [target_col]
    else:
        # ensure target first
        if target_col not in cols:
            cols = [target_col] + cols
        else:
            cols = [target_col] + [c for c in cols if c != target_col]

    run_pipeline(
        adapter=adapter,
        csv_path=args.csv_path,
        output_jsonl=args.output,
        dataset_name=args.dataset_name,
        task=args.task,
        window_len=args.window_len,
        stride=args.stride,
        target_col=target_col,
        series_cols=cols,
        max_windows=args.max_windows,
        label_col=args.label_col,
        label_mode=args.label_mode,
        constant_class=args.constant_class,
        enforce_claims=(not args.no_enforce_claims),
        caption_style=args.caption_style
    )

if __name__ == "__main__":
    main()
