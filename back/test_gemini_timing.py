#!/usr/bin/env python3
"""
测试 Gemini API 首个输出时间统计
"""

import asyncio
import sys
import aiohttp
import json
from services.azure_openai_service import OpenAIService
from config import settings

async def test_gemini_first_chunk_time():
    """测试从请求 Gemini 到返回第一个输出块的时间"""

    print("="*80)
    print("🧪 测试 Gemini API 首个输出时间")
    print("="*80)

    # 创建 OpenAI 服务实例（实际是 Gemini）
    openai_service = OpenAIService(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model
    )

    messages = [
        {
            "role": "user",
            "content": "请写一个简短的Python函数，计算两个数的和"
        }
    ]

    print(f"\n📤 发送请求到: {settings.openai_base_url}")
    print(f"🤖 模型: {settings.openai_model}")
    print(f"💬 查询: {messages[0]['content']}\n")

    try:
        print("="*80)
        print("📥 接收 Gemini 流式响应:")
        print("="*80)

        chunk_count = 0
        async for chunk in openai_service.chat_completion_stream(
            messages,
            max_tokens=500,
            temperature=0.7
        ):
            chunk_count += 1
            if chunk_count == 1:
                print(f"\n✅ 首个输出已接收（见上方时间统计）")
            elif chunk_count <= 5:
                # 显示前几个chunk的内容预览
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    print(f"  📝 Chunk {chunk_count}: {content[:50]}...")

        print(f"\n{'='*80}")
        print(f"✅ 测试完成，共接收 {chunk_count} 个数据块")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}\n")
        return False

    return True

if __name__ == "__main__":
    result = asyncio.run(test_gemini_first_chunk_time())
    sys.exit(0 if result else 1)