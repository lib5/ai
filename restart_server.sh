#!/bin/bash

# 清理并重新启动服务器脚本

echo "=== 清理现有服务器进程 ==="
pkill -f "python.*main.py"
sleep 1

echo "=== 启动新服务器 ==="
python3 main.py > /tmp/server.log 2>&1 &
sleep 2

echo "=== 检查服务器状态 ==="
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ 服务器启动成功！"
    echo "📍 访问地址: http://localhost:8000"
    echo "📋 查看日志: tail -f /tmp/server.log"
else
    echo "❌ 服务器启动失败"
fi
