@echo off
chcp 65001 >nul
echo ========================================
echo   动态环境下道路桩号视觉检测与文字识别软件
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 正在检查依赖...
pip install -r requirements.txt -q

echo.
echo [2/3] 正在启动服务...
echo.
echo ========================================
echo   本地访问地址: http://localhost:5000
echo   局域网访问: http://0.0.0.0:5000
echo ========================================
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

REM 启动应用
python app.py
pause
