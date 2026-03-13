#!/bin/bash
# Ubuntu服务器部署脚本

echo "================================"
echo "个人知识库 - Ubuntu部署脚本"
echo "================================"

# 更新系统
echo "正在更新系统..."
sudo apt-get update -y
sudo apt-get upgrade -y

# 安装Python和pip
echo "正在安装Python..."
sudo apt-get install -y python3 python3-pip python3-venv

# 安装系统依赖
echo "正在安装系统依赖..."
sudo apt-get install -y \
    python3-dev \
    libpq-dev \
    gcc \
    postgresql-client \
    nginx \
    supervisor

# 创建虚拟环境
echo "正在创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
echo "正在安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建数据目录
mkdir -p data

# 设置环境变量
export FLASK_ENV=production
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export DATABASE_URL=postgresql://user:password@localhost:5432/knowledge_base

# 保存环境变量
echo "export FLASK_ENV=production" >> ~/.bashrc
echo "export SECRET_KEY=$SECRET_KEY" >> ~/.bashrc
echo "export DATABASE_URL=$DATABASE_URL" >> ~/.bashrc

# 配置systemd服务
echo "正在配置systemd服务..."
sudo tee /etc/systemd/system/knowledge-base.service > /dev/null <<EOF
[Unit]
Description=Knowledge Base Flask Application
After=network.target

[Service]
User=$USER
WorkingDirectory=/home/$USER/knowledge-base
Environment="PATH=/home/$USER/knowledge-base/venv/bin"
ExecStart=/home/$USER/knowledge-base/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
echo "正在启动服务..."
sudo systemctl daemon-reload
sudo systemctl enable knowledge-base
sudo systemctl start knowledge-base

# 配置Nginx（可选）
echo "Nginx配置（需要手动完成）"
echo "创建Nginx配置文件: /etc/nginx/sites-available/knowledge-base"

echo "================================"
echo "部署完成！"
echo "================================"
echo "访问: http://your-server-ip:5000"
echo "查看状态: sudo systemctl status knowledge-base"
echo "查看日志: sudo journalctl -u knowledge-base"
echo "================================"