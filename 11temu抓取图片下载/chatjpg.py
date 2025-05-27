import os
import requests
from openpyxl import load_workbook
import concurrent.futures
from tqdm import tqdm

# 配置参数
EXCEL_FILE = "data.xlsx"  # 改为你的Excel文件名
SAVE_FOLDER = "downloaded_images"  # 保存图片的文件夹名
COLUMN_LETTER = "U"  # 要处理的列
START_ROW = 2  # 起始行
MAX_THREADS = 100  # 最大线程数

def download_image(url, save_path):
    """下载图片并保存到指定路径"""
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True, None
        return False, f"HTTP错误码: {response.status_code}"
    except Exception as e:
        return False, str(e)

def download_task(task):
    """处理单个下载任务"""
    url, filename = task
    success, error = download_image(url, filename)
    if success:
        tqdm.write(f"下载成功：{filename}")
    else:
        tqdm.write(f"下载失败：{url} - 错误：{error}")
    return success

# 创建保存目录
os.makedirs(SAVE_FOLDER, exist_ok=True)

# 加载Excel文件
wb = load_workbook(EXCEL_FILE)
ws = wb.active

# 收集下载任务
tasks = []
existing_files = set(os.listdir(SAVE_FOLDER))  # 已存在的文件

for row in ws.iter_rows(min_row=START_ROW, min_col=ord(COLUMN_LETTER) - 64):
    cell = row[0]
    if cell.value:
        urls = cell.value.strip().split('\n')
        if urls:
            first_url = urls[0].strip()
            if first_url:
                filename = os.path.basename(first_url.split('/')[-1])
                save_path = os.path.join(SAVE_FOLDER, filename)
                
                # 跳过已存在的文件
                if filename in existing_files:
                    print(f"文件已存在，跳过：{filename}")
                    continue
                
                # 避免重复添加相同文件名的任务
                if filename not in existing_files:
                    existing_files.add(filename)
                    tasks.append((first_url, save_path))

# 执行多线程下载
if tasks:
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(download_task, task) for task in tasks]
        with tqdm(total=len(futures), desc="下载进度", unit="file") as pbar:
            for future in concurrent.futures.as_completed(futures):
                future.result()
                pbar.update(1)
else:
    print("没有需要下载的文件")

print("全部任务处理完成！")