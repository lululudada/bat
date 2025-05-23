import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

def download_taobao_images(url, save_folder='taobao_images'):
    """
    下载淘宝商品页面的图片到当前目录下的指定文件夹
    
    参数:
        url (str): 淘宝商品页面的URL
        save_folder (str): 保存图片的文件夹名称（默认在当前目录下创建）
    """
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(current_dir, save_folder)
    
    # 创建保存图片的文件夹
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        print(f"已创建图片保存目录: {save_path}")
    
    # 设置请求头，模拟浏览器访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.taobao.com/'
    }
    
    try:
        # 发送HTTP请求
        print(f"正在访问: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # 解析HTML内容
        soup = BeautifulSoup(response.text, 'html.parser')
        image_count = 0
        
        # 下载主图
        main_image = soup.find(id='J_ImgBooth')
        if main_image and main_image.get('src'):
            image_url = main_image['src']
            if not image_url.startswith('http'):
                image_url = 'https:' + image_url
            if download_image(image_url, save_path, headers):
                image_count += 1
        
        # 下载详情图片
        desc_div = soup.find(class_='desc')
        if desc_div:
            for img in desc_div.find_all('img'):
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    if not img_url.startswith('http'):
                        img_url = 'https:' + img_url
                    if download_image(img_url, save_path, headers):
                        image_count += 1
        
        print(f"\n图片下载完成！共下载 {image_count} 张图片")
        print(f"图片保存位置: {save_path}")
        
        # 尝试自动打开文件夹（仅Windows）
        try:
            if os.name == 'nt':
                os.startfile(save_path)
        except:
            pass
        
    except Exception as e:
        print(f"发生错误: {e}")

def download_image(url, save_path, headers):
    """下载单个图片并保存"""
    try:
        # 获取图片文件名
        filename = url.split('/')[-1]
        # 移除可能存在的查询参数
        filename = re.sub(r'\?.*$', '', filename)
        full_path = os.path.join(save_path, filename)
        
        # 如果文件已存在则跳过
        if os.path.exists(full_path):
            print(f"文件已存在，跳过: {filename}")
            return False
        
        # 下载图片
        print(f"正在下载: {filename}")
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        # 保存图片
        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return False

if __name__ == '__main__':
    # 用户输入淘宝商品URL
    taobao_url = input("请输入淘宝商品链接: ").strip()
    
    # 检查URL有效性
    if not taobao_url.startswith(('http://', 'https://')):
        print("错误：请输入有效的URL（以http://或https://开头）")
    else:
        download_taobao_images(taobao_url)