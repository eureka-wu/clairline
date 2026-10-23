@echo off
chcp 65001 >nul
title 长龙航空 · 畅飞卡综合规划与监控平台 (Vue3 + Python)

echo ========================================================
echo   长龙航空畅飞卡智能服务平台 (前后端一体化)
echo   前端架构: Vue 3 + Vite + ECharts
echo   后端架构: Python 3 + SQLite3 数据库
echo   访问地址: http://localhost:3000
echo ========================================================

:: 检查前端依赖与生产构建产物
if not exist "frontend\node_modules" (
    echo [*] 正在初始化前端依赖包 (npm install)...
    cd frontend && call npm install && cd ..
)

if not exist "frontend\dist" (
    echo [*] 正在构建前端单页应用 (npm run build)...
    cd frontend && call npm run build && cd ..
)

echo [*] 正在启动后端服务并打开浏览器...
start "" "http://localhost:3000"

python backend/server.py
pause
