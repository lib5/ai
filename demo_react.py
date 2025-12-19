#!/usr/bin/env python3
"""
演示真正的ReAct模式 - 不同查询类型的行为
"""

import asyncio
import aiohttp
import json

async def send_query(query_text: str, user_id: str = "demo_user"):
    """发送查询并显示结果"""
    url = "http://localhost:8000/api/chat"

    request_data = {
        "user_id": user_id,
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": query_text}
                ]
            }
        ]
    }

    print(f"\n{'='*70}")
    print(f"查询: {query_text}")
    print(f"{'='*70}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    content = await response.text()

                    # 解析SSE响应
                    full_json = ""
                    for line in content.split('\n'):
                        line = line.strip()
                        if line.startswith('data: '):
                            try:
                                event_data = json.loads(line[6:])
                                if event_data.get('event') == 'chunk':
                                    full_json += event_data.get('data', '')
                            except:
                                pass

                    if full_json:
                        result = json.loads(full_json)
                        data = result.get('data', {})

                        # 显示答案
                        print(f"\n📝 AI回答:")
                        print(f"   {data.get('answer', '')}")

                        # 显示推理过程
                        print(f"\n🧠 ReAct推理过程:")
                        steps = data.get('reasoning_trace', [])
                        for step in steps:
                            step_type = step.get('type', '').upper()
                            content = step.get('content', '')

                            if step_type == 'THOUGHT':
                                print(f"   💭 {step_type}: {content[:80]}...")
                            elif step_type == 'ACTION':
                                tool_name = step.get('tool_name', 'N/A')
                                print(f"   🎯 {step_type}: 选择工具 '{tool_name}' - {content}")
                            elif step_type == 'OBSERVATION':
                                print(f"   👁️  {step_type}: 获得结果")

                        # 显示迭代次数
                        print(f"\n🔄 迭代次数: {data.get('iterations', 0)}")

                else:
                    print(f"❌ 错误: {response.status}")
                    error_text = await response.text()
                    print(f"   {error_text}")

        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")

async def main():
    """演示不同类型的ReAct行为"""
    print("\n" + "="*70)
    print("🚀 真正的 ReAct 模式演示")
    print("="*70)
    print("\n这个演示将展示ReAct Agent如何自主决定使用不同工具")
    print("根据查询类型，Agent会智能选择最合适的行动。")

    # 测试用例
    test_cases = [
        ("简单对话 - 问候", "你好！"),
        ("简单对话 - 自我介绍", "请介绍一下你自己"),
        ("搜索查询", "搜索Python编程语言的特点"),
        ("搜索查询", "查找人工智能的应用"),
        ("时间查询", "现在是什么时间？"),
    ]

    for description, query in test_cases:
        print(f"\n\n▶️  测试: {description}")
        await send_query(query, f"user_{len(test_cases)}")

    print("\n\n" + "="*70)
    print("✅ 演示完成!")
    print("="*70)
    print("\n关键观察:")
    print("  1. 简单对话 → 直接回答 (direct_answer)")
    print("  2. 搜索请求 → 使用网络搜索 (web_search)")
    print("  3. 时间查询 → 获取当前时间 (get_current_time)")
    print("  4. 所有查询都是1次迭代 (智能停止)")
    print("  5. 完整保留推理轨迹 (Thought → Action → Observation)")

if __name__ == "__main__":
    asyncio.run(main())
