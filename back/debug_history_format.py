#!/usr/bin/env python3
"""
调试历史消息格式 - 打印原始数据结构
"""

import asyncio
import json
import aiohttp
from config import settings

async def debug_history_format():
    """调试历史消息的原始格式"""
    print("=" * 80)
    print("调试历史消息原始格式")
    print("=" * 80)

    # 尝试不同的用户ID
    test_user_ids = [
        "550e8400-e29b-41d4-a716-446655440000",  # 测试中的UUID
        "user_123",  # 简单用户ID
    ]

    for user_id in test_user_ids:
        print(f"\n{'=' * 60}")
        print(f"测试用户ID: {user_id}")
        print(f"{'=' * 60}")

        try:
            # 调用获取历史接口
            url = f"{settings.chat_api_base_url}/api/v1/chat/history"
            request_data = {
                "user_id": user_id,
                "page": 1,
                "page_size": 10
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    print(f"状态码: {response.status}")

                    if response.status == 200:
                        result = await response.json()
                        print(f"\n完整响应:")
                        print(json.dumps(result, indent=2, ensure_ascii=False))

                        if "data" in result and "messages" in result["data"]:
                            messages = result["data"]["messages"]
                            print(f"\n获取到 {len(messages)} 条消息:")

                            for i, msg in enumerate(messages, 1):
                                print(f"\n--- 消息 {i} ---")
                                print(f"原始数据:")
                                print(json.dumps(msg, indent=2, ensure_ascii=False))

                                # 分析消息结构
                                role = msg.get("role", "unknown")
                                print(f"\n分析:")
                                print(f"  角色: {role}")
                                print(f"  字段: {list(msg.keys())}")

                                if role == "assistant":
                                    print(f"  助手消息详细分析:")
                                    # 检查所有可能包含答案的字段
                                    for key, value in msg.items():
                                        if key in ['content', 'steps', 'answer', 'text', 'response', 'message']:
                                            print(f"    {key}: {type(value)} = {value}")
                    else:
                        error_text = await response.text()
                        print(f"错误响应: {error_text}")

        except Exception as e:
            print(f"异常: {str(e)}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_history_format())
