@echo off
chcp 65001
git add .
set /p ps=请输入注释:
git commit -m "ps"
git push -u origin master
pause