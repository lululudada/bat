@echo off
chcp 65001
echo 正在更新Git仓库...
echo ---------------------------

REM 检查当前目录是否是Git仓库
if not exist ".git" (
    echo 错误：当前目录不是Git仓库！
    pause
    exit /b 1
)

REM 执行更新操作
git pull 2>&1

if %errorlevel% equ 0 (
    echo.
    echo [成功] 仓库已更新到最新版本
) else (
    echo.
    echo [错误] 更新失败，请检查网络或冲突
)

echo ---------------------------
pause