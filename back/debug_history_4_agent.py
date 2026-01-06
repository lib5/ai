#!/usr/bin/env python3
"""
调试 /api/v1/chat/history_4_agent 接口返回的数据
"""

import asyncio
import json
import aiohttp
from config import settings

async def debug_history_4_agent():
    """调试 /api/v1/chat/history_4_agent 接口"""
    print("=" * 80)
    print("调试 /api/v1/chat/history_4_agent 接口")
    print("=" * 80)

    # 获取配置的基础URL
    base_url = settings.chat_api_base_url
    print(f"配置的基础URL: {base_url}")

    # 构造完整URL
    url = f"{base_url}/api/v1/chat/history_4_agent"
    print(f"完整URL: {url}")

    # 测试不同的用户ID
    test_user_ids = [
        "550e8400-e29b-41d4-a716-446655440000",  # 测试中的UUID
    ]

    for user_id in test_user_ids:
        print(f"\n{'=' * 60}")
        print(f"测试用户ID: {user_id}")
        print(f"{'=' * 60}")

        try:
            request_data = {
                "user_id": user_id,
                "page": 1,
                "page_size": 10
            }

            print(f"\n请求数据:")
            print(json.dumps(request_data, indent=2, ensure_ascii=False))

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    print(f"\n状态码: {response.status}")

                    # 读取原始响应
                    response_text = await response.text()
                    print(f"\n原始响应:")
                    print(response_text)

                    # 尝试解析JSON
                    try:
                        result = await response.json()
                        print(f"\n解析后的JSON:")
                        print(json.dumps(result, indent=2, ensure_ascii=False))

                        # 分析数据结构
                        if isinstance(result, dict):
                            print(f"\n数据结构分析:")
                            print(f"  顶级键: {list(result.keys())}")

                            if "data" in result:
                                data = result["data"]
                                print(f"  data 键: {list(data.keys()) if isinstance(data, dict) else type(data)}")

                                if isinstance(data, dict) and "messages" in data:
                                    messages = data["messages"]
                                    print(f"\n  消息数量: {len(messages)}")
                                    print(f"  消息类型: {type(messages)}")

                                    if messages:
                                        print(f"\n  消息详情:")
                                        for i, msg in enumerate(messages[:3], 1):  # 只显示前3条
                                            print(f"\n  --- 消息 {i} ---")
                                            print(f"     类型: {type(msg)}")
                                            if isinstance(msg, dict):
                                                print(f"     键: {list(msg.keys())}")
                                                print(f"     完整数据:")
                                                print(json.dumps(msg, indent=4, ensure_ascii=False))
                                            else:
                                                print(f"     值: {msg}")
                    except json.JSONDecodeError as e:
                        print(f"\nJSON解析失败: {e}")

        except Exception as e:
            print(f"\n请求异常: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_history_4_agent())
