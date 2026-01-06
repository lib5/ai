#!/usr/bin/env python3
"""
寻找有实际聊天数据的用户ID
"""

import asyncio
import json
import aiohttp
from config import settings

async def find_user_with_data():
    """寻找有实际聊天数据的用户ID"""
    print("=" * 80)
    print("寻找有实际聊天数据的用户ID")
    print("=" * 80)

    # 从日志中提取的可能的用户ID格式
    possible_user_ids = [
        # 标准UUID格式
        "550e8400-e29b-41d4-a716-446655440000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "6ba7b811-9dad-11d1-80b4-00c04fd430c8",

        # 从日志中看到的用户信息反推
        "user_18600241181",
        "test_user_2e3b6b0f",
        "13632598013",  # 从日志中的电话号反推
        "18600241181",  # 从日志中的用户ID反推
    ]

    # 尝试不同的分页参数
    test_params = [
        {"page": 1, "page_size": 10},
        {"page": 1, "page_size": 50},
        {"page": 1, "page_size": 100},
    ]

    base_url = settings.chat_api_base_url
    url = f"{base_url}/api/v1/chat/history_4_agent"

    print(f"测试URL: {url}")

    for user_id in possible_user_ids:
        print(f"\n{'=' * 60}")
        print(f"测试用户ID: {user_id}")
        print(f"{'=' * 60}")

        for params in test_params:
            try:
                request_data = {
                    "user_id": user_id,
                    **params
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:

                        print(f"\n  参数: {params}")
                        print(f"  状态码: {response.status}")

                        if response.status == 200:
                            result = await response.json()
                            messages = result.get("data", {}).get("messages", [])

                            print(f"  消息数量: {len(messages)}")

                            if messages:
                                print(f"  ✅ 找到数据！")

                                # 显示前2条消息的摘要
                                for i, msg in enumerate(messages[:2], 1):
                                    if isinstance(msg, dict):
                                        role = msg.get("role", "unknown")
                                        print(f"    消息 {i} - 角色: {role}")

                                        # 显示content摘要
                                        content = msg.get("content", [])
                                        if isinstance(content, list):
                                            for j, item in enumerate(content[:2], 1):
                                                if isinstance(item, dict) and "text" in item:
                                                    text = item["text"]
                                                    print(f"      文本 {j}: {text[:50]}...")

                                        # 显示steps摘要
                                        steps = msg.get("steps", {})
                                        if isinstance(steps, dict) and "assistant_answer" in steps:
                                            answer = steps.get("assistant_answer", "")
                                            print(f"      助手回答: {answer[:50]}...")

                                return user_id, messages
                        else:
                            error_text = await response.text()
                            if "422" not in error_text:  # 避免打印太多UUID错误
                                print(f"  错误: {error_text[:100]}...")

            except Exception as e:
                print(f"  异常: {str(e)}")

    print(f"\n❌ 没有找到有数据的用户ID")

    # 尝试获取所有用户（如果支持）
    print(f"\n尝试获取所有用户...")
    try:
        # 假设有获取所有用户的接口
        all_users_url = f"{base_url}/api/v1/users"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                all_users_url,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    users = await response.json()
                    print(f"找到用户列表: {json.dumps(users, indent=2, ensure_ascii=False)}")
                else:
                    print(f"获取用户列表失败: {response.status}")
    except Exception as e:
        print(f"尝试获取用户列表失败: {str(e)}")

    return None, []

if __name__ == "__main__":
    user_id, messages = asyncio.run(find_user_with_data())
    if user_id:
        print(f"\n🎉 找到有数据的用户: {user_id}")
        print(f"消息数量: {len(messages)}")
    else:
        print(f"\n❌ 未找到有数据的用户")
