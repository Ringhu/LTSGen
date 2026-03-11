import os
import json
import argparse
import re
from collections import defaultdict

def parse_filename(fname):
    """
    解析类似：
    best_linear_correlation_L1024_pred.jsonl
    long_up_run_L512_failed.jsonl
    返回: (task_name, L, status) 或 (None, None, None)
    """
    m = re.match(r"(.+)_L(\d+)_(pred|failed)\.jsonl$", fname)
    if not m:
        return None, None, None
    task = m.group(1)
    L = int(m.group(2))
    status = m.group(3)
    return task, L, status


def iter_jsonl(path):
    """逐行读取 jsonl，返回 (obj, line_no)"""
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line), i
            except json.JSONDecodeError:
                print(f"[WARN] JSON 解析失败: {path}:{i}")
                continue


def main(root_dir: str):
    # 每个文件的统计
    per_file_stats = {}

    # 所有文件合计
    total_stats = {
        "samples": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }

    # 按 (task, L) 聚合
    # key: (task, L)，value: stats dict
    by_task_len = defaultdict(lambda: {
        "samples": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    })

    files = sorted([f for f in os.listdir(root_dir) if f.endswith(".jsonl")])

    if not files:
        print(f"[INFO] 目录 {root_dir} 下没有找到 .jsonl 文件")
        return

    for fname in files:
        fpath = os.path.join(root_dir, fname)

        file_stats = {
            "samples": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        task, L, status = parse_filename(fname)

        for obj, ln in iter_jsonl(fpath):
            file_stats["samples"] += 1
            total_stats["samples"] += 1

            # 兼容 "token_usage" 或 "usage" 两种 key
            usage = obj.get("token_usage") or obj.get("usage") or {}

            pt = usage.get("prompt_tokens", 0)
            ct = usage.get("completion_tokens", 0)
            tt = usage.get("total_tokens", pt + ct)

            file_stats["prompt_tokens"] += pt
            file_stats["completion_tokens"] += ct
            file_stats["total_tokens"] += tt

            total_stats["prompt_tokens"] += pt
            total_stats["completion_tokens"] += ct
            total_stats["total_tokens"] += tt

            # 如果文件名能解析出 (task, L)，也统计一份
            if task is not None and L is not None:
                agg = by_task_len[(task, L)]
                agg["samples"] += 1
                agg["prompt_tokens"] += pt
                agg["completion_tokens"] += ct
                agg["total_tokens"] += tt

        per_file_stats[fname] = file_stats

    # ========= 打印每个文件的 usage =========
    print("==== 每个文件的 token usage ====")
    header = f"{'file':50} {'n':>6} {'prompt':>12} {'completion':>12} {'total':>12} {'avg_total':>12}"
    print(header)
    print("-" * len(header))

    for fname in sorted(per_file_stats.keys()):
        st = per_file_stats[fname]
        n = st["samples"]
        pt = st["prompt_tokens"]
        ct = st["completion_tokens"]
        tt = st["total_tokens"]
        avg = tt / n if n > 0 else 0.0
        print(f"{fname:50} {n:6d} {pt:12d} {ct:12d} {tt:12d} {avg:12.1f}")

    # ========= 打印总 usage =========
    print("\n==== 所有文件合计的 token usage ====")
    n = total_stats["samples"]
    pt = total_stats["prompt_tokens"]
    ct = total_stats["completion_tokens"]
    tt = total_stats["total_tokens"]
    avg = tt / n if n > 0 else 0.0
    print(f"{'TOTAL':50} {n:6d} {pt:12d} {ct:12d} {tt:12d} {avg:12.1f}")

    # ========= 按 (task, L) 聚合 =========
    if by_task_len:
        print("\n==== 按 (task, L) 聚合的 token usage ====")
        header2 = f"{'task':35} {'L':>6} {'n':>6} {'prompt':>12} {'completion':>12} {'total':>12} {'avg_total':>12}"
        print(header2)
        print("-" * len(header2))

        for (task, L) in sorted(by_task_len.keys(), key=lambda x: (x[0], x[1])):
            st = by_task_len[(task, L)]
            n = st["samples"]
            pt = st["prompt_tokens"]
            ct = st["completion_tokens"]
            tt = st["total_tokens"]
            avg = tt / n if n > 0 else 0.0
            print(f"{task:35} {L:6d} {n:6d} {pt:12d} {ct:12d} {tt:12d} {avg:12.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="统计 answer jsonl 文件的 token usage")
    parser.add_argument(
        "-d", "--dir",
        type=str,
        default=".",
        help="存放 answer 文件的目录（默认当前目录）"
    )
    args = parser.parse_args()
    main(args.dir)
