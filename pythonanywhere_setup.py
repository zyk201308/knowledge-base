"""
PythonAnywhere部署脚本
使用此脚本配置PythonAnywhere的Web应用
"""

import os
import sys

# 设置Python路径
sys.path.insert(0, '/home/你的用户名/knowledge-base')

# 导入Flask应用
from app import app

# 配置生产环境
app.config['DEBUG'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')

# 设置数据库URL（如果使用PostgreSQL）
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/knowledge_base.db')

if __name__ == '__main__':
    app.run()