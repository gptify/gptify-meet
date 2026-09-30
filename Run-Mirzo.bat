@echo off
title Mirzo - AI Uchrashuv Kotibi
cd /d "%~dp0"

echo ========================================================
echo               Mirzo - AI Uchrashuv Kotibi
echo ========================================================
echo.
echo Tizim ishga tushirilmoqda...

:: Check if port 8000 is already active
netstat -ano | findstr :8000 >nul 2>&1
if %errorlevel% equ 0 (
    echo Server allaqachon ishlab turibdi.
    start http://127.0.0.1:8000
    exit /b
)

:: Launch python launcher
python run.py
pause
