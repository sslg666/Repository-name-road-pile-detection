@echo off
chcp 65001 >nul
echo ========================================
echo   云端部署准备工具
echo ========================================
echo.

echo 请选择部署方式:
echo.
echo 1. PythonAnywhere (推荐，免费)
echo 2. Railway.app (免费额度)
echo 3. Docker 部署
echo 4. 查看完整部署指南
echo.
set /p choice=请输入选项 (1-4):

if "%choice%"=="1" goto pythonanywhere
if "%choice%"=="2" goto railway
if "%choice%"=="3" goto docker
if "%choice%"=="4" goto guide
goto end

:pythonanywhere
echo.
echo ========================================
echo   PythonAnywhere 部署步骤
echo ========================================
echo.
echo 1. 访问 https://www.pythonanywhere.com 注册账号
echo 2. 点击 "Files" 上传整个 road_pile_detection 文件夹
echo 3. 打开 Bash 控制台，运行:
echo    cd ~/road_pile_detection
echo    pip install --user -r requirements.txt
echo 4. 点击 "Web" 标签，添加新应用
echo 5. 配置 WSGI 文件（详见 DEPLOY.md）
echo 6. 点击 Reload 启动
echo.
echo 详细步骤请查看 DEPLOY.md 文件
echo.
pause
goto end

:railway
echo.
echo ========================================
echo   Railway.app 部署步骤
echo ========================================
echo.
echo 1. 注册 https://railway.app 账号
echo 2. 将代码上传到 GitHub
echo 3. 在 Railway 中连接 GitHub 仓库
echo 4. 自动部署完成
echo.
echo 详细步骤请查看 DEPLOY.md 文件
echo.
pause
goto end

:docker
echo.
echo ========================================
echo   Docker 部署
echo ========================================
echo.
echo 请确保已安装 Docker，然后运行:
echo.
echo cd road_pile_detection
echo docker build -t pile-detection .
echo docker run -p 5000:5000 pile-detection
echo.
echo 或使用 Docker Compose:
echo docker-compose up -d
echo.
pause
goto end

:guide
echo.
echo 正在打开部署指南...
start notepad DEPLOY.md
goto end

:end
