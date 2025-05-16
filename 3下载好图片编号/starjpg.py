import os
import pandas as pd
import requests
from tqdm import tqdm
import re

def download_images_from_excel(
    excel_path,
    target_column="主图（URL）地址",
    save_folder="downloaded_images",
    timeout=15,
    max_retries=3
):
    """从单个Excel文件下载指定列的图片"""
    
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
            return

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
            return

        print(f"找到 {len(urls)} 个唯一URL")

        # 下载配置
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # 下载图片
        success_count = 0
        for url in tqdm(urls, desc="下载进度"):
            for retry in range(max_retries):
                try:
                    if not re.match(r'^https?://', url):
                        break

                    response = session.get(url, stream=True, timeout=timeout)
                    response.raise_for_status()

                    # 获取文件扩展名
                    ext = (
                        '.jpg' if 'jpeg' in response.headers.get('Content-Type', '') else
                        '.png' if 'png' in response.headers.get('Content-Type', '') else
                        '.gif' if 'gif' in response.headers.get('Content-Type', '') else
                        '.webp' if 'webp' in response.headers.get('Content-Type', '') else
                        os.path.splitext(url)[1] or '.jpg'
                    )

                    # 生成文件名
                    filename = os.path.basename(url).split('?')[0] or f"image_{success_count+1}{ext}"
                    if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        filename = f"{os.path.splitext(filename)[0]}{ext}"

                    save_path = os.path.join(save_folder, filename)
                    
                    # 处理重名文件
                    counter = 1
                    while os.path.exists(save_path):
                        name, ext = os.path.splitext(filename)
                        save_path = os.path.join(save_folder, f"{name}_{counter}{ext}")
                        counter += 1

                    # 保存文件
                    with open(save_path, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)

                    success_count += 1
                    break

                except Exception as e:
                    if retry == max_retries - 1:
                        print(f"\n下载失败: {url[:60]}... - {type(e).__name__}")
                    continue

        print(f"✅ 成功下载: {success_count}/{len(urls)}")

    except Exception as e:
        print(f"❌ 处理失败: {type(e).__name__}: {str(e)}")

def batch_process_folder(
    folder_path=None,
    target_column="主图（URL）地址",
    output_subfolder="下载的图片"
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

    # 处理每个文件
    total_success = 0
    total_urls = 0
    for file in excel_files:
        file_path = os.path.join(folder_path, file)
        # 为每个文件创建单独的子文件夹
        file_save_folder = os.path.join(
            output_folder, 
            os.path.splitext(file)[0]  # 使用文件名作为子文件夹名
        )
        download_images_from_excel(
            excel_path=file_path,
            target_column=target_column,
            save_folder=file_save_folder,
            timeout=15,
            max_retries=3
        )

    print(f"\n{'='*50}")
    print(f"🎉 批量处理完成！")
    print(f"📁 输出目录: {output_folder}")
    print(f"{'='*50}")

if __name__ == "__main__":
    # 直接运行即可处理当前文件夹
    batch_process_folder()