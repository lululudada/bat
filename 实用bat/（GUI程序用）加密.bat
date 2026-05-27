@echo off
chcp 65001

echo ============================
echo  1. 开始加密 Python 文件
echo ============================

set /p file=请输入你的主文件名（例如 main.py）:

pyarmor gen %file%

echo.
echo ============================
echo  2. 进入加密目录
echo ============================

cd dist

echo ============================
echo  3. 开始打包 EXE
echo ============================

pyinstaller -F -w %file%

echo.
echo ============================
echo  完成！EXE 在 dist\dist 目录
echo ============================

pause