chcp 65001
@echo off
REM 创建系统级配置目录（需要管理员权限）
mkdir C:\ProgramData\pip 2>nul

REM 创建 pip.ini 文件
echo [global] > C:\ProgramData\pip\pip.ini
echo index-url = https://mirrors.aliyun.com/pypi/simple/ >> C:\ProgramData\pip\pip.ini

REM 验证是否成功
echo 配置已部署到 C:\ProgramData\pip\pip.ini
pip config list
pause