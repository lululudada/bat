import os
import hashlib

def compute_hash(file_path):
    """计算文件的哈希指纹（SHA-256更安全）"""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def wait_for_enter():

    input("按回车键继续...")

print("确认删除")

wait_for_enter()

def remove_duplicates():
    # 配置参数
    target_folder = "待筛选照片"  # 用户需要操作的文件夹
    safe_mode = False           # 安全模式默认开启（仅显示不删除）
    os.makedirs(target_folder, exist_ok=True)
    
    # 收集文件信息
    files = []
    for filename in os.listdir(target_folder):
        path = os.path.join(target_folder, filename)
        if os.path.isfile(path) and path.lower().endswith( ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp', '.jfif') ):
            files.append(path)
    
    # 通过哈希识别重复项
    hash_dict = {}
    duplicates = set()
    for filepath in files:
        try:
            file_hash = compute_hash(filepath)
            if file_hash in hash_dict:
                duplicates.add(filepath)
                # 记录最早出现的文件作为保留文件
                hash_dict[file_hash].append(filepath) 
            else:
                hash_dict[file_hash] = [filepath]
        except Exception as e:
            print(f"跳过无法读取的文件: {filepath} - {str(e)}")
    
    # 处理重复文件
    duplicate_count = 0
    for file_list in hash_dict.values():
        if len(file_list) > 1:
            # 保留第一个文件，标记后续为重复
            for dup_file in file_list[1:]:
                if safe_mode:
                    print(f"[安全模式] 将删除：{os.path.basename(dup_file)}")
                    duplicate_count += 1
                else:
                    try:
                        os.remove(dup_file)
                        print(f"已删除重复文件：{os.path.basename(dup_file)}")
                        duplicate_count += 1
                    except Exception as e:
                        print(f"删除失败：{dup_file} - {str(e)}")
    
    print("\n操作报告：")
    print(f"扫描文件总数：{len(files)}")
    print(f"发现重复文件：{duplicate_count}")
    
    if safe_mode:
        print("\n安全模式已启用（未执行实际删除）")
        print("如需实际删除，请修改代码设置 safe_mode = False")

if __name__ == "__main__":
    remove_duplicates()