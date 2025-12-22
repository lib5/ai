#!/usr/bin/env python3
"""
测试聊天历史功能的脚本
"""

import asyncio
import uuid
from services.true_react_agent import TrueReActAgent

async def test_fetch_chat_history():
    """测试获取聊天历史功能"""
    print("=" * 80)
    print("测试聊天历史获取功能")
    print("=" * 80)

    # 创建 ReAct Agent 实例
    agent = TrueReActAgent()
    await agent.initialize()

    # 测试1: 使用有效的UUID
    print("\n1. 测试使用有效UUID (550e8400-e29b-41d4-a716-446655440000)")
    test_user_id = "550e8400-e29b-41d4-a716-446655440000"
    history = await agent.fetch_chat_history(test_user_id)
    print(f"   结果: 获取到 {len(history)} 条历史消息")

    # 测试2: 使用无效的UUID
    print("\n2. 测试使用无效UUID (invalid_user_id)")
    history = await agent.fetch_chat_history("invalid_user_id")
    print(f"   结果: 获取到 {len(history)} 条历史消息")

    # 测试3: 传递包含有效user_id的metadata
    print("\n3. 测试传递包含有效user_id的metadata")
    user_metadata = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "测试用户",
        "city": "北京"
    }
    agent.user_id = None
    if user_metadata and isinstance(user_metadata, dict):
        agent.user_id = user_metadata.get('id')
    print(f"   提取的user_id: {agent.user_id}")

    if agent.user_id:
        agent.chat_history = await agent.fetch_chat_history(agent.user_id, page=1, page_size=5)
        print(f"   结果: 获取到 {len(agent.chat_history)} 条历史消息")

    # 测试4: 传递不包含id的metadata
    print("\n4. 测试传递不包含id的metadata")
    user_metadata = {
        "username": "测试用户",
        "city": "北京"
    }
    agent.user_id = None
    if user_metadata and isinstance(user_metadata, dict):
        agent.user_id = user_metadata.get('id')
    print(f"   提取的user_id: {agent.user_id}")

    if agent.user_id:
        agent.chat_history = await agent.fetch_chat_history(agent.user_id, page=1, page_size=5)
        print(f"   结果: 获取到 {len(agent.chat_history)} 条历史消息")
    else:
        print("   跳过: 没有有效的user_id")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_fetch_chat_history())
