#!/usr/bin/env python3
"""
简单的流式输出测试
验证步骤是否逐步显示，而不是一次性返回
"""

import asyncio
import aiohttp
import json
import time

async def test_streaming_simple():
    """测试简单的流式输出"""
    url = "http://localhost:8000/api/chat"

    request_data = {
        "user_id": "test_user_simple",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "老李的电话多少"}
                ]
            }
        ],
        "metadata": {
            "user": {
                "id": "test_user_simple",
                "username": "test_user",
                "city": "上海"
            }
        }
    }

    print("=" * 60)
    print("开始流式输出测试")
    print("=" * 60)
    print(f"\n发送请求到: {url}")
    print(f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}\n")

    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=request_data) as response:
            print(f"响应状态: {response.status}\n")

            if response.status == 200:
                step_count = 0
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            step_count += 1
                            current_time = time.time() - start_time

                            print(f"[{current_time:.2f}s] 步骤 {step_count}:")
                            if 'data' in data and 'steps' in data['data']:
                                steps = data['data']['steps']
                                if steps:
                                    latest_step = steps[-1]
                                    step_type = latest_step.get('tool_type', 'Unknown')

                                    # 打印完整的字段信息
                                    print(f"  message_id: {latest_step.get('message_id', 'N/A')}")
                                    print(f"  present_content: {latest_step.get('present_content', 'N/A')}")
                                    print(f"  tool_type: {step_type}")

                                    # 如果不是Finish步骤，显示更多字段
                                    if step_type != 'Finish':
                                        print(f"  parameters: {latest_step.get('parameters', 'N/A')}")
                                        print(f"  tool_status: {latest_step.get('tool_status', 'Unknown')}")
                                        if latest_step.get('observation'):
                                            print(f"  observation: {str(latest_step.get('observation'))[:100]}")
                                        if latest_step.get('execution_duration'):
                                            print(f"  execution_duration: {latest_step.get('execution_duration')}ms")
                            print()

                        except json.JSONDecodeError:
                            continue

                print(f"\n{'='*60}")
                print(f"测试完成，总用时: {time.time() - start_time:.2f}s")
                print(f"总共接收 {step_count} 个数据块")
                print(f"{'='*60}\n")
            else:
                error_text = await response.text()
                print(f"请求失败: {response.status} - {error_text}")

if __name__ == "__main__":
    asyncio.run(test_streaming_simple())
