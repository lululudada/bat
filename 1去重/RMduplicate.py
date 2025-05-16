import os
import pandas as pd
from tqdm import tqdm


def batch_deduplicate_excel(input_folder=None, output_folder=None, subset_column='产品名称'):
    """
    批量处理当前文件夹内所有Excel文件，按指定列去重
    
    参数:
        input_folder: 输入文件夹路径(默认当前文件夹)
        output_folder: 输出文件夹路径(默认当前文件夹下的'去重结果'文件夹)
        subset_column: 根据哪一列判断重复(默认'产品名称')
    """
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 设置默认路径
    if input_folder is None:
        input_folder = current_dir  # 默认当前文件夹作为输入
    
    if output_folder is None:
        output_folder = os.path.join(current_dir, '去重结果')  # 默认创建子文件夹
    
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)
    
    # 获取所有Excel文件（忽略已处理的输出文件）
    excel_files = [f for f in os.listdir(input_folder) 
                 if f.lower().endswith(('.xlsx', '.xls')) 
                 and not f.startswith('~$')]  # 忽略临时文件
    
    if not excel_files:
        print("⚠️ 当前文件夹未找到Excel文件！")
        return
    
    print(f"🔍 找到 {len(excel_files)} 个Excel文件：{', '.join(excel_files)}")
    
    # 带进度条处理
    success_count = 0
    for filename in tqdm(excel_files, desc="正在处理"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        
        try:
            # 1. 读取Excel文件
            df = pd.read_excel(input_path)
            

            
            # 2. 检查指定列是否存在
            if subset_column not in df.columns:
                tqdm.write(f"⚠️ 跳过 {filename}：未找到列 '{subset_column}'")
                continue
            
            # 3. 删除重复项
            before = len(df)
            df.drop_duplicates(
                subset=[subset_column],
                keep='first',
                inplace=True
            )
            after = len(df)
            removed = before - after

                        # 新增：删除前17列
            if len(df.columns) > 17:
                df.drop(df.columns[:17], axis=1, inplace=True)
                tqdm.write(f"🗑️ {filename}：已删除前17列")
            
            # 4. 保存结果
            df.to_excel(output_path, index=False)
            success_count += 1
            
            if removed > 0:
                tqdm.write(f"✔ {filename}：删除 {removed} 条重复数据")
            
        except Exception as e:
            tqdm.write(f"× 处理失败: {filename} - 错误类型: {type(e).__name__}, 详情: {str(e)}")
            continue
        
    
    # 打印总结报告
    print(f"\n{'='*40}")
    print(f"📊 处理完成！\n"
          f"✅ 成功处理: {success_count}/{len(excel_files)} 个文件\n"
          f"📂 输出位置: {os.path.abspath(output_folder)}")
    print(f"{'='*40}")

if __name__ == "__main__":
    # 使用示例（全部使用默认参数）
    batch_deduplicate_excel()  # 最简单的调用方式
    
    # 如果想按其他列去重（例如"订单号"）
    # batch_deduplicate_excel(subset_column="订单号")