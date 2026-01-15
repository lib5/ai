#!/bin/bash

# 测试结果验证脚本运行器
# 使用方法: ./run_validation.sh [测试结果文件路径] [输出路径]

set -e

# 默认参数
TEST_FILE="${1:-/home/libo/chatapi/test_dataset/test_results_intermediate_20260113_203830.json}"
OUTPUT_FILE="${2:-/home/libo/chatapi/test_dataset_quantity/validation_report_$(date +%Y%m%d_%H%M%S).json}"

echo "============================================================"
echo "测试结果验证工具 - 使用 Azure OpenAI GPT-4.1"
echo "============================================================"
echo ""
echo "配置检查:"

# 检查Python和依赖
echo "检查Python环境..."
python --version

echo "检查aiohttp..."
python -c "import aiohttp; print('  ✓ aiohttp已安装 (版本:', aiohttp.__version__, ')'"

echo "检查配置..."
python -c "
import sys
sys.path.append('/home/libo/chatapi')
from config import settings
print('  ✓ Azure OpenAI端点:', settings.azure_endpoint[:50] + '...' if len(settings.azure_endpoint) > 50 else '  ✓ Azure OpenAI端点:', settings.azure_endpoint)
print('  ✓ Azure OpenAI模型:', settings.azure_deployment_name)
print('  ✓ Azure OpenAI API版本:', settings.azure_api_version)
"

echo ""
echo "开始验证..."
echo "测试文件: $TEST_FILE"
echo "输出文件: $OUTPUT_FILE"
echo ""

# 运行验证脚本
python /home/libo/chatapi/test_dataset_quantity/test_result_validator.py "$TEST_FILE" --output "$OUTPUT_FILE"

echo ""
echo "验证完成！"
echo "结果已保存到: $OUTPUT_FILE"
