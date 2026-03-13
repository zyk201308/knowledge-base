# Gunicorn配置文件

import multiprocessing

# 服务器地址
bind = "0.0.0.0:5000"

# Worker配置
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 日志配置
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 进程名称
proc_name = "knowledge-base"