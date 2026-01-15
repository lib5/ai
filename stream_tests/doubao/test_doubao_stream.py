#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆包模型流式测试脚本
测试豆包模型的TTFT (首Token时间) 性能

使用方法:
1. 设置环境变量 DOUBAO_API_KEY
2. 运行测试: python test_doubao_stream.py
"""

import os
import sys
import asyncio
import argparse
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import settings
from stream_tests.doubao.stream_adapter import DoubaoStreamTester


def check_api_key():
    """检查API密钥是否设置"""
    if not settings.doubao_api_key:
        print("❌ 错误: 未设置 DOUBAO_API_KEY 环境变量")
        print("\n请设置环境变量:")
        print("   export DOUBAO_API_KEY='your_doubao_api_key'")
        print("\n或者在 .env 文件中添加:")
        print("   DOUBAO_API_KEY=your_doubao_api_key")
        return False

    return True


def print_model_info(tester: DoubaoStreamTester):
    """打印模型信息"""
    print("\n" + "=" * 60)
    print("🚀 豆包模型流式测试配置")
    print("=" * 60)
    print(f"\n📌 模型名称: {tester.model_name}")
    print(f"   API端点: {tester.get_api_url()}")
    print(f"   超时时间: {tester.timeout}s")
    print(f"   测试类型: TTFT (首Token时间)")


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
    print("🚀 豆包模型流式测试 (TTFT)")
    print("=" * 60)

    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="豆包模型TTFT测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本使用
  python test_doubao_stream.py

  # 使用自定义测试数据
  python test_doubao_stream.py --prompts my_prompts.json

  # 设置请求间隔为3秒
  python test_doubao_stream.py --delay 3

  # 使用指定的模型
  python test_doubao_stream.py --model doubao-pro-4k
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
        default=settings.speed_test_delay,
        help=f'请求间隔时间，单位秒 (默认: {settings.speed_test_delay})'
    )

    parser.add_argument(
        '--model',
        type=str,
        default=settings.doubao_model,
        help=f'豆包模型名称 (默认: {settings.doubao_model})'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=settings.doubao_timeout,
        help=f'请求超时时间，单位秒 (默认: {settings.doubao_timeout})'
    )

    args = parser.parse_args()

    # 打印测试配置
    print(f"\n⚙️ 测试配置:")
    print(f"   测试数据: {args.prompts}")
    print(f"   请求间隔: {args.delay}秒")
    print(f"   模型: {args.model}")
    print(f"   超时时间: {args.timeout}秒")
    print(f"   测试类型: TTFT (首Token时间)")

    # 检查API密钥
    if not check_api_key():
        return 1

    # 创建测试器
    tester = DoubaoStreamTester(
        api_key=settings.doubao_api_key,
        model=args.model,
        base_url=settings.doubao_base_url,
        timeout=args.timeout
    )

    # 打印模型信息
    print_model_info(tester)

    # 加载测试数据
    prompts = await load_prompts(args.prompts)
    if prompts is None:
        return 1

    # 运行流式测试
    print("\n" + "=" * 60)
    print("🎯 开始流式测试")
    print("=" * 60)

    try:
        await tester.run_stream_test(prompts, delay_between_requests=args.delay)

        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"doubao_stream_test_{timestamp}.json"
        tester.save_results(output_file)

        print("\n" + "=" * 60)
        print("✅ 流式测试完成!")
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
