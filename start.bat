@echo off
chcp 65001 >nul
title 长龙航空 · 畅飞卡综合规划与监控平台
echo ========================================================
echo ✈️ 正在启动长龙航空畅飞卡服务平台 (前后端一体化)...
echo 🌐 本地访问地址: http://localhost:3000
echo ========================================================
start "" "http://localhost:3000"
python backend/server.py
pause
