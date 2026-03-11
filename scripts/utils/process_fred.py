import json
import re
from typing import Dict, Any, List, Tuple


TS_KEY_PATTERN = re.compile(r"^timeseries\d+$")


def get_timeseries_keys(obj: Dict[str, Any]) -> List[str]:
    """Return sorted timeseries keys: timeseries1, timeseries2, ..."""
    keys = [k for k in obj.keys() if TS_KEY_PATTERN.match(k)]
    keys.sort(key=lambda x: int(re.findall(r"\d+", x)[0]))
    return keys


def lengths_for_sample(obj: Dict[str, Any], ts_keys: List[str]) -> List[Tuple[str, int]]:
    lens = []
    if "timestamp" in obj and isinstance(obj["timestamp"], list):
        lens.append(("timestamp", len(obj["timestamp"])))
    else:
        lens.append(("timestamp", -1))

    for k in ts_keys:
        if isinstance(obj.get(k), list):
            lens.append((k, len(obj[k])))
        else:
            lens.append((k, -1))
    return lens


def trim_to_length(obj: Dict[str, Any], ts_keys: List[str], target_len: int) -> Dict[str, Any]:
    """Trim timestamp and all timeseries keys to target_len from the end."""
    obj["timestamp"] = obj["timestamp"][:target_len]
    for k in ts_keys:
        obj[k] = obj[k][:target_len]
    return obj


def process_jsonl(
    in_path: str,
    out_path: str,
    max_gap: int = 20,
    drop_if_missing: bool = True,
    drop_if_cols_mismatch: bool = True,
) -> None:
    """
    Fix length mismatches in a jsonl dataset.

    Rules:
      1. 自动识别 timeseries*
      2. 如果 cols 数量 != timeseries 数量 -> drop（可选）
      3. 如果存在非 list / 缺失 -> drop
      4. 如果 max_len - min_len <= max_gap -> 裁切到 min_len
      5. 否则 drop
    """
    total = 0
    kept = 0
    trimmed = 0
    dropped = 0

    dropped_examples = []
    trimmed_examples = []

    with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                dropped += 1
                if len(dropped_examples) < 5:
                    dropped_examples.append(
                        {"line_no": line_no, "reason": "json_decode_error"}
                    )
                continue

            ts_keys = get_timeseries_keys(obj)

            if not ts_keys:
                dropped += 1
                if len(dropped_examples) < 5:
                    dropped_examples.append(
                        {"index": obj.get("index"), "reason": "no_timeseries_keys"}
                    )
                continue

            # === 新增规则：cols 数量必须与 timeseries 数量一致 ===
            if drop_if_cols_mismatch:
                cols = obj.get("cols")
                if not isinstance(cols, list) or len(cols) != len(ts_keys):
                    dropped += 1
                    if len(dropped_examples) < 5:
                        dropped_examples.append(
                            {
                                "index": obj.get("index"),
                                "reason": "cols_timeseries_mismatch",
                                "cols_len": len(cols) if isinstance(cols, list) else None,
                                "timeseries_len": len(ts_keys),
                            }
                        )
                    continue

            lens = lengths_for_sample(obj, ts_keys)

            invalid = [(k, l) for k, l in lens if l < 0]
            if invalid and drop_if_missing:
                dropped += 1
                if len(dropped_examples) < 5:
                    dropped_examples.append(
                        {
                            "index": obj.get("index"),
                            "reason": "missing_or_nonlist",
                            "invalid": invalid,
                        }
                    )
                continue

            valid_lens = [l for _, l in lens if l >= 0]
            min_len = min(valid_lens)
            max_len = max(valid_lens)
            gap = max_len - min_len

            if gap > max_gap:
                dropped += 1
                if len(dropped_examples) < 5:
                    dropped_examples.append(
                        {
                            "index": obj.get("index"),
                            "reason": "gap_too_large",
                            "lengths": lens,
                            "gap": gap,
                        }
                    )
                continue

            if gap > 0:
                obj = trim_to_length(obj, ts_keys, min_len)
                trimmed += 1
                if len(trimmed_examples) < 5:
                    trimmed_examples.append(
                        {
                            "index": obj.get("index"),
                            "target_len": min_len,
                            "gap": gap,
                        }
                    )

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            kept += 1

    print("=== Processing Finished ===")
    print(f"Input file : {in_path}")
    print(f"Output file: {out_path}")
    print(f"Total      : {total}")
    print(f"Kept       : {kept}")
    print(f"Trimmed    : {trimmed}")
    print(f"Dropped    : {dropped}")

    if trimmed_examples:
        print("\n--- Trimmed examples (up to 5) ---")
        for ex in trimmed_examples:
            print(ex)

    if dropped_examples:
        print("\n--- Dropped examples (up to 5) ---")
        for ex in dropped_examples:
            print(ex)

if __name__ == "__main__":
    # 改成你的真实路径
    input_jsonl = "/cluster/home/user1/hulining/TSDataset/TSandLanguage/data/fred_blog_full_index.jsonl"
    output_jsonl = "./dataset/fred_blog.jsonl"

    process_jsonl(
        in_path=input_jsonl,
        out_path=output_jsonl,
        max_gap=20,
        drop_if_missing=True,
        drop_if_cols_mismatch=True
    )
