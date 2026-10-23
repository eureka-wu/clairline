@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Changlong Airlines - Dev Mode (HMR)

echo ========================================================
echo   Changlong Airlines - Dev Mode (Vite HMR + Python)
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:3000
echo ========================================================

echo Cleaning ports 3000 and 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo [1/2] Starting Python backend API...
start "Changlong-Backend-API" cmd /k "python backend\server.py"

echo [2/2] Starting Vite frontend dev server...
cd frontend
start "" cmd /c "timeout /t 2 >nul & start http://localhost:5173"
call npm run dev
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Vite dev server exited with error code %ERRORLEVEL%.
)
pause
