from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains


options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9527")
browser = webdriver.Chrome(options=options)

# 打开百度
browser.get("https://www.baidu.com")

# 定位搜索框并输入 "1+1"
search_box = browser.find_element(By.ID, "kw")  # 百度搜索框的ID是 "kw"
search_box.send_keys("1+1")

# 定位搜索按钮并点击
search_button = browser.find_element(By.ID, "su")  # 百度搜索按钮的ID是 "su"
search_button.click()

# 等待结果（可选）
import time
time.sleep(3)  # 等待3秒查看结果

# 关闭浏览器
#browser.quit()