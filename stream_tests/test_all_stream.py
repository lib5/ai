#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
所有模型流式测试脚本
统一测试豆包、Gemini等模型的TTFT性能

使用方法:
1. python test_all_stream.py --model doubao
2. python test_all_stream.py --model gemini
3. python test_all_stream.py --model all
"""

import os
import sys
import asyncio
import argparse
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from stream_tests.doubao.stream_adapter import DoubaoStreamTester
from stream_tests.gemini.stream_adapter import GeminiStreamTester
from stream_tests.qwen.stream_adapter import QwenStreamTester
from stream_tests.gpt4.stream_adapter import GPT4StreamTester


async def load_prompts(file_path: str):
    """加载测试prompts"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        prompts = data['prompts']
        all_prompts = [p for p in prompts if p.get('type') in ['text', 'image']]
        return all_prompts
    except Exception as e:
        print(f"❌ 错误: 加载测试数据失败: {e}")
        return None


async def test_model(model_name: str, prompts: list, delay: float):
    """测试指定模型"""
    tester = None

    if model_name.lower() == 'doubao':
        if not settings.doubao_api_key:
            print("❌ 豆包API密钥未设置")
            return None

        tester = DoubaoStreamTester(
            api_key=settings.doubao_api_key,
            model=settings.doubao_model,
            base_url=settings.doubao_base_url,
            timeout=settings.doubao_timeout
        )

    elif model_name.lower() == 'gemini':
        if not settings.openai_api_key:
            print("❌ Gemini API密钥未设置")
            return None

        tester = GeminiStreamTester(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            timeout=60
        )

    elif model_name.lower() == 'qwen':
        qwen_api_key = os.getenv("QWEN_API_KEY") or settings.qwen_api_key
        if not qwen_api_key:
            print("❌ Qwen API密钥未设置")
            return None

        tester = QwenStreamTester(
            api_key=qwen_api_key,
            model='qwen3-vl-plus',
            timeout=60
        )

    elif model_name.lower() == 'gpt4':
        if not settings.azure_openai_api_key:
            print("❌ Azure OpenAI API密钥未设置")
            return None

        tester = GPT4StreamTester(
            api_key=settings.azure_openai_api_key,
            deployment_name='gpt-4.1',
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            timeout=30
        )

    if tester is None:
        print(f"❌ 不支持的模型: {model_name}")
        return None

    print(f"\n{'='*60}")
    print(f"🚀 开始测试 {model_name}")
    print(f"{'='*60}")

    await tester.run_stream_test(prompts, delay_between_requests=delay)

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{model_name}_stream_test_{timestamp}.json"
    tester.save_results(output_file)

    return tester


async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 所有模型流式测试 (TTFT)")
    print("=" * 60)

    parser = argparse.ArgumentParser(
        description="所有模型TTFT测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 测试豆包
  python test_all_stream.py --model doubao

  # 测试Gemini
  python test_all_stream.py --model gemini

  # 测试Qwen
  python test_all_stream.py --model qwen

  # 测试GPT-4
  python test_all_stream.py --model gpt4

  # 测试所有可用模型
  python test_all_stream.py --model all

  # 使用自定义测试数据
  python test_all_stream.py --model doubao --prompts my_prompts.json
        """
    )

    parser.add_argument(
        '--model',
        type=str,
        required=True,
        choices=['doubao', 'gemini', 'qwen', 'gpt4', 'all'],
        help='要测试的模型'
    )

    parser.add_argument(
        '--prompts',
        type=str,
        default='benchmark_prompts_20_base64.json',
        help='测试数据文件路径'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='请求间隔时间，单位秒'
    )

    args = parser.parse_args()

    # 加载测试数据
    prompts = await load_prompts(args.prompts)
    if prompts is None:
        return 1

    print(f"\n📁 测试数据: {args.prompts}")
    print(f"📊 测试prompts: {len(prompts)}")

    # 确定要测试的模型
    models_to_test = []
    if args.model == 'all':
        models_to_test = ['doubao', 'gemini', 'qwen', 'gpt4']
    else:
        models_to_test = [args.model]

    results = {}
    for model in models_to_test:
        result = await test_model(model, prompts, args.delay)
        if result:
            results[model] = result

    # 打印总结
    print(f"\n{'='*60}")
    print("✅ 所有测试完成!")
    print(f"{'='*60}")

    if results:
        print("\n📊 模型TTFT对比:")
        for model, tester in results.items():
            stats = tester.calculate_statistics()
            if 'ttft_ms' in stats:
                ttft = stats['ttft_ms']
                print(f"\n{model.upper()}:")
                print(f"  TTFT均值: {ttft['mean']:.2f}ms")
                print(f"  TTFT中位数: {ttft['median']:.2f}ms")
                print(f"  TTFT最小: {ttft['min']:.2f}ms")
                print(f"  TTFT最大: {ttft['max']:.2f}ms")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
