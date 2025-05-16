import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 目标网页 URL
url = "http://ludada.vip"

# 本地保存图片的目录
save_dir = "downloaded_images"
os.makedirs(save_dir, exist_ok=True)  # 创建目录（如果不存在）

# 发送 HTTP 请求获取网页内容
response = requests.get(url)
response.raise_for_status()  # 检查请求是否成功

# 使用 BeautifulSoup 解析 HTML
soup = BeautifulSoup(response.text, 'html.parser')

# 查找所有 <img> 标签
img_tags = soup.find_all('img')

# 遍历并下载图片
for idx, img in enumerate(img_tags, start=1):
    img_url = img.get('src')  # 获取图片 URL
    if not img_url:
        continue  # 跳过无效的图片链接

    # 处理相对路径（如 /images/example.jpg）
    img_url = urljoin(url, img_url)

    try:
        # 下载图片
        img_data = requests.get(img_url, timeout=10).content
        # 提取文件名（如 example.jpg）
        img_name = os.path.basename(img_url) or f"image_{idx}.jpg"
        save_path = os.path.join(save_dir, img_name)

        # 保存图片到本地
        with open(save_path, 'wb') as f:
            f.write(img_data)
        print(f"✅ 下载成功: {img_name}")
    except Exception as e:
        print(f"❌ 下载失败: {img_url} - {e}")

print("🎉 图片爬取完成！")
