#!/bin/bash

# 清理并重新启动服务器脚本

echo "=== 清理现有服务器进程 ==="
pkill -f "python.*main.py"
sleep 1

echo "=== 启动新服务器 ==="
# 使用 unbuffer 或 PYTHONUNBUFFERED 来确保无缓冲输出
PYTHONUNBUFFERED=1 python3 -u main.py > server_deploy.log 2>&1 &
echo "⏳ 等待服务器启动..."
sleep 5

echo "=== 检查服务器状态 ==="
MAX_RETRIES=5
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 服务器启动成功！"
        echo "📍 访问地址: http://localhost:8000"
        echo "📋 查看日志: tail -f server.log"
        exit 0
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "⏳ 健康检查失败，重试中... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 3
    fi
done

echo "❌ 服务器启动失败，请检查日志:"
echo "   tail -50 server.log"
echo ""
echo "常见问题:"
echo "  1. 端口被占用: lsof -i :8000"
echo "  2. 配置错误: 检查 .env 文件"
echo "  3. 依赖问题: pip install -r requirements.txt"
