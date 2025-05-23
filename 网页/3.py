from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9527")
browser = webdriver.Chrome(options=options)

url = 'https://www.bilibili.com'
browser.get(url)
print(browser.title)	# 哔哩哔哩 (゜-゜)つロ 干杯~-bilibili

