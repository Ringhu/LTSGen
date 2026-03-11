import os

# ================= 配置区域 =================

# 1. 在这里指定你要扫描的文件夹路径 (支持绝对路径或相对路径)
#    如果要扫描当前脚本所在的文件夹，请保持为空字符串: ""
#    Windows 示例: r"D:\Projects\MyPythonProject" (建议前面加 r 防止转义)
#    Mac/Linux 示例: "/Users/name/code/project"
SOURCE_DIR = r"/cluster/home/user1/hulining/TSDataset/LTSGen/tslm" 

# 2. 输出文件的名字
OUTPUT_FILE = "all_project_code.txt"

# 3. 需要扫描的文件后缀
TARGET_EXT = ".py"

# 4. 需要忽略的目录 (防止合并无关代码)
IGNORE_DIRS = {
    '.git', '__pycache__', 'venv', 'env', 
    '.idea', '.vscode', 'node_modules', 
    'build', 'dist', 'migrations', 'src'
}

# ===========================================

def merge_files(source_dir):
    # 如果用户没填路径，默认使用当前脚本所在目录
    if not source_dir:
        source_dir = os.getcwd()
    
    # 检查路径是否存在
    if not os.path.exists(source_dir):
        print(f"❌ 错误：找不到路径 -> {source_dir}")
        return

    # 确定输出文件的完整路径（保存到脚本运行目录下，而不是源目录下，防止污染源目录）
    output_path = os.path.join(os.getcwd(), OUTPUT_FILE)
    
    current_script = os.path.basename(__file__)
    total_files = 0
    
    print(f"📂 正在扫描目录: {os.path.abspath(source_dir)}")
    print(f"📝 目标输出文件: {output_path}\n")

    try:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            # os.walk 递归遍历
            for root, dirs, files in os.walk(source_dir):
                # 过滤掉不需要的目录
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                
                for file in files:
                    # 检查后缀，且防止合并脚本自己（如果脚本放在源目录里的话）
                    if file.endswith(TARGET_EXT) and file != current_script:
                        file_path = os.path.join(root, file)
                        # 计算相对路径，让 LLM 知道文件的层级结构
                        rel_path = os.path.relpath(file_path, source_dir)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as infile:
                                content = infile.read()
                                
                                # === 写入分隔符和文件路径 ===
                                outfile.write(f"\n{'='*50}\n")
                                outfile.write(f"File: {rel_path}\n")
                                outfile.write(f"{'='*50}\n\n")
                                
                                outfile.write(content)
                                outfile.write("\n")
                                
                                print(f"  -> 已合并: {rel_path}")
                                total_files += 1
                        except Exception as e:
                            print(f"  ⚠️ 跳过文件 {rel_path}: {e}")
                            
    except IOError as e:
         print(f"❌ 无法创建输出文件: {e}")

    if total_files > 0:
        print(f"\n✅ 完成！共合并 {total_files} 个文件。")
        print(f"👉 结果已保存为: {output_path}")
    else:
        print("\n⚠️ 未找到任何符合条件的 .py 文件。")

if __name__ == "__main__":
    merge_files(SOURCE_DIR)