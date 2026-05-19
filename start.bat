@echo off
chcp 65001 >nul
echo ========================================
echo  Road Pile Detection System
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt

echo.
echo [2/3] Starting server...
echo.
echo ========================================
echo  Open browser: http://localhost:5000
echo ========================================
echo.

python app.py
pause
