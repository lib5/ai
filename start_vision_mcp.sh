#!/bin/bash

# 视觉MCP服务器集成 - 快速启动脚本

echo "============================================================"
echo "视觉MCP服务器集成 - 快速启动脚本"
echo "============================================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3命令"
    exit 1
fi

echo "✅ Python3 已安装"

# 检查依赖
echo ""
echo "📦 检查依赖..."
python3 -c "import aiohttp, fastapi, pydantic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  警告: 缺少依赖，正在安装..."
    pip3 install -r requirements.txt
fi

echo "✅ 依赖检查完成"

# 检查环境变量
echo ""
echo "⚙️  检查环境变量..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "⚠️  未找到.env文件，从.example复制..."
        cp .env.example .env
        echo "✅ 已创建.env文件，请根据需要修改配置"
    else
        echo "⚠️  警告: 未找到.env.example文件"
    fi
else
    echo "✅ .env文件存在"
fi

# 检查MCP服务器
echo ""
echo "🔍 检查MCP服务器状态..."
python3 check_mcp_status.py

echo ""
echo "============================================================"
echo "🚀 启动选项"
echo "============================================================"
echo "1. 启动Chat API服务器 (默认端口: 8000)"
echo "2. 启动视觉MCP服务器 (需要先安装: npm install -g vision-mcp-server)"
echo "3. 运行完整测试"
echo "4. 查看帮助文档"
echo "5. 退出"
echo ""

read -p "请选择操作 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🚀 启动Chat API服务器..."
        echo "   访问地址: http://localhost:8000"
        echo "   API文档: http://localhost:8000/docs"
        echo "   健康检查: http://localhost:8000/health"
        echo ""
        echo "按 Ctrl+C 停止服务器"
        echo ""
        python3 main.py
        ;;
    2)
        echo ""
        echo "🚀 启动视觉MCP服务器..."
        echo "   确保已安装: npm install -g vision-mcp-server"
        echo ""
        echo "按 Ctrl+C 停止服务器"
        echo ""
        npx -y vision-mcp-server
        ;;
    3)
        echo ""
        echo "🧪 运行完整测试..."
        python3 test_react_vision_complete.py
        ;;
    4)
        echo ""
        echo "📚 可用文档:"
        echo "   - VISION_MCP_GUIDE.md (详细使用指南)"
        echo "   - VISION_MCP_INTEGRATION_SUMMARY.md (集成总结)"
        echo "   - README.md (项目文档)"
        echo ""
        echo "要查看文档，请运行:"
        echo "   cat VISION_MCP_GUIDE.md"
        echo "   cat VISION_MCP_INTEGRATION_SUMMARY.md"
        ;;
    5)
        echo ""
        echo "👋 再见!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ 无效选择"
        exit 1
        ;;
esac
