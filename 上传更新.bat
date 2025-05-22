@echo off
chcp 65001
git config --global user.email "77462123@qq.com"
git config --global user.name "lululudada"
git init
git add .
set /p ps=请输入注释:
git commit -m "%ps%"
git push -u origin master
pause