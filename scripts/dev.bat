@echo off
cd /d "%~dp0"
title Changlong Airlines - Dev Server

python dev_runner.py
if errorlevel 1 (
    echo.
    echo [ERROR] Dev server stopped with error code %ERRORLEVEL%.
    pause
)
