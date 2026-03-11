import json
import numpy as np
from tqdm import tqdm
import math

def transpose_timeseries(ts_data):
    """
    将 (Time, Variables) 形状转换为 (Variables, Time)
    例如: [[1, 2], [3, 4]] -> [[1, 3], [2, 4]]
    """
    if not ts_data:
        return []
    try:
        # 使用 zip(*iter) 进行转置
        return list(map(list, zip(*ts_data)))
    except Exception:
        return []

def get_fingerprint(ts_data, num_points=10, precision=4):
    """
    生成时间序列的指纹，用于快速哈希查找。
    取第一个变量的前 num_points 个点，保留 precision 位小数。
    ts_data 必须是 (Variables, Time) 格式。
    """
    if not ts_data or not ts_data[0]:
        return None
    
    # 取第一个变量序列
    first_series = ts_data[0]
    # 取前 N 个点（如果不够 N 个就取全部）
    sample_points = first_series[:num_points]
    
    # 转为 tuple 并保留精度，作为 dict key
    return tuple(round(x, precision) for x in sample_points)

def is_match(ts1, ts2, rtol=1e-05, atol=1e-08):
    """
    严格对比两个时间序列是否一致。
    ts1, ts2 均为 (Variables, Time) 格式。
    """
    # 1. 检查变量数量
    if len(ts1) != len(ts2):
        return False
    # 2. 检查时间步长 (取第一个变量检查)
    if len(ts1[0]) != len(ts2[0]):
        return False
    
    # 3. 使用 numpy 进行数值比对 (处理浮点数精度问题)
    try:
        # 将列表转换为 numpy array
        arr1 = np.array(ts1)
        arr2 = np.array(ts2)
        return np.allclose(arr1, arr2, rtol=rtol, atol=atol)
    except Exception:
        return False

def merge_datasets(caption_file, qa_file, output_file):
    print("正在加载 Caption 数据并构建索引...")
    
    # --- 1. 构建 Caption 数据的查找表 ---
    # Key: 指纹 (第一个变量的前几个点)
    # Value: list of caption_entries (解决哈希冲突)
    caption_lookup = {}
    
    with open(caption_file, 'r', encoding='utf-8') as f:
        for line in tqdm(f):
            try:
                entry = json.loads(line)
                raw_ts = entry.get("timeseries", [])
                
                # 重要：Caption 数据的 timeseries 是 (Time, Variables)，需要转置为 (Variables, Time)
                transposed_ts = transpose_timeseries(raw_ts)
                
                # 生成指纹
                fingerprint = get_fingerprint(transposed_ts)
                if fingerprint:
                    if fingerprint not in caption_lookup:
                        caption_lookup[fingerprint] = []
                    # 存储 转置后的数据 和 原始entry，方便后续比对和提取
                    caption_lookup[fingerprint].append({
                        "transposed_ts": transposed_ts,
                        "captions": entry.get("descriptions", []) # 注意这里提取 descriptions
                    })
            except json.JSONDecodeError:
                continue

    print(f"索引构建完成，共 {len(caption_lookup)} 个唯一指纹组。开始匹配 QA 数据...")

    # --- 2. 遍历 QA 数据进行匹配 ---
    matched_count = 0
    total_count = 0
    
    with open(qa_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in tqdm(f_in):
            total_count += 1
            try:
                qa_entry = json.loads(line)
                qa_ts = qa_entry.get("timeseries", [])
                
                # QA 数据已经是 (Variables, Time)，不需要转置
                
                # 1. 计算 QA 数据的指纹
                fingerprint = get_fingerprint(qa_ts)
                
                found_captions = None
                
                # 2. 快速查找
                if fingerprint in caption_lookup:
                    candidates = caption_lookup[fingerprint]
                    
                    # 3. 详细比对 (解决指纹碰撞或确认精度)
                    for cand in candidates:
                        if is_match(qa_ts, cand["transposed_ts"]):
                            found_captions = cand["captions"]
                            break
                
                # 4. 如果匹配成功，注入 captions 字段
                if found_captions:
                    qa_entry["captions"] = found_captions
                    matched_count += 1
                else:
                    # 如果没匹配上，可以保留原样或标记，这里选择保留原样但 captions 为空或不加
                    # qa_entry["captions"] = [] 
                    pass
                
                # 写入结果
                f_out.write(json.dumps(qa_entry, ensure_ascii=False) + "\n")
                
            except json.JSONDecodeError:
                continue

    print(f"\n处理完成！")
    print(f"总 QA 样本数: {total_count}")
    print(f"成功匹配数: {matched_count}")
    print(f"匹配率: {matched_count/total_count:.2%}")
    print(f"结果已保存至: {output_file}")

# --- 使用示例 ---
# 请将下面的路径替换为你实际的文件路径
if __name__ == "__main__":
    CAPTION_FILE = "/cluster/home/user1/hulining/TSDataset/LTSGen/gen_tst_dataset/fred_captions.jsonl"  # 你的 caption 样本文件
    QA_FILE = "/cluster/home/user1/hulining/TSDataset/TSandLanguage/data/FREDTS/fred_blog_QA_HHHHHH.jsonl"            # 你的原始问答样本文件
    OUTPUT_FILE = "/cluster/home/user1/hulining/TSDataset/LTSGen/gen_tst_dataset/merge_fred_qa_with_captions.jsonl" # 输出文件
    
    merge_datasets(CAPTION_FILE, QA_FILE, OUTPUT_FILE)