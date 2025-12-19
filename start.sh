#!/bin/bash

# 聊天 API 启动脚本

echo "启动聊天 API 服务..."

# 检查是否安装了依赖
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖包..."
pip install -r requirements.txt

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，将使用环境变量或默认值"
    echo "请参考 .env.example 文件创建 .env 文件"
fi

# 启动服务
echo "启动 FastAPI 服务..."
python main.py