@echo off
cd /d "%~dp0"
title Changlong Airlines Card Web

echo ========================================================
echo   Changlong Airlines Card Platform (Vue3 + Python)
echo   Local Address: http://localhost:3000
echo ========================================================

if not exist "frontend\dist" (
    echo Building frontend...
    cd frontend
    call npm run build
    cd /d "%~dp0"
)

echo Checking and cleaning port 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo Terminating orphan process PID: %%a
    taskkill /f /pid %%a >nul 2>&1
)

echo Starting server...
start "" cmd /c "timeout /t 1 >nul & start http://localhost:3000"

python backend\server.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server exited with error code %ERRORLEVEL%.
)
pause
