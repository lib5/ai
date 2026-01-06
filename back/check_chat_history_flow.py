#!/usr/bin/env python3
"""
检查聊天历史获取的完整流程
"""

import asyncio
import json
from services.true_react_agent import true_react_agent

async def check_chat_history_flow():
    """检查聊天历史获取的完整流程"""
    print("=" * 80)
    print("检查聊天历史获取的完整流程")
    print("=" * 80)

    # 初始化ReAct Agent
    print("\n1. 初始化ReAct Agent...")
    try:
        await true_react_agent.initialize()
        print("✅ ReAct Agent 初始化成功")
    except Exception as e:
        print(f"❌ ReAct Agent 初始化失败: {str(e)}")
        return

    # 测试不同的用户ID
    test_user_ids = [
        "550e8400-e29b-41d4-a716-446655440000",  # 测试中的UUID
    ]

    for user_id in test_user_ids:
        print(f"\n{'=' * 60}")
        print(f"测试用户ID: {user_id}")
        print(f"{'=' * 60}")

        # 设置用户metadata
        user_metadata = {
            "id": user_id,
            "username": "测试用户",
            "city": "北京"
        }

        # 调用fetch_chat_history方法
        print(f"\n2. 调用 fetch_chat_history 方法...")
        try:
            chat_history = await true_react_agent.fetch_chat_history(user_id, page=1, page_size=10)
            print(f"✅ fetch_chat_history 返回:")
            print(f"   类型: {type(chat_history)}")
            print(f"   长度: {len(chat_history)}")
            print(f"   内容: {json.dumps(chat_history, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"❌ fetch_chat_history 失败: {str(e)}")
            chat_history = []

        # 模拟_format_chat_history的处理
        print(f"\n3. 模拟 _format_chat_history 处理...")
        if chat_history:
            formatted_history = true_react_agent._format_chat_history(chat_history)
            print(f"✅ 格式化后的历史:")
            print(formatted_history)
        else:
            print(f"⚠️  聊天历史为空，无法格式化")

        # 检查是否有其他地方存储了对话历史
        print(f"\n4. 检查 agent.chat_history 属性...")
        if hasattr(true_react_agent, 'chat_history'):
            print(f"   agent.chat_history 类型: {type(true_react_agent.chat_history)}")
            print(f"   agent.chat_history 长度: {len(true_react_agent.chat_history)}")
            if true_react_agent.chat_history:
                print(f"   agent.chat_history 内容:")
                print(json.dumps(true_react_agent.chat_history, indent=2, ensure_ascii=False))
        else:
            print(f"   agent.chat_history 属性不存在")

    print("\n" + "=" * 80)
    print("检查完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(check_chat_history_flow())
