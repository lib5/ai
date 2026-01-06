#!/usr/bin/env python3
"""
直接显示 /api/v1/chat/history_4_agent 接口返回的原始内容
"""

import asyncio
import json
import aiohttp
from config import settings

async def show_history_response():
    """显示历史接口的原始返回内容"""
    print("=" * 80)
    print("显示 /api/v1/chat/history_4_agent 接口原始返回内容")
    print("=" * 80)

    base_url = settings.chat_api_base_url
    url = f"{base_url}/api/v1/chat/history_4_agent"

    # 测试不同的用户ID，看哪个有数据
    test_user_ids = [
        "550e8400-e29b-41d4-a716-446655440000",  # 测试中的UUID
        "user_123",  # 简单用户ID
        "test_user",  # 测试用户
    ]

    for user_id in test_user_ids:
        print(f"\n{'=' * 60}")
        print(f"用户ID: {user_id}")
        print(f"{'=' * 60}")

        try:
            request_data = {
                "user_id": user_id,
                "page": 1,
                "page_size": 10
            }

            print(f"\n📤 请求URL: {url}")
            print(f"📤 请求数据: {json.dumps(request_data, ensure_ascii=False)}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    print(f"\n📥 状态码: {response.status}")
                    print(f"📥 响应头:")
                    for key, value in response.headers.items():
                        print(f"   {key}: {value}")

                    # 获取原始响应文本
                    response_text = await response.text()
                    print(f"\n📥 原始响应 (text):")
                    print(response_text)

                    # 尝试解析为JSON
                    try:
                        response_json = json.loads(response_text)
                        print(f"\n📥 解析后的JSON:")
                        print(json.dumps(response_json, indent=2, ensure_ascii=False))

                        # 详细分析数据结构
                        if isinstance(response_json, dict) and "data" in response_json:
                            data = response_json["data"]
                            if isinstance(data, dict) and "messages" in data:
                                messages = data["messages"]
                                print(f"\n🔍 数据分析:")
                                print(f"   messages类型: {type(messages)}")
                                print(f"   messages长度: {len(messages)}")

                                if messages:
                                    print(f"\n📋 消息详情:")
                                    for i, msg in enumerate(messages, 1):
                                        print(f"\n   消息 {i}:")
                                        print(f"     类型: {type(msg)}")
                                        if isinstance(msg, dict):
                                            print(f"     键: {list(msg.keys())}")
                                            print(f"     内容:")
                                            print(json.dumps(msg, indent=4, ensure_ascii=False))
                                        else:
                                            print(f"     值: {msg}")
                                else:
                                    print(f"\n⚠️  messages为空列表")

                    except json.JSONDecodeError:
                        print(f"\n⚠️  无法解析为JSON")

        except Exception as e:
            print(f"\n❌ 异常: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("显示完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(show_history_response())
