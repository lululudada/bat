import os
import subprocess

# 先切换到chrome可执行文件的路径
os.chdir(r"C:\Program Files\Google\Chrome\Application")
# 然后使用Popen执行cmd命令，这里的chrome.exe 可替换为 chrome，注意这里没有 start
subprocess.Popen('chrome.exe --remote-debugging-port=9527 --user-data-dir="C:\selenium"')

from selenium import webdriver

if __name__ == '__main__':
    browser = webdriver.Chrome()
    browser.get('https://www.csdn.net/')
    # 获取远程链接的地址
    print('remote_url:', browser.caps['goog:chromeOptions']['debuggerAddress'])
    print('session_id:', browser.session_id)
    print(browser.title)

