#!/bin/bash
# 启动脚本

# 设置环境变量
export FLASK_ENV=production
export PORT=5000
export HOST=0.0.0.0

# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py