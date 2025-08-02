import pandas as pd
import numpy as np
from openpyxl import load_workbook
import os
import glob

def find_template_file():
    """在当前目录中查找包含'Bulk_Upload_Template'的Excel文件"""
    possible_files = glob.glob('*Bulk_Upload_Template*.xlsx')
    if not possible_files:
        raise FileNotFoundError("未找到包含'Bulk_Upload_Template'的Excel文件")
    return possible_files[0]  # 返回找到的第一个匹配文件

def process_bulk_upload_template():
    # 查找模板文件
    input_file_path = find_template_file()
    print(f"找到模板文件: {input_file_path}")
    
    # 加载Excel文件
    wb = load_workbook(input_file_path)
    
    # 获取Template工作表
    if 'Template' not in wb.sheetnames:
        raise ValueError("Excel文件中缺少'Template'工作表")
    
    template_sheet = wb['Template']
    
    # 读取所有行
    all_rows = list(template_sheet.iter_rows(values_only=True))
    
    # 提取前两行（标题行）
    header_rows = all_rows[:2]
    
    # 数据行（从第3行开始）
    data_rows = all_rows[2:]
    
    # 创建DataFrame
    columns = [cell for cell in header_rows[0]]
    df = pd.DataFrame(data_rows, columns=columns)
    
    # 添加原始行索引
    df['original_index'] = range(len(df))
    
    # 按Goods ID分组（每个组算一个货品）
    grouped = df.groupby('Goods ID')
    
    # 计算货品总数
    total_products = len(grouped)
    print(f"总货品数量: {total_products}")
    
    # 计算需要拆分的文件数量
    num_files = (total_products + 1999) // 2000  # 向上取整
    print(f"需要拆分成 {num_files} 个文件")
    
    # 获取原始工作簿的所有工作表（除了Template）
    other_sheets = {}
    for sheet_name in wb.sheetnames:
        if sheet_name != 'Template':
            other_sheets[sheet_name] = wb[sheet_name]
    
    # 处理每个文件
    for file_num in range(1, num_files + 1):
        # 创建新工作簿
        output_wb = load_workbook(input_file_path)
        
        # 删除所有工作表
        for sheet_name in output_wb.sheetnames:
            del output_wb[sheet_name]
        
        # 添加原始工作表（除了Template）
        for sheet_name, sheet in other_sheets.items():
            new_sheet = output_wb.create_sheet(title=sheet_name)
            # 复制原始工作表中的所有单元格
            for row in sheet.iter_rows():
                for cell in row:
                    new_sheet[cell.coordinate].value = cell.value
        
        # 计算当前文件的货品范围
        start_idx = (file_num - 1) * 2000
        end_idx = min(file_num * 2000, total_products)
        
        # 获取当前批次的货品ID
        product_ids = list(grouped.groups.keys())[start_idx:end_idx]
        
        # 创建新的Template工作表
        ws = output_wb.create_sheet(title='Template')
        
        # 添加标题行
        for r_idx, row in enumerate(header_rows, 1):
            for c_idx, value in enumerate(row, 1):
                ws.cell(row=r_idx, column=c_idx, value=value)
        
        # 添加数据行
        row_counter = len(header_rows) + 1
        for pid in product_ids:
            group = grouped.get_group(pid)
            # 按原始行索引排序以保持原始顺序
            group = group.sort_values('original_index')
            for _, row in group.iterrows():
                for c_idx, col in enumerate(columns, 1):
                    ws.cell(row=row_counter, column=c_idx, value=row[col])
                row_counter += 1
        
        # 保存为新文件
        output_path = os.path.splitext(input_file_path)[0] + f"_已处理_{file_num}.xlsx"
        output_wb.save(output_path)
        print(f"已创建文件: {output_path}")
    
    return f"共创建了 {num_files} 个文件"

# 使用示例
if __name__ == "__main__":
    try:
        result = process_bulk_upload_template()
        print(result)
        print("按Enter键退出...")
        input()  # 等待用户按Enter键
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        print("按Enter键退出...")
        input()  # 等待用户按Enter键