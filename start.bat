@echo off
REM 启动脚本 - Windows

echo ========================================
echo 个人知识库启动脚本
echo ========================================

REM 设置环境变量
set FLASK_ENV=production
set PORT=5000
set HOST=0.0.0.0

REM 安装依赖
echo 正在安装依赖...
pip install -r requirements.txt

REM 运行应用
echo 启动服务器...
python app.py

pause