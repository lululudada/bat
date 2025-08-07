import time
import random
import json
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def save_cookies(driver, filename):
    """保存当前会话的cookies到文件"""
    cookies = driver.get_cookies()
    with open(filename, 'w') as f:
        json.dump(cookies, f)
    print(f"Cookies已保存至 {filename}")

def load_cookies(driver, filename):
    """从文件加载cookies到当前会话"""
    if not os.path.exists(filename):
        return False
        
    with open(filename, 'r') as f:
        cookies = json.load(f)
    
    driver.get("https://www.pinterest.com/")
    
    for cookie in cookies:
        if 'domain' in cookie and cookie['domain'] in ['.pinterest.com', 'pinterest.com']:
            try:
                driver.add_cookie(cookie)
            except:
                continue
    
    return True

def extract_all_image_urls(driver):
    """提取页面中所有图片的真实URL（包括.jfif格式）"""
    image_urls = set()
    
    # 方法1: 从图片元素中提取
    img_elements = driver.find_elements(By.TAG_NAME, 'img')
    for img in img_elements:
        src = img.get_attribute('src')
        if src and src.startswith('http') and any(ext in src for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.jfif']):
            # 移除尺寸参数以获取原始图片
            if '/originals/' in src:
                image_urls.add(src)
            elif re.search(r'/\d+x/', src):
                # 尝试获取原始尺寸
                original_src = re.sub(r'/\d+x/', '/originals/', src)
                image_urls.add(original_src)
            else:
                image_urls.add(src)
    
    # 方法2: 从CSS背景图中提取
    elements = driver.find_elements(By.XPATH, "//*[contains(@style, 'background-image')]")
    for element in elements:
        style = element.get_attribute('style')
        if 'url(' in style:
            match = re.search(r'url\(["\']?(https?://[^"\'\)]+)["\']?\)', style)
            if match:
                url = match.group(1)
                if any(ext in url for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.jfif']):
                    # 移除尺寸参数
                    if '/originals/' in url:
                        image_urls.add(url)
                    elif re.search(r'/\d+x/', url):
                        original_url = re.sub(r'/\d+x/', '/originals/', url)
                        image_urls.add(original_url)
                    else:
                        image_urls.add(url)
    
    # 方法3: 从图片容器中提取数据
    pin_containers = driver.find_elements(By.XPATH, "//div[@data-test-id='pin']")
    for container in pin_containers:
        try:
            # Pinterest 图片数据存储在 img 标签或 div 背景中
            img = container.find_element(By.TAG_NAME, 'img')
            src = img.get_attribute('src')
            if src and src.startswith('http'):
                # 尝试获取最高质量版本
                if '/originals/' in src:
                    image_urls.add(src)
                elif re.search(r'/\d+x/', src):
                    original_src = re.sub(r'/\d+x/', '/originals/', src)
                    image_urls.add(original_src)
                else:
                    image_urls.add(src)
        except:
            continue
    
    return list(image_urls)

def get_pinterest_images(search_term, scroll_count=5, cookies_file="pinterest_cookies.json"):
    """
    获取Pinterest图片下载链接（支持所有格式）
    :param search_term: 搜索关键词
    :param scroll_count: 页面滚动次数
    :param cookies_file: cookies存储文件名
    :return: 图片下载链接列表
    """
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-images")  # 禁用图片加载加速
    
    # 初始化WebDriver
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    all_image_urls = set()
    
    try:
        # 尝试加载cookies
        if os.path.exists(cookies_file):
            driver.get("https://www.pinterest.com/")
            load_cookies(driver, cookies_file)
            time.sleep(2)
            driver.refresh()
            time.sleep(3)
        
        # 如果cookies无效或不存在，提示用户手动登录
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-test-id='header-avatar']"))
            )
        except:
            print("未登录或cookies失效，请手动登录...")
            driver.get("https://www.pinterest.com/login/")
            input("登录完成后按回车继续...")
            save_cookies(driver, cookies_file)
        
        # 访问搜索页面
        print(f"搜索: {search_term}...")
        driver.get(f"https://pinterest.com/search/pins/?q={search_term}")
        
        # 等待页面加载
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-test-id='pin']"))
        )
        time.sleep(3)
        
        # 滚动页面指定次数
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(scroll_count):
            print(f"滚动 {i+1}/{scroll_count}...")
            
            # 滚动到底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.5, 3.0))
            
            # 提取当前视图中的所有图片URL
            current_image_urls = extract_all_image_urls(driver)
            all_image_urls.update(current_image_urls)
            print(f"已收集 {len(all_image_urls)} 个图片链接")
            
            # 检查是否到达页面底部
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("已到达页面底部，停止滚动")
                break
            last_height = new_height
        
        # 最终提取所有图片链接
        final_image_urls = extract_all_image_urls(driver)
        all_image_urls.update(final_image_urls)
        
        # 过滤掉缩略图
        filtered_urls = set()
        for url in all_image_urls:
            if not any(size in url for size in ['75x75', '140x', '236x', '280x']):
                filtered_urls.add(url)
        
        print(f"共获取 {len(filtered_urls)} 个高质量图片链接")
        return list(filtered_urls)
    
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return []
    
    finally:
        driver.quit()

if __name__ == "__main__":
    # 用户输入
    search_query = input("请输入搜索关键词: ").strip()
    scroll_times = int(input("请输入滚动次数(3-10): ").strip())
    
    # 获取图片链接
    print("\n开始采集图片链接...")
    start_time = time.time()
    image_links = get_pinterest_images(search_query, scroll_times)
    
    # 打印结果
    print(f"\n获取到 {len(image_links)} 个图片链接 (耗时 {time.time()-start_time:.1f}秒):")
    
    # 按格式分类统计
    format_count = {
        '.jfif': 0,
        '.jpg': 0,
        '.jpeg': 0,
        '.png': 0,
        '.webp': 0,
        '.gif': 0,
        '其他': 0
    }
    
    for link in image_links:
        if '.jfif' in link:
            format_count['.jfif'] += 1
        elif '.jpg' in link:
            format_count['.jpg'] += 1
        elif '.jpeg' in link:
            format_count['.jpeg'] += 1
        elif '.png' in link:
            format_count['.png'] += 1
        elif '.webp' in link:
            format_count['.webp'] += 1
        elif '.gif' in link:
            format_count['.gif'] += 1
        else:
            format_count['其他'] += 1
    
    # 打印格式统计
    print("\n图片格式统计:")
    for fmt, count in format_count.items():
        if count > 0:
            print(f"{fmt}: {count}个")
    
    # 保存到文件
    if image_links:
        filename = f"pinterest_{search_query}_links.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(image_links))
        print(f"\n所有链接已保存至 {filename}")
        
        # 生成HTML预览文件
        html_filename = f"pinterest_{search_query}_preview.html"
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(f"<html><head><title>Pinterest {search_query} 图片预览</title></head><body>")
            f.write(f"<h1>Pinterest '{search_query}' 搜索结果 ({len(image_links)}张图片)</h1>")
            f.write(f"<p>格式统计: {', '.join([f'{k} {v}' for k, v in format_count.items() if v > 0])}</p>")
            f.write("<div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;'>")
            for i, url in enumerate(image_links[:100]):  # 最多显示前100张
                f.write(f"<div><img src='{url}' style='width: 100%; border: 1px solid #ddd;'><br><a href='{url}' target='_blank'>{url[-30:]}</a></div>")
            f.write("</div></body></html>")
        print(f"预览文件已保存至 {html_filename}")
    else:
        print("未获取到图片链接，请检查关键词或尝试增加滚动次数")