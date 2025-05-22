# -*- coding: utf-8 -*-
import concurrent.futures
import openpyxl
import requests
import base64
import logging
import threading
from openpyxl import load_workbook
from pathlib import Path
from requests.exceptions import Timeout

# 配置日志
# 修改为：
logging.basicConfig(
    filename=str(Path(__file__).parent / 'title_generation.log'),  # 关键修改点
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# 全局配置
CURRENT_DIR = Path(__file__).parent
EXCEL_PATH = CURRENT_DIR / "上架表模板MX_已处理.xlsx"
API_KEY = "sk-4BcnxDna9rNMGe5XqRnOHNlQdCEuZhhCvb2LwWUJR7f5iYaG"
BASE_URL = "https://xiaoai.plus/v1"
TIMEOUT = 35
MAX_WORKERS = 30  # 根据API承受能力调整（建议4-8）
LOCK = threading.Lock()  # 线程锁

def process_row(sheet, row):
    """处理单行任务的独立函数"""
    base_path = sheet.cell(row=row, column=1).value
    filename = sheet.cell(row=row, column=2).value
    
    # 跳过无效行和已处理项
    if not all([base_path, filename]) or sheet.cell(row=row, column=9).value:
        return None
    
    img_path = (CURRENT_DIR / base_path.strip() / filename.strip()).resolve()
    if not img_path.exists():
        logging.warning(f"Missing file: {img_path}")
        return (row, None)
    
    try:
        base64_image = base64.b64encode(img_path.read_bytes()).decode('utf-8')
        title = generate_title(base64_image)
        return (row, title.strip('"') if title else None)
    except Exception as e:
        logging.error(f"行处理失败：第{row}行 - {str(e)}")
        return (row, None)

def generate_title(image_base64):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "model": "gpt-4o",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "你是一个墨西哥跨境电商专家，请为这个T恤图片生成西班牙语商品标题，要求："
                        "1.【材质+克重】+【设计类型】+【核心元素】+【情感/功能卖点】+【场景/人群】 2.突出产品卖点 3.符合当地语言习惯 "
                        "4.长度不超过250字符 5.不要使用引号 6.必须包含180g棉质T恤 7.西班牙语"
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        }]
    }
    # ... 保持其他代码不变 ...
    try:
        response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=TIMEOUT)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"API请求失败：{str(e)}")
        return None

def main():
    print("🟢 多线程程序启动")
    if not EXCEL_PATH.exists():
        print(f"❌ 错误：文件 {EXCEL_PATH} 不存在")
        return

    wb = load_workbook(EXCEL_PATH)
    sheet = wb.active
    total_rows = sheet.max_row - 1  # 排除标题行
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        futures = {executor.submit(process_row, sheet, row): row for row in range(2, sheet.max_row + 1)}
        
        # 实时进度跟踪
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if not result:
                continue
            
            row, title = result
            if title:
                # 线程安全写入
                with LOCK:
                    sheet.cell(row=row, column=9).value = title
                    wb.save(EXCEL_PATH)  # 每次保存都写盘
                
                completed += 1
                print(f"✅ 进度：{completed}/{total_rows} | 第{row}行：{title[:30]}...")
            else:
                print(f"⚠️ 第{row}行处理失败")

    print("\n🎉 处理完成！建议人工检查结果")

if __name__ == "__main__":
    main()