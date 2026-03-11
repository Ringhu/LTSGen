from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Merge per-dataset UCR train jsonl files")
    parser.add_argument("--input_dir", default="gen_tst_dataset/ucr/train_shards")
    parser.add_argument("--pattern", default="ucr_*_train.jsonl")
    parser.add_argument("--output", default="gen_tst_dataset/ucr/merged/ucr_train_merged.jsonl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    jsonl_files = sorted(glob.glob(str(input_dir / args.pattern)))
    if not jsonl_files:
        raise FileNotFoundError(f"No files matched: {input_dir / args.pattern}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fout:
        for file_path_str in jsonl_files:
            file_path = Path(file_path_str)
            dataset_name = file_path.name.replace("ucr_", "").replace("_train.jsonl", "")
            print(f"Merging {dataset_name}")

            with file_path.open("r", encoding="utf-8") as fin:
                for line in fin:
                    item = json.loads(line)
                    item["source_dataset"] = dataset_name
                    fout.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Merge completed: {output_path}")


if __name__ == "__main__":
    main()
