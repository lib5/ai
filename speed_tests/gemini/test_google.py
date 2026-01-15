#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google官方Gemini模型速度测试脚本
专门测试Google官方Gemini-3-Flash的非流式输出速度和性能

使用方法:
1. python test_google.py
2. python test_google.py --prompts my_prompts.json
"""

import os
import sys
import asyncio
import argparse
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from speed_tests.gemini.google_adapter import GoogleGeminiTester


def check_api_key(api_key: str):
    """检查API密钥是否设置"""
    if not api_key:
        print("❌ 错误: API密钥未提供")
        return False
    return True


def print_model_info(tester: GoogleGeminiTester):
    """打印模型信息"""
    print("\n" + "=" * 60)
    print("🚀 Google官方Gemini模型配置信息")
    print("=" * 60)
    print(f"\n📌 模型名称: {tester.model_name}")
    print(f"   API端点: {tester.get_api_url()}")
    print(f"   超时时间: {tester.timeout}s")
    print(f"   测试类型: 非流式输出")


async def load_prompts(file_path: str):
    """加载测试prompts"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        prompts = data['prompts']
        # 加载所有类型的prompts（文本和图片）
        all_prompts = [p for p in prompts if p.get('type') in ['text', 'image']]

        print(f"\n📁 测试数据信息:")
        print(f"   总prompts: {len(prompts)}")
        print(f"   测试prompts: {len(all_prompts)} (文本+图片)")

        return all_prompts
    except FileNotFoundError:
        print(f"❌ 错误: 测试数据文件不存在: {file_path}")
        return None
    except Exception as e:
        print(f"❌ 错误: 加载测试数据失败: {e}")
        return None


async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 Google官方Gemini模型非流式速度测试")
    print("=" * 60)

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="Google官方Gemini模型速度测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本使用
  python test_google.py

  # 使用自定义测试数据
  python test_google.py --prompts my_prompts.json

  # 设置请求间隔为3秒
  python test_google.py --delay 3

  # 使用指定的模型
  python test_google.py --model gemini-3-flash-preview
        """
    )

    parser.add_argument(
        '--prompts',
        type=str,
        default='benchmark_prompts_20_base64.json',
        help='测试数据文件路径 (默认: benchmark_prompts_20_base64.json)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='请求间隔时间，单位秒 (默认: 2.0)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='gemini-3-flash-preview',
        help='Gemini模型名称 (默认: gemini-3-flash-preview)'
    )

    parser.add_argument(
        '--api-key',
        type=str,
        default='AQ.Ab8RN6J9GWr-zLevwtQ-kjFdSlZRy2wIabqdn4sNbszpacBJ0A',
        help='API密钥 (默认: 内置密钥)'
    )

    parser.add_argument(
        '--base-url',
        type=str,
        default='https://generativelanguage.googleapis.com',
        help='API基础URL (默认: https://generativelanguage.googleapis.com)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=120,
        help=f'请求超时时间，单位秒 (默认: 120)'
    )

    args = parser.parse_args()

    # 打印测试配置
    print(f"\n⚙️ 测试配置:")
    print(f"   测试数据: {args.prompts}")
    print(f"   请求间隔: {args.delay}秒")
    print(f"   模型: {args.model}")
    print(f"   API端点: {args.base_url}")
    print(f"   超时时间: {args.timeout}秒")
    print(f"   测试类型: 非流式输出")

    # 检查API密钥
    if not check_api_key(args.api_key):
        return 1

    # 创建测试器
    tester = GoogleGeminiTester(
        api_key=args.api_key,
        model=args.model,
        base_url=args.base_url,
        timeout=args.timeout
    )

    # 打印模型信息
    print_model_info(tester)

    # 加载测试数据
    prompts = await load_prompts(args.prompts)
    if prompts is None:
        return 1

    # 运行速度测试
    print("\n" + "=" * 60)
    print("🎯 开始速度测试")
    print("=" * 60)

    try:
        await tester.run_test(prompts, delay_between_requests=args.delay)

        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_short = args.model.replace('-', '_')
        output_file = f"google_gemini_{model_short}_{timestamp}.json"
        tester.save_results(output_file)

        print("\n" + "=" * 60)
        print("✅ 速度测试完成!")
        print("=" * 60)
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
