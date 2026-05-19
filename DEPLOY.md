# 部署指南

## 方式一：本地运行（推荐新手）

### 1. 安装依赖
```bash
cd road_pile_detection
pip install -r requirements.txt
```

### 2. 启动应用
```bash
python app.py
```

### 3. 访问应用
- 本机访问：http://localhost:5000
- 局域网访问：http://你的IP:5000

---

## 方式二：部署到 PythonAnywhere（免费，推荐）

### 步骤 1：注册账号
访问 https://www.pythonanywhere.com 注册免费账号

### 步骤 2：上传代码
1. 点击 "Files" 标签
2. 上传整个 `road_pile_detection` 文件夹
3. 或者使用 Git 克隆：
```bash
cd ~
git clone <你的仓库地址>
```

### 步骤 3：安装依赖
1. 点击 "Consoles" -> "Bash"
2. 运行：
```bash
cd ~/road_pile_detection
pip install --user -r requirements.txt
```

### 步骤 4：配置 Web 应用
1. 点击 "Web" 标签
2. 点击 "Add a new web app"
3. 选择 "Manual configuration"
4. 选择 Python 3.11
5. 设置源代码路径：`/home/你的用户名/road_pile_detection`

### 步骤 5：配置 WSGI
点击 "WSGI configuration file" 链接，修改内容为：
```python
import sys
import os

project_home = '/home/你的用户名/road_pile_detection'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application
```

### 步骤 6：启动
点击 "Reload" 按钮，访问 `https://你的用户名.pythonanywhere.com`

---

## 方式三：部署到 Railway.app（免费额度）

### 步骤 1：准备
1. 注册 https://railway.app 账号
2. 安装 Git

### 步骤 2：上传代码到 GitHub
```bash
cd road_pile_detection
git init
git add .
git commit -m "Initial commit"
git remote add origin <你的GitHub仓库地址>
git push -u origin main
```

### 步骤 3：部署
1. 登录 Railway.app
2. 点击 "New Project"
3. 选择 "Deploy from GitHub repo"
4. 选择你的仓库
5. Railway 会自动检测并部署

### 步骤 4：配置环境变量
在 Railway 项目设置中添加：
- `FLASK_DEBUG` = `false`
- `PORT` = `5000`

---

## 方式四：使用 Docker 部署

### 本地 Docker 运行
```bash
cd road_pile_detection
docker build -t pile-detection .
docker run -p 5000:5000 pile-detection
```

### 使用 Docker Compose
```bash
cd road_pile_detection
docker-compose up -d
```

---

## 方式五：部署到自己的服务器

### 1. 安装环境
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip nginx

# CentOS/RHEL
sudo yum install python3 python3-pip nginx
```

### 2. 上传代码
```bash
scp -r road_pile_detection user@server:/opt/
```

### 3. 安装依赖
```bash
cd /opt/road_pile_detection
pip3 install -r requirements.txt
pip3 install gunicorn
```

### 4. 创建系统服务
创建 `/etc/systemd/system/pile-detection.service`：
```ini
[Unit]
Description=Pile Detection Web App
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/road_pile_detection
ExecStart=/usr/local/bin/gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 300
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5. 启动服务
```bash
sudo systemctl daemon-reload
sudo systemctl start pile-detection
sudo systemctl enable pile-detection
```

### 6. 配置 Nginx 反向代理
创建 `/etc/nginx/sites-available/pile-detection`：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 100M;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/pile-detection /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 常见问题

### Q: 首次加载很慢？
A: 首次运行需要下载 EasyOCR 语言模型（约100MB），请耐心等待。

### Q: 如何修改端口？
A: 设置环境变量 `PORT=8080` 或修改 `app.py` 中的端口号。

### Q: 如何开启 HTTPS？
A: 使用 Let's Encrypt 免费证书，或在云平台开启 SSL。

### Q: 上传文件大小限制？
A: 默认 100MB，可在 `app.py` 中修改 `MAX_CONTENT_LENGTH`。

---

## 推荐方案

| 方案 | 难度 | 费用 | 适用场景 |
|------|------|------|----------|
| 本地运行 | ★☆☆ | 免费 | 个人使用 |
| PythonAnywhere | ★★☆ | 免费 | 分享给朋友 |
| Railway.app | ★★☆ | 免费额度 | 快速分享 |
| Docker | ★★★ | 视服务器 | 企业部署 |
| 自建服务器 | ★★★★ | 视服务器 | 完全控制 |
