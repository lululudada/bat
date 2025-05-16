import os
import pandas as pd
import requests
from tqdm import tqdm
import re
from PIL import Image  # 新增Pillow库用于图片处理

jpg = int(input("请输入起始编号： "))
print(f"你输入的编号起始为：LU {jpg}-2")
def process_and_save_image(image_data, save_path, target_size=(1350, 1800)):
    """处理图片到指定大小并保存为JPG格式"""
    try:
        img = Image.open(image_data)
        # 调整尺寸并保持比例（填充背景）
        img = img.resize(target_size, Image.LANCZOS)
        # 转换为RGB模式（兼容RGBA等格式）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(save_path, 'JPEG', quality=95)
        return True
    except Exception as e:
        print(f"\n图片处理失败: {str(e)}")
        return False

def download_images_from_excel(
    excel_path,
    target_column="主图（URL）地址",
    save_folder="downloaded_images",
    timeout=15,
    max_retries=3,
    start_index=1  # 新增起始序号参数
):
    """从单个Excel文件下载并处理图片"""
    
    print(f"\n处理文件: {os.path.basename(excel_path)}")
    os.makedirs(save_folder, exist_ok=True)

    try:
        df = pd.read_excel(excel_path, engine="openpyxl")
        
        # 检查目标列是否存在
        if target_column not in df.columns:
            available_columns = [col for col in df.columns if re.search(r'url|地址|链接|image|图片', col, re.I)]
            print(f"⚠️ 未找到列: '{target_column}'")
            if available_columns:
                print(f"🔍 检测到可能的目标列: {', '.join(available_columns)}")
            return 0  # 返回处理成功的数量

        # 提取并清理URL
        urls = (
            df[target_column]
            .astype(str)
            .str.strip()
            .replace(['nan', 'None', ''], pd.NA)
            .dropna()
            .unique()
            .tolist()
        )

        if not urls:
            print("⚠️ 目标列中没有有效的URL")
            return 0

        print(f"找到 {len(urls)} 个唯一URL")

        # 下载配置
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # 下载图片
        success_count = 0
        current_index = start_index  # 使用传入的起始序号
        
        for url in tqdm(urls, desc="下载进度"):
            for retry in range(max_retries):
                try:
                    if not re.match(r'^https?://', url):
                        break

                    response = session.get(url, stream=True, timeout=timeout)
                    response.raise_for_status()

                    # 生成标准化文件名 LU001-2.jpg 格式
                    file_number = str(current_index).zfill(4)
                    filename = f"LU{file_number}-2.jpg"
                    save_path = os.path.join(save_folder, filename)
                    
                    # 处理图片并保存
                    if process_and_save_image(response.raw, save_path):
                        success_count += 1
                        current_index += 1  # 序号递增
                    break

                except Exception as e:
                    if retry == max_retries - 1:
                        print(f"\n下载失败: {url[:60]}... - {type(e).__name__}")
                    continue

        print(f"✅ 成功下载并处理: {success_count}/{len(urls)}")
        return success_count  # 返回成功数量供累计

    except Exception as e:
        print(f"❌ 处理失败: {type(e).__name__}: {str(e)}")
        return 0

def batch_process_folder(
    folder_path=None,
    target_column="主图（URL）地址",
    output_subfolder="下载的图片",
    start_index=1  # 新增全局起始序号
):
    """批量处理文件夹中的所有Excel文件"""
    
    # 设置默认路径
    if folder_path is None:
        folder_path = os.path.dirname(os.path.abspath(__file__))
    
    output_folder = os.path.join(folder_path, output_subfolder)
    os.makedirs(output_folder, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"📂 正在扫描文件夹: {folder_path}")
    print(f"💾 输出目录: {output_folder}")
    print(f"🔍 目标列: '{target_column}'")
    print(f"🔢 起始序号: {start_index}")
    print(f"{'='*50}\n")

    # 获取所有Excel文件
    excel_files = [
        f for f in os.listdir(folder_path) 
        if f.lower().endswith(('.xlsx', '.xls'))
        and not f.startswith('~$')  # 忽略临时文件
    ]

    if not excel_files:
        print("⚠️ 文件夹中没有找到Excel文件！")
        return

    print(f"找到 {len(excel_files)} 个Excel文件:")
    for i, f in enumerate(excel_files, 1):
        print(f"{i}. {f}")

    # 处理每个文件（序号累计）
    total_success = 0
    current_index = start_index
    
    for file in excel_files:
        file_path = os.path.join(folder_path, file)
        file_save_folder = output_folder  # 现在统一输出到一个文件夹
        
        success = download_images_from_excel(
            excel_path=file_path,
            target_column=target_column,
            save_folder=file_save_folder,
            timeout=15,
            max_retries=3,
            start_index=current_index  # 传入当前序号
        )
        total_success += success
        current_index += success  # 累计序号

    print(f"\n{'='*50}")
    print(f"🎉 批量处理完成！")
    print(f"📊 总成功数量: {total_success}")
    print(f"📁 输出目录: {output_folder}")
    print(f"🔢 下一个起始序号: {current_index}")
    print(f"{'='*50}")

if __name__ == "__main__":
    # 新增Pillow到requirements
    requirements = """
    pandas>=1.3.0
    openpyxl>=3.0.0
    requests>=2.26.0
    tqdm>=4.62.0
    Pillow>=9.0.0  # 新增图片处理库
    """
    
    # 直接运行即可处理当前文件夹
    batch_process_folder(
        start_index=jpg  # ！！可以修改起始序号
    )