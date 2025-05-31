import time
import random
import json
import os
import re
import logging
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pinterest_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('pinterest_scraper')

def save_cookies(driver, filename):
    """保存当前会话的cookies到文件"""
    try:
        cookies = driver.get_cookies()
        with open(filename, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"Cookies已保存至 {filename}")
    except Exception as e:
        logger.error(f"保存cookies时出错: {str(e)}")

def load_cookies(driver, filename):
    """从文件加载cookies到当前会话"""
    if not os.path.exists(filename):
        logger.warning(f"Cookies文件 {filename} 不存在")
        return False
        
    try:
        with open(filename, 'r') as f:
            cookies = json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Cookies文件 {filename} 格式错误，将删除并重新创建")
        os.remove(filename)
        return False
    
    # 清除现有cookies
    driver.delete_all_cookies()
    
    # 添加新cookies
    for cookie in cookies:
        try:
            # 修复域名格式
            if 'domain' in cookie and cookie['domain'].startswith('.'):
                cookie['domain'] = cookie['domain'][1:]
            driver.add_cookie(cookie)
        except Exception as e:
            logger.debug(f"添加cookie时出错: {str(e)}")
    
    logger.info(f"已从 {filename} 加载cookies")
    return True

def extract_all_image_urls(driver):
    """提取页面中所有图片的真实URL（包括.jfif格式）"""
    image_urls = set()
    
    # 方法1: 从所有图片元素中提取
    img_elements = driver.find_elements(By.TAG_NAME, 'img')
    for img in img_elements:
        try:
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
                    
                # 尝试获取data-src属性
                data_src = img.get_attribute('data-src')
                if data_src and data_src.startswith('http'):
                    if '/originals/' in data_src:
                        image_urls.add(data_src)
                    elif re.search(r'/\d+x/', data_src):
                        original_data_src = re.sub(r'/\d+x/', '/originals/', data_src)
                        image_urls.add(original_data_src)
                    else:
                        image_urls.add(data_src)
        except:
            continue
    
    # 方法2: 从CSS背景图中提取
    elements = driver.find_elements(By.XPATH, "//*[contains(@style, 'background-image')]")
    for element in elements:
        try:
            style = element.get_attribute('style')
            if 'url(' in style:
                match = re.search(r'url\(["\']?(https?://[^"\'\)]+)["\']?\)', style)
                if match:
                    url = match.group(1)
                    # 尝试获取最高质量版本
                    if '/originals/' in url:
                        image_urls.add(url)
                    elif re.search(r'/\d+x/', url):
                        original_url = re.sub(r'/\d+x/', '/originals/', url)
                        image_urls.add(original_url)
                    else:
                        image_urls.add(url)
        except:
            continue
    
    # 方法3: 从图片容器中提取数据
    pin_containers = driver.find_elements(By.XPATH, "//div[contains(@class, 'PinCard') or contains(@class, 'pinCard')]")
    for container in pin_containers:
        try:
            # 尝试从data属性获取
            data_json = container.get_attribute('data-test-pin-id')
            if data_json:
                try:
                    data = json.loads(data_json)
                    if 'images' in data and 'orig' in data['images']:
                        image_urls.add(data['images']['orig']['url'])
                    elif 'images' in data and 'originals' in data['images']:
                        image_urls.add(data['images']['originals']['url'])
                except:
                    pass
        except:
            continue
    
    # 方法4: 从相关推荐区域提取
    try:
        related_section = driver.find_element(By.XPATH, "//div[contains(@data-test-id, 'related-pins')]")
        related_imgs = related_section.find_elements(By.TAG_NAME, 'img')
        for img in related_imgs:
            try:
                src = img.get_attribute('src')
                if src and src.startswith('http'):
                    if '/originals/' in src:
                        image_urls.add(src)
                    elif re.search(r'/\d+x/', src):
                        original_src = re.sub(r'/\d+x/', '/originals/', src)
                        image_urls.add(original_src)
                    else:
                        image_urls.add(src)
            except:
                continue
    except:
        pass
    
    # 方法5: 从详情页提取
    try:
        detail_container = driver.find_element(By.XPATH, "//div[@data-test-id='pin-detail-image']")
        img = detail_container.find_element(By.TAG_NAME, 'img')
        src = img.get_attribute('src')
        if src and src.startswith('http'):
            if '/originals/' in src:
                image_urls.add(src)
            elif re.search(r'/\d+x/', src):
                original_src = re.sub(r'/\d+x/', '/originals/', src)
                image_urls.add(original_src)
            else:
                image_urls.add(src)
    except:
        pass
    
    return list(image_urls)

def get_chrome_driver():
    """创建并返回Chrome WebDriver"""
    # 配置Chrome选项 - 减少日志和错误
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    chrome_options.add_argument("--disable-site-isolation-trials")
    
    # 设置用户代理
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    # 初始化WebDriver
    service = Service()
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_pinterest_page(url, scroll_count=5, cookies_file="pinterest_cookies.json"):
    """
    抓取指定Pinterest页面上的所有图片链接
    :param url: Pinterest页面URL
    :param scroll_count: 页面滚动次数
    :param cookies_file: cookies存储文件名
    :return: 图片下载链接列表
    """
    driver = get_chrome_driver()
    all_image_urls = set()
    
    try:
        # 尝试加载cookies
        cookies_loaded = False
        if os.path.exists(cookies_file):
            logger.info("尝试加载cookies...")
            driver.get("https://www.pinterest.com/")
            time.sleep(2)
            cookies_loaded = load_cookies(driver, cookies_file)
            time.sleep(2)
            
            # 刷新页面检查登录状态
            driver.refresh()
            time.sleep(3)
            
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@data-test-id='header-avatar']"))
                )
                logger.info("✓ Cookies加载成功，已保持登录状态")
                cookies_loaded = True
            except:
                logger.warning("× Cookies无效或已过期")
                cookies_loaded = False
        
        # 如果cookies无效或不存在，提示用户手动登录
        if not cookies_loaded:
            logger.info("\n请手动登录Pinterest账号...")
            logger.info("登录完成后，请回到此窗口按回车键继续")
            driver.get("https://www.pinterest.com/login/")
            
            # 等待用户手动登录
            input("按回车键继续...")
            
            # 保存cookies供下次使用
            save_cookies(driver, cookies_file)
        
        # 访问目标页面
        logger.info(f"正在访问页面: {url}")
        driver.get(url)
        
        # 等待页面加载
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'PinCard') or contains(@class, 'pinCard')]"))
            )
        except:
            logger.warning("页面加载超时，尝试继续执行...")
        
        time.sleep(3)
        
        # 滚动页面指定次数
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(scroll_count):
            logger.info(f"滚动 {i+1}/{scroll_count}...")
            
            # 滚动到底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 随机等待时间
            wait_time = random.uniform(1.0, 2.5)
            time.sleep(wait_time)
            
            # 提取当前视图中的所有图片URL
            current_image_urls = extract_all_image_urls(driver)
            all_image_urls.update(current_image_urls)
            logger.info(f"已收集 {len(all_image_urls)} 个图片链接")
            
            # 检查是否到达页面底部
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logger.info("已到达页面底部，停止滚动")
                break
            last_height = new_height
        
        # 最终提取所有图片链接
        final_image_urls = extract_all_image_urls(driver)
        all_image_urls.update(final_image_urls)
        
        # 过滤掉明显的空链接
        filtered_urls = {url for url in all_image_urls if len(url) > 30 and 'pinimg.com' in url}
        
        logger.info(f"共获取 {len(filtered_urls)} 个图片链接")
        return list(filtered_urls)
    
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        return []
    
    finally:
        try:
            driver.quit()
            logger.info("浏览器已关闭")
        except:
            pass

def main():
    """主程序"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='Pinterest图片链接抓取工具')
    parser.add_argument('url', type=str, nargs='?', help='要抓取的Pinterest页面URL')
    parser.add_argument('-s', '--scroll', type=int, default=5, help='滚动次数 (默认: 5)')
    parser.add_argument('-c', '--cookies', type=str, default="pinterest_cookies.json", 
                        help='cookies文件路径 (默认: pinterest_cookies.json)')
    
    args = parser.parse_args()
    
    # 如果没有提供URL，则提示用户输入
    if not args.url:
        print("\nPinterest图片抓取工具")
        print("=" * 40)
        url = input("请输入Pinterest页面URL: ").strip()
        scroll_count = int(input("请输入滚动次数 (3-10): ").strip())
        cookies_file = input(f"请输入cookies文件路径 (回车使用默认): ").strip() or "pinterest_cookies.json"
    else:
        url = args.url
        scroll_count = args.scroll
        cookies_file = args.cookies
    
    # 验证URL
    #if not url.startswith("https://mx.pinterest."):
    #    logger.error("错误: 请输入有效的Pinterest URL (以https://pinterest.开头)")
    #    return
    
    # 获取图片链接
    logger.info(f"\n开始抓取页面: {url}")
    start_time = time.time()
    image_links = scrape_pinterest_page(url, scroll_count, cookies_file)
    
    # 打印结果
    logger.info(f"\n获取到 {len(image_links)} 个图片链接 (耗时 {time.time()-start_time:.1f}秒)")
    
    # 按格式分类统计
    format_count = {}
    
    for link in image_links:
        # 从URL中提取文件扩展名
        ext_match = re.search(r'\.([a-z0-9]{3,4})(?=[?&#]|$)', link, re.IGNORECASE)
        if ext_match:
            ext = '.' + ext_match.group(1).lower()
            format_count[ext] = format_count.get(ext, 0) + 1
        else:
            format_count['未知'] = format_count.get('未知', 0) + 1
    
    # 打印格式统计
    logger.info("\n图片格式统计:")
    for fmt, count in format_count.items():
        logger.info(f"{fmt}: {count}个")
    
    # 保存到文件
    if image_links:
        # 从URL生成文件名
        domain = urlparse(url).netloc
        path = urlparse(url).path.replace('/', '_')[:50]
        filename = f"pinterest_{domain}_{path}_links.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(image_links))
        logger.info(f"\n所有链接已保存至 {filename}")
        
        # 生成HTML预览文件
        html_filename = f"pinterest_{domain}_{path}_preview.html"
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(f"<html><head><title>Pinterest 图片抓取预览 - {url}</title>")
            f.write("<style>")
            f.write("body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }")
            f.write(".container { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }")
            f.write(".img-box { border: 1px solid #ddd; padding: 10px; border-radius: 5px; text-align: center; background-color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }")
            f.write("img { max-width: 100%; height: auto; max-height: 200px; object-fit: contain; }")
            f.write("a { font-size: 12px; word-break: break-all; display: block; margin-top: 5px; color: #0066cc; text-decoration: none; }")
            f.write("a:hover { text-decoration: underline; }")
            f.write(".header { background-color: #bd081c; color: white; padding: 15px; margin-bottom: 20px; border-radius: 5px; }")
            f.write(".stats { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }")
            f.write("</style></head><body>")
            f.write(f"<div class='header'><h1>Pinterest 图片抓取结果</h1></div>")
            f.write(f"<div class='stats'>")
            f.write(f"<p><strong>原始页面:</strong> <a href='{url}' target='_blank'>{url}</a></p>")
            f.write(f"<p><strong>抓取时间:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>")
            f.write(f"<p><strong>图片数量:</strong> {len(image_links)}</p>")
            f.write(f"<p><strong>格式统计:</strong> {', '.join([f'{k} {v}' for k, v in format_count.items()])}</p>")
            f.write(f"</div>")
            f.write("<div class='container'>")
            
            # 显示所有图片（最多500张）
            for i, url in enumerate(image_links[:500]):
                # 创建缩略图URL
                thumbnail_url = re.sub(r'/originals/', '/236x/', url)
                
                # 如果替换失败，尝试其他方式
                if thumbnail_url == url:
                    thumbnail_url = re.sub(r'/\d+x/', '/236x/', url)
                
                f.write(f"<div class='img-box'>")
                f.write(f"<img src='{thumbnail_url}' onerror=\"this.src='https://placehold.co/200x200/efefef/999999?text=Image+Error'\">")
                f.write(f"<br><a href='{url}' target='_blank' title='{url}'>{url[-40:]}</a>")
                f.write(f"</div>")
            
            f.write("</div></body></html>")
        logger.info(f"预览文件已保存至 {html_filename}")
        logger.info(f"您可以在浏览器中打开此文件查看所有图片")
    else:
        logger.info("未获取到图片链接，请尝试增加滚动次数或检查页面内容")

if __name__ == "__main__":
    main()