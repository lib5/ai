#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini模型快速测试脚本
测试一个文本prompt和一个图片prompt，输出详细统计信息
"""

import os
import sys
import json
import asyncio
import time
import statistics
import numpy as np
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import settings
from speed_tests.gemini.adapter import GeminiTester


def load_test_prompts(file_path: str):
    """加载测试prompts - 一个文本一个图片"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    prompts = data['prompts']
    text_prompts = [p for p in prompts if p.get('type') == 'text']
    image_prompts = [p for p in prompts if p.get('type') == 'image']

    selected = []
    if text_prompts:
        selected.append(text_prompts[0])
    if image_prompts:
        selected.append(image_prompts[0])

    return selected


def extract_question(prompt: dict) -> str:
    """提取问题内容"""
    prompt_type = prompt.get('type', 'text')
    query = prompt.get('query', '')

    if prompt_type == 'image':
        # 图片类型，显示图片URL或标记
        image_urls = prompt.get('image_urls', [])
        if image_urls:
            return f"[图片] {query}" if query else f"[图片: {len(image_urls)}张]"
        return f"[图片] {query}"
    else:
        return query if query else "[文本]"


def parse_complete_prompt(complete_prompt) -> list:
    """
    解析complete_prompt为消息列表
    处理两种格式：JSON字符串 或 直接的list
    """
    # 如果已经是list，直接使用
    if isinstance(complete_prompt, list):
        messages = complete_prompt
    else:
        # 如果是字符串，解析JSON
        messages = json.loads(complete_prompt)

    # 转换消息格式为Gemini API兼容格式
    converted_messages = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')

        if isinstance(content, list):
            # 处理复合内容（文本+图片）
            new_content = []
            for item in content:
                item_type = item.get('type', '')
                if item_type == 'input_text' or item_type == 'text':
                    new_content.append({
                        "type": "text",
                        "text": item.get('text', '')
                    })
                elif item_type == 'input_image' or item_type == 'image_url':
                    # Gemini API图片格式
                    image_url = item.get('image_url', '')
                    if isinstance(image_url, dict):
                        image_url = image_url.get('url', '')
                    new_content.append({
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    })

            if new_content:
                converted_messages.append({"role": role, "content": new_content})
        else:
            # 普通文本内容
            converted_messages.append({"role": role, "content": content})

    return converted_messages


def print_detailed_stats(results: list):
    """打印详细统计信息"""
    successful = [r for r in results if r.get('success', False)]

    if not successful:
        print("\n❌ 没有成功的测试结果")
        return

    print("\n" + "=" * 70)
    print("📊 详细测试结果")
    print("=" * 70)

    # 打印每个测试的详细信息
    for i, r in enumerate(results, 1):
        print(f"\n--- 测试 {i} ---")
        print(f"  类型: {r['type']}")
        print(f"  问题: {r['question'][:60]}..." if len(r['question']) > 60 else f"  问题: {r['question']}")
        if r['success']:
            print(f"  ✅ 响应时间: {r['response_time_ms']:.2f} ms")
            print(f"  输出Token: {r['output_tokens']}")
            print(f"  Token速度: {r['tokens_per_second']:.2f} tokens/s")
            print(f"  响应预览: {r['response_preview']}")
        else:
            print(f"  ❌ 错误: {r['error']}")

    # 分类统计
    text_results = [r for r in successful if r.get('type') == 'text']
    image_results = [r for r in successful if r.get('type') == 'image']

    print("\n" + "=" * 70)
    print("📈 分类统计")
    print("=" * 70)

    def calc_stats(values, name, unit=""):
        print(f"\n{name}:")
        print(f"  均值: {statistics.mean(values):.2f}{unit}")
        print(f"  中位数: {statistics.median(values):.2f}{unit}")
        print(f"  最小值: {min(values):.2f}{unit}")
        print(f"  最大值: {max(values):.2f}{unit}")
        if len(values) >= 5:
            print(f"  P80: {np.percentile(values, 80):.2f}{unit}")
            print(f"  P90: {np.percentile(values, 90):.2f}{unit}")
            print(f"  P99: {np.percentile(values, 99):.2f}{unit}")

    # 文本类型统计
    if text_results:
        text_times = [r['response_time_ms'] for r in text_results]
        text_tokens = [r['output_tokens'] for r in text_results]
        text_speed = [r['tokens_per_second'] for r in text_results]

        print("\n📝 文本类型 (无图片):")
        calc_stats(text_times, "  响应时间", " ms")
        calc_stats(text_tokens, "  输出Token数")
        calc_stats(text_speed, "  Token生成速度", " tokens/s")
        print(f"  测试数量: {len(text_results)}")

    # 图片类型统计
    if image_results:
        image_times = [r['response_time_ms'] for r in image_results]
        image_tokens = [r['output_tokens'] for r in image_results]
        image_speed = [r['tokens_per_second'] for r in image_results]

        print("\n📸 图片类型 (有图片):")
        calc_stats(image_times, "  响应时间", " ms")
        calc_stats(image_tokens, "  输出Token数")
        calc_stats(image_speed, "  Token生成速度", " tokens/s")
        print(f"  测试数量: {len(image_results)}")

    # 图片 vs 文本对比
    if text_results and image_results:
        text_avg_time = statistics.mean([r['response_time_ms'] for r in text_results])
        image_avg_time = statistics.mean([r['response_time_ms'] for r in image_results])
        text_avg_speed = statistics.mean([r['tokens_per_second'] for r in text_results])
        image_avg_speed = statistics.mean([r['tokens_per_second'] for r in image_results])

        time_diff = ((image_avg_time - text_avg_time) / text_avg_time) * 100
        speed_diff = ((text_avg_speed - image_avg_speed) / image_avg_speed) * 100

        print("\n" + "=" * 70)
        print("📊 图片 vs 文本速度对比")
        print("=" * 70)
        print(f"\n⏱️ 响应时间:")
        print(f"  文本平均: {text_avg_time:.2f} ms")
        print(f"  图片平均: {image_avg_time:.2f} ms")
        print(f"  图片比文本慢: {time_diff:.1f}%")

        print(f"\n🚀 Token生成速度:")
        print(f"  文本平均: {text_avg_speed:.2f} tokens/s")
        print(f"  图片平均: {image_avg_speed:.2f} tokens/s")
        if image_avg_speed > 0:
            print(f"  文本比图片快: {speed_diff:.1f}%")
        else:
            print(f"  无法计算速度差异")

    # 整体统计（当测试数量超过2时）
    if len(successful) >= 2:
        print("\n" + "=" * 70)
        print("📈 整体统计汇总")
        print("=" * 70)

        response_times = [r['response_time_ms'] for r in successful]
        output_tokens = [r['output_tokens'] for r in successful]
        tokens_per_second = [r['tokens_per_second'] for r in successful]

        calc_stats(response_times, "⏱️  响应时间", " ms")
        calc_stats(output_tokens, "📝 输出Token数")
        calc_stats(tokens_per_second, "🚀 Token生成速度", " tokens/s")


async def run_single_test(tester: GeminiTester, prompt: dict) -> dict:
    """运行单个测试"""
    prompt_type = prompt.get('type', 'text')
    question = extract_question(prompt)

    print(f"\n🔄 测试中: [{prompt_type}] {question[:50]}...")

    start_time = time.time()

    try:
        # 使用本地的parse_complete_prompt函数
        messages = parse_complete_prompt(prompt['complete_prompt'])

        # 发送请求
        response = await tester.chat_completion(messages)

        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000

        # 提取响应内容
        content = tester.extract_content(response)
        output_tokens = tester.estimate_tokens(content)
        tokens_per_second = (output_tokens / response_time_ms) * 1000 if response_time_ms > 0 else 0

        return {
            'success': True,
            'type': prompt_type,
            'question': question,
            'response_time_ms': response_time_ms,
            'output_tokens': output_tokens,
            'tokens_per_second': tokens_per_second,
            'response_preview': content[:100] + "..." if len(content) > 100 else content
        }

    except Exception as e:
        end_time = time.time()
        return {
            'success': False,
            'type': prompt_type,
            'question': question,
            'response_time_ms': (end_time - start_time) * 1000,
            'output_tokens': 0,
            'tokens_per_second': 0,
            'error': str(e)
        }


async def main():
    print("=" * 70)
    print("🚀 Gemini模型快速测试 (1文本 + 1图片)")
    print("=" * 70)

    # 检查API密钥
    if not settings.openai_api_key:
        print("❌ 错误: 未设置 OPENAI_API_KEY")
        return 1

    # 创建测试器
    tester = GeminiTester(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        base_url=settings.openai_base_url,
        timeout=60
    )

    print(f"\n📌 模型: {tester.model_name}")
    print(f"   API: {tester.get_api_url()}")

    # 加载测试数据（使用base64版本）
    prompts_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'benchmark_prompts_20_base64.json'
    )

    prompts = load_test_prompts(prompts_file)
    print(f"\n📁 加载了 {len(prompts)} 个测试prompt")

    # 运行测试
    results = []
    for prompt in prompts:
        result = await run_single_test(tester, prompt)
        results.append(result)

        # 将结果添加到tester中，这样save_results可以访问
        from speed_tests.base_tester import TestResult
        tester_result = TestResult(
            model_name=tester.model_name,
            prompt_id=prompt.get('id', 0),
            prompt_type=result['type'],
            response_time_ms=result['response_time_ms'],
            input_tokens=0,  # 快速测试不计算输入token
            output_tokens=result['output_tokens'],
            tokens_per_second=result['tokens_per_second'],
            success=result['success'],
            error_message=result.get('error')
        )
        tester.results.append(tester_result)

        await asyncio.sleep(1)  # 请求间隔

    # 打印统计
    print_detailed_stats(results)

    # 保存结果（使用base_tester的save_results方法）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"gemini_quick_test_{timestamp}.json"

    # 使用base_tester的save_results方法保存完整统计
    tester.save_results(output_file)

    print("\n✅ 测试完成!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
