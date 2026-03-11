#!/usr/bin/env python3
import csv
import sys

def read_first_n_rows(file_path, n, encoding="utf-8"):
    with open(file_path, "r", newline="", encoding=encoding) as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= n:      # 已经读了 n 行就退出
                break
            # 这里直接打印整行，你也可以用 join 处理格式
            print(",".join(row))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python preview_csv.py <csv文件路径> <行数n>")
        sys.exit(1)

    csv_path = sys.argv[1]
    n = int(sys.argv[2])
    read_first_n_rows(csv_path, n)
