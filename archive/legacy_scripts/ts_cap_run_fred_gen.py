import json
import logging
import sys
import os
import numpy as np
from tqdm import tqdm
import re # 记得在文件头部导入 re
# -----------------------------------------------------------------------------
# 1. 环境设置
# -----------------------------------------------------------------------------
sys.path.append(os.getcwd())

from ts_capv2.core.sample import generate_sample

# -----------------------------------------------------------------------------
# 2. 配置参数
# -----------------------------------------------------------------------------
INPUT_FILE = "/cluster/home/user1/hulining/TSDataset/LTSGen/dataset/fred_blog.jsonl"
OUTPUT_FILE = "./gen_tst_dataset/fred_captions.jsonl"

CAPTION_LANG = "zh"
WINDOW_MODE = "full" 

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("fred_combiner")

# -----------------------------------------------------------------------------
# 3. 辅助函数：清洗 FRED 冗余列名
# -----------------------------------------------------------------------------
def _clean_fred_name(raw_name: str) -> str:
    """
    终极版清洗逻辑：处理 FRED 复杂的计算指标命名。
    """
    # 1. 预处理：去掉常见的频率和单位后缀
    name = raw_name
    noise_patterns = [
        r",\s*(Monthly|Quarterly|Annual|Daily|Weekly)",
        r",\s*(Not )?Seasonally Adjusted",
        r",\s*Index \w+ \d{4}=\d+",
        r"Index \w+ \d{4}=\d+ of", 
        r",\s*Millions of Dollars",
        r",\s*Billions of Dollars",
        r",\s*Percent",
    ]
    for pat in noise_patterns:
        name = re.sub(pat, "", name, flags=re.IGNORECASE)

    # 2. 处理分号
    if ";" in name:
        parts = name.split(";")
        candidate = parts[1].strip()
        if len(candidate) > 4: 
            name = candidate
        else:
            name = parts[0].strip()

    # 3. 处理括号
    name = re.sub(r"\s*\(Index.*?\)", "", name) 
    
    # 4. 最后的清理
    name = name.strip()
    
    # [新增] 5. 去除尾部的介词 (of, in, at, for)
    # 很多 FRED 标题被截断后会留下 "Ratio of", "Assets in"
    name = re.sub(r"\s+(of|in|at|for|by)\s*$", "", name, flags=re.IGNORECASE)

    if len(name) < 3:
        name = raw_name.split(",")[0]
        
    return name
# -----------------------------------------------------------------------------
# 4. 核心处理逻辑
# -----------------------------------------------------------------------------
def process_fred_line(line_data, line_idx):
    # --- A. 解析基础数据 ---
    cols_names = line_data.get("cols", [])
    timestamps = line_data.get("timestamp", [])
    message = line_data.get("message", "")
    idx_key = str(line_data.get("index", line_idx))

    if not cols_names or not timestamps:
        return None

    # --- B. 构建数据矩阵 (T, D) ---
    series_data_cols = []
    for i, c_name in enumerate(cols_names):
        key = f"timeseries{i+1}"
        vals = line_data.get(key)
        if vals is None:
            vals = [0.0] * len(timestamps)
        try:
            vals = [float(v) if v is not None else 0.0 for v in vals]
        except ValueError:
            vals = [0.0] * len(timestamps)
        series_data_cols.append(vals)
    
    try:
        arr_t_d = np.array(series_data_cols, dtype=float).T
        values_list = arr_t_d.tolist()
    except Exception as e:
        logger.warning(f"Data shape mismatch at line {line_idx}: {e}")
        return None

    # --- C. 准备元数据 ---
    domain_context = {
        "dataset": "FRED",
        "original_analysis": message,
        "description": "Economic time series data."
    }
    
    # [关键修改]：构建 meta 时，分离 name (短) 和 meaning (长)
    variables_meta_base = []
    for i, raw_name in enumerate(cols_names):
        short_name = _clean_fred_name(raw_name)
        variables_meta_base.append({
            "name": short_name,       # <--- 用于行文，例如 "Assets in 529 Plans"
            "index": i,
            "meaning_zh": raw_name,   # <--- 保留全称作为解释
            "unit": None
        })

    # --- D. 循环生成 & 拼接 ---
    combined_parts = []

    for t_idx, target_meta in enumerate(variables_meta_base):
        target_name = target_meta["name"] # 使用短名作为 Key
        
        # 标记 role
        current_vars_meta = [v.copy() for v in variables_meta_base]
        for v in current_vars_meta:
            v["role"] = "target" if v["index"] == t_idx else "feature"

        rec = generate_sample(
            timestamps=timestamps,
            values=values_list,
            series_cols=[v["name"] for v in variables_meta_base], # 传递短名列表
            target_col=target_name,
            dataset_name="fred",
            task="analysis",
            series_key=f"fred_{idx_key}",
            indices=None,
            variables_meta=current_vars_meta,
            label=None,
            domain_context=domain_context,
            enforce_claims=True,
            caption_lang=CAPTION_LANG,
            llm_enabled=False,
            seed=None
        )
        
        base_cap = rec["caption_base"]
        part_text = f"【序列 {t_idx+1}：{target_name}】{base_cap}"
        combined_parts.append(part_text)

    final_combined_text = "\n".join(combined_parts)

    # --- E. 组装最终输出 Record ---
    final_record = {
        "dataset": "fred",
        "task": "analysis",
        "series_key": f"fred_{idx_key}",
        "window_length": len(timestamps),
        "indices": [0, len(timestamps)],
        "time": timestamps,
        "timeseries": values_list,
        "variables": variables_meta_base,
        "label": {"class": None},
        "descriptions": [final_combined_text],
        "domain_context": domain_context
    }
    
    return final_record

def main():
    logger.info(f"Reading input: {INPUT_FILE}")
    logger.info(f"Writing output: {OUTPUT_FILE}")
    
    if not os.path.exists(INPUT_FILE):
        logger.error("Input file not found!")
        return

    success_count = 0
    with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as fout:
        lines = fin.readlines()
        for i, line in tqdm(enumerate(lines), total=len(lines), desc="Processing"):
            line = line.strip()
            if not line: continue
            try:
                row_data = json.loads(line)
            except json.JSONDecodeError:
                continue
            result = process_fred_line(row_data, i)
            if result:
                fout.write(json.dumps(result, ensure_ascii=False) + "\n")
                success_count += 1

    logger.info(f"Done! Processed {success_count} records.")

if __name__ == "__main__":
    main()