import requests
import os
import time
import threading
from tkinter import *
from tkinter import ttk, messagebox
from urllib.parse import quote, urlparse
from PIL import Image, ImageTk
import io
import random
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import psutil
import subprocess
import undetected_chromedriver as uc

class TemuImageScraper:
    def __init__(self, root):
        self.root = root
        self.root.title("Temu商品图片采集工具 - 使用现有浏览器")
        self.root.geometry("900x700")
        self.root.configure(bg='#f5f5f5')
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f5f5f5')
        self.style.configure('TLabel', background='#f5f5f5', font=('Arial', 10))
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('Header.TLabel', font=('Arial', 16, 'bold'))
        
        # 浏览器驱动路径
        self.driver_path = None
        self.driver = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # 标题
        header = ttk.Label(self.root, text="Temu商品图片采集工具 - 使用现有浏览器", style='Header.TLabel')
        header.pack(pady=20)
        
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(padx=20, pady=10, fill=BOTH, expand=True)
        
        # 输入框架
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=X, pady=10)
        
        ttk.Label(input_frame, text="搜索关键词:").grid(row=0, column=0, sticky=W, pady=5)
        self.keyword_var = StringVar()
        keyword_entry = ttk.Entry(input_frame, textvariable=self.keyword_var, width=50)
        keyword_entry.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        
        ttk.Label(input_frame, text="采集页数:").grid(row=1, column=0, sticky=W, pady=5)
        self.pages_var = IntVar(value=1)
        pages_spin = ttk.Spinbox(input_frame, from_=1, to=50, textvariable=self.pages_var, width=10)
        pages_spin.grid(row=1, column=1, padx=5, pady=5, sticky=W)
        
        ttk.Label(input_frame, text="保存路径:").grid(row=2, column=0, sticky=W, pady=5)
        self.path_var = StringVar(value=os.getcwd())
        path_entry = ttk.Entry(input_frame, textvariable=self.path_var, width=50)
        path_entry.grid(row=2, column=1, padx=5, pady=5, sticky=EW)
        ttk.Button(input_frame, text="浏览", command=self.browse_path).grid(row=2, column=2, padx=5, pady=5)
        
        # Chrome驱动路径设置
        ttk.Label(input_frame, text="Chrome驱动路径:").grid(row=3, column=0, sticky=W, pady=5)
        self.driver_path_var = StringVar()
        driver_path_entry = ttk.Entry(input_frame, textvariable=self.driver_path_var, width=50)
        driver_path_entry.grid(row=3, column=1, padx=5, pady=5, sticky=EW)
        ttk.Button(input_frame, text="浏览", command=self.browse_driver_path).grid(row=3, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="(可选，如果不设置，将使用系统PATH中的驱动)").grid(row=4, column=1, sticky=W, pady=0)
        
        # Chrome调试端口设置
        ttk.Label(input_frame, text="Chrome调试端口:").grid(row=5, column=0, sticky=W, pady=5)
        self.port_var = IntVar(value=9222)
        port_spin = ttk.Spinbox(input_frame, from_=1000, to=9999, textvariable=self.port_var, width=10)
        port_spin.grid(row=5, column=1, padx=5, pady=5, sticky=W)
        ttk.Label(input_frame, text="(默认9222，需要先以调试模式启动Chrome)").grid(row=5, column=2, sticky=W, pady=5)
        
        # 图片尺寸筛选
        ttk.Label(input_frame, text="最小图片尺寸:").grid(row=6, column=0, sticky=W, pady=5)
        self.min_size_var = IntVar(value=200)
        min_size_spin = ttk.Spinbox(input_frame, from_=50, to=2000, textvariable=self.min_size_var, width=10)
        min_size_spin.grid(row=6, column=1, padx=5, pady=5, sticky=W)
        ttk.Label(input_frame, text="像素(宽或高)").grid(row=6, column=2, sticky=W, pady=5)
        
        input_frame.columnconfigure(1, weight=1)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X, pady=10)
        
        ttk.Button(button_frame, text="开始采集", command=self.start_scraping).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="停止", command=self.stop_scraping).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="打开文件夹", command=self.open_folder).pack(side=RIGHT, padx=5)
        ttk.Button(button_frame, text="测试浏览器连接", command=self.test_browser).pack(side=LEFT, padx=5)
        ttk.Button(button_frame, text="启动调试Chrome", command=self.launch_debug_chrome).pack(side=LEFT, padx=5)
        
        # 进度框架
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=X, pady=10)
        
        ttk.Label(progress_frame, text="进度:").pack(anchor=W)
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=X, pady=5)
        
        self.status_var = StringVar(value="准备就绪")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(anchor=W)
        
        # 日志框架
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=BOTH, expand=True, pady=10)
        
        ttk.Label(log_frame, text="采集日志:").pack(anchor=W)
        
        log_text_frame = Frame(log_frame)
        log_text_frame.pack(fill=BOTH, expand=True, pady=5)
        
        self.log_text = Text(log_text_frame, height=15, wrap=WORD)
        scrollbar = Scrollbar(log_text_frame, orient=VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 预览框架
        preview_frame = ttk.LabelFrame(main_frame, text="图片预览")
        preview_frame.pack(fill=BOTH, expand=True, pady=10)
        
        self.preview_label = Label(preview_frame, text="暂无预览", bg='white', relief="solid", borderwidth=1)
        self.preview_label.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 控制变量
        self.is_scraping = False
        self.stop_requested = False
        
    def browse_path(self):
        from tkinter import filedialog
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
            
    def browse_driver_path(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="选择ChromeDriver",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file_path:
            self.driver_path_var.set(file_path)
            
    def open_folder(self):
        path = self.path_var.get()
        if os.path.exists(path):
            os.startfile(path) if os.name == 'nt' else os.system(f'open "{path}"')
        else:
            messagebox.showwarning("警告", "指定的路径不存在！")
            
    def log_message(self, message):
        self.log_text.insert(END, f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        self.log_text.see(END)
        self.root.update()
        
    def update_preview(self, image_data):
        try:
            image = Image.open(io.BytesIO(image_data))
            image.thumbnail((300, 300))
            photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=photo, text="")
            self.preview_label.image = photo
        except Exception as e:
            self.preview_label.configure(text="预览加载失败")
            
    def launch_debug_chrome(self):
        """启动调试模式的Chrome浏览器"""
        try:
            # 查找Chrome浏览器的安装路径
            chrome_path = None
            if os.name == 'nt':  # Windows
                possible_paths = [
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                    os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        chrome_path = path
                        break
            else:  # macOS or Linux
                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                if not os.path.exists(chrome_path):
                    chrome_path = "google-chrome"  # 尝试使用系统PATH中的Chrome
            
            if not chrome_path:
                messagebox.showerror("错误", "未找到Chrome浏览器安装路径")
                return
                
            # 构建启动命令
            port = self.port_var.get()
            user_data_dir = os.path.join(os.getcwd(), f"chrome_profile_{port}")
            
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir)
                
            cmd = [
                chrome_path,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={user_data_dir}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            # 启动Chrome
            subprocess.Popen(cmd)
            self.log_message(f"已启动调试模式Chrome，端口: {port}")
            self.log_message("请在浏览器中登录Temu账号，然后点击'测试浏览器连接'")
            
        except Exception as e:
            self.log_message(f"启动Chrome失败: {str(e)}")
            messagebox.showerror("错误", f"启动Chrome失败: {str(e)}")
            
    def init_browser(self):
        """初始化浏览器驱动，只attach到已存在的调试Chrome实例（与test_browser一致）"""
        try:
            port = self.port_var.get()
            driver_path = self.driver_path_var.get().strip()
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            if driver_path and os.path.exists(driver_path):
                self.driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
            else:
                from selenium.webdriver.chrome.service import Service
                service = Service()
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            # 注入反检测脚本
            try:
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.navigator.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    """
                })
                self.log_message("已注入反检测脚本")
            except Exception as e2:
                self.log_message(f'注入反检测脚本失败: {str(e2)}')
            self.log_message("浏览器驱动初始化成功，已连接到现有Chrome实例")
            return True
        except Exception as e:
            self.log_message(f"浏览器驱动初始化失败: {str(e)}")
            messagebox.showerror("错误", f"浏览器驱动初始化失败: {str(e)}\n\n请确保:\n1. 已启动调试模式的Chrome浏览器\n2. ChromeDriver版本与Chrome浏览器版本匹配\n3. 端口设置正确")
            return False
            
    def close_browser(self):
        """关闭浏览器驱动，但不关闭Chrome浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                self.log_message("浏览器驱动已关闭")
            except:
                pass
            finally:
                self.driver = None
                
    def test_browser(self):
        """测试浏览器是否正常连接（仅用Selenium attach模式，避免uc卡死）"""
        try:
            port = self.port_var.get()
            driver_path = self.driver_path_var.get().strip()
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            if driver_path and os.path.exists(driver_path):
                driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
            else:
                from selenium.webdriver.chrome.service import Service
                service = Service()
                driver = webdriver.Chrome(service=service, options=chrome_options)
            try:
                current_url = driver.current_url
                title = driver.title
                self.log_message(f"浏览器连接测试成功: {title} - {current_url}")
                messagebox.showinfo("测试成功", f"浏览器连接测试成功: {title}")
            except Exception as e:
                self.log_message(f"浏览器连接测试失败: {str(e)}")
                messagebox.showerror("测试失败", f"浏览器连接测试失败: {str(e)}")
            finally:
                try:
                    driver.quit()
                except:
                    pass
        except Exception as e:
            self.log_message(f"浏览器连接测试失败: {str(e)}")
            messagebox.showerror("测试失败", f"浏览器连接测试失败: {str(e)}")
            
    def is_likely_product_image(self, img_url, img_element):
        """判断图片是否可能是商品图片"""
        # 检查URL特征
        url_lower = img_url.lower()
        url_keywords = [
            'product', 'goods', 'item', 'commodity', 
            'gallery', 'image', 'pic', 'photo',
            'jpg', 'jpeg', 'png', 'webp'
        ]
        
        # 检查是否包含常见图片关键词
        for keyword in url_keywords:
            if keyword in url_lower:
                return True
                
        # 检查常见图片域名
        domain = urlparse(img_url).netloc.lower()
        if any(x in domain for x in ['temu', 'alicdn', 'amazonaws', 'cloudfront']):
            return True
            
        return False
        
    def extract_image_urls_from_page(self):
        """从当前页面提取所有可能的图片URL，支持多属性和背景图"""
        image_urls = []
        try:
            img_elements = self.driver.find_elements(By.TAG_NAME, "img")
            self.log_message(f"找到 {len(img_elements)} 个图片元素")
            for img_element in img_elements:
                try:
                    # 优先尝试多种属性
                    img_url = (
                        img_element.get_attribute("src") or
                        img_element.get_attribute("data-src") or
                        img_element.get_attribute("data-original") or
                        img_element.get_attribute("data-lazy")
                    )
                    # 检查style中的背景图
                    if not img_url:
                        style = img_element.get_attribute("style")
                        if style and "background-image" in style:
                            import re
                            match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                            if match:
                                img_url = match.group(1)
                    if not img_url:
                        continue
                    # 确保URL是完整的
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif not img_url.startswith('http'):
                        current_url = self.driver.current_url
                        base_url = current_url.split('/search_result')[0] if '/search_result' in current_url else current_url
                        if img_url.startswith('/'):
                            img_url = base_url + img_url
                        else:
                            img_url = base_url + '/' + img_url
                    if self.is_likely_product_image(img_url, img_element):
                        image_urls.append(img_url)
                        self.log_message(f"找到可能的产品图片: {img_url[:80]}...")
                except Exception as e:
                    self.log_message(f"处理图片元素时出错: {str(e)}")
                    continue
            # 额外查找div等标签的背景图
            bg_elements = self.driver.find_elements(By.XPATH, "//*[contains(@style,'background-image')]")
            for bg in bg_elements:
                try:
                    style = bg.get_attribute("style")
                    if style:
                        import re
                        match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                        if match:
                            img_url = match.group(1)
                            if img_url.startswith('//'):
                                img_url = 'https:' + img_url
                            elif not img_url.startswith('http'):
                                current_url = self.driver.current_url
                                base_url = current_url.split('/search_result')[0] if '/search_result' in current_url else current_url
                                if img_url.startswith('/'):
                                    img_url = base_url + img_url
                                else:
                                    img_url = base_url + '/' + img_url
                            if self.is_likely_product_image(img_url, bg):
                                image_urls.append(img_url)
                                self.log_message(f"背景图产品图片: {img_url[:80]}...")
                except Exception as e:
                    self.log_message(f"处理背景图元素时出错: {str(e)}")
                    continue
        except Exception as e:
            self.log_message(f"提取图片URL时出错: {str(e)}")
        return image_urls

    def scrape_images_with_selenium(self):
        """使用Selenium采集图片（加强滚动和等待）"""
        keyword = self.keyword_var.get().strip()
        if not keyword:
            messagebox.showwarning("警告", "请输入搜索关键词！")
            return
        pages = self.pages_var.get()
        save_path = os.path.join(self.path_var.get(), keyword)
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        if not self.init_browser():
            return
        self.is_scraping = True
        self.stop_requested = False
        total_images = 0
        try:
            for page in range(1, pages + 1):
                if self.stop_requested:
                    break
                self.status_var.set(f"正在采集第 {page} 页...")
                self.log_message(f"开始采集第 {page} 页")
                search_url = f"https://www.temu.com/search_result.html?search_key={quote(keyword)}&page={page}"
                try:
                    self.log_message(f"访问页面: {search_url}")
                    self.driver.get(search_url)
                    # 等待页面加载完成
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.TAG_NAME, "img"))
                    )
                    # 多次滚动页面，确保图片全部加载
                    self.log_message("多次滚动页面以加载所有图片...")
                    scroll_pause_time = 1
                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    for i in range(10):  # 滚动更多次
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(scroll_pause_time)
                        new_height = self.driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            break
                        last_height = new_height
                    # 额外等待图片加载
                    time.sleep(2)
                    image_urls = self.extract_image_urls_from_page()
                    self.log_message(f"找到 {len(image_urls)} 个可能的商品图片URL")
                    if not image_urls:
                        self.log_message("未找到商品图片，尝试备用方法...")
                        img_elements = self.driver.find_elements(By.TAG_NAME, "img")
                        for img_element in img_elements:
                            try:
                                img_url = img_element.get_attribute("src") or img_element.get_attribute("data-src")
                                if img_url and img_url.startswith('http'):
                                    image_urls.append(img_url)
                            except:
                                pass
                        self.log_message(f"备用方法找到 {len(image_urls)} 个图片URL")
                    # 下载图片
                    for idx, img_url in enumerate(image_urls):
                        if self.stop_requested:
                            break
                            
                        try:
                            self.log_message(f"下载图片 {idx+1}/{len(image_urls)}: {img_url[:80]}...")
                            img_response = requests.get(img_url, timeout=15, headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            })
                            img_response.raise_for_status()
                            
                            # 检查图片尺寸
                            try:
                                img = Image.open(io.BytesIO(img_response.content))
                                width, height = img.size
                                min_size = self.min_size_var.get()
                                
                                if width < min_size and height < min_size:
                                    self.log_message(f"跳过小图片: {width}x{height}")
                                    continue
                            except:
                                pass
                            
                            # 保存图片
                            img_name = f"{keyword}_{page}_{idx+1}_{int(time.time())}.jpg"
                            img_path = os.path.join(save_path, img_name)
                            
                            with open(img_path, 'wb') as f:
                                f.write(img_response.content)
                                
                            total_images += 1
                            self.log_message(f"图片保存成功: {img_name}")
                            
                            # 更新预览
                            if idx == 0:  # 只预览第一张图片
                                self.update_preview(img_response.content)
                                
                            # 更新进度
                            progress_value = ((page-1) * 100 / pages) + ((idx+1) * 100 / (len(image_urls) * pages))
                            self.progress['value'] = progress_value
                            self.root.update()
                            
                            # 添加随机延迟，避免请求过于频繁
                            time.sleep(random.uniform(0.5, 1.5))
                            
                        except Exception as e:
                            self.log_message(f"下载图片失败: {str(e)}")
                            continue
                    
                except Exception as e:
                    self.log_message(f"获取第 {page} 页失败: {str(e)}")
                    continue
                    
            if self.stop_requested:
                self.status_var.set("采集已停止")
                self.log_message("采集任务被用户停止")
            else:
                self.status_var.set(f"采集完成，共获取 {total_images} 张图片")
                self.log_message(f"采集完成，共获取 {total_images} 张图片")
                messagebox.showinfo("完成", f"采集完成，共获取 {total_images} 张图片")
                
        except Exception as e:
            self.log_message(f"采集过程中发生错误: {str(e)}")
            messagebox.showerror("错误", f"采集过程中发生错误: {str(e)}")
            
        finally:
            self.close_browser()
            self.is_scraping = False
            self.stop_requested = False
            self.progress['value'] = 0
            
    def start_scraping(self):
        if self.is_scraping:
            messagebox.showwarning("警告", "采集正在进行中！")
            return
            
        thread = threading.Thread(target=self.scrape_images_with_selenium)
        thread.daemon = True
        thread.start()
        
    def stop_scraping(self):
        if self.is_scraping:
            self.stop_requested = True
            self.log_message("正在停止采集...")
        else:
            messagebox.showinfo("提示", "没有正在进行的采集任务")

if __name__ == "__main__":
    root = Tk()
    app = TemuImageScraper(root)
    root.mainloop()