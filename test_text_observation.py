#!/usr/bin/env python3
"""
测试observation字段 - 文本查询
"""
import asyncio
import aiohttp
import json

async def test_text_observation():
    """测试observation字段（文本查询）"""
    print("=" * 60)
    print("测试 observation 字段 - 文本查询")
    print("=" * 60)

    request_data = {
        "user_id": "test_user",
        "query": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "现在几点了？"
                    }
                ]
            }
        ]
    }

    url = "http://localhost:8000/api/chat"

    async with aiohttp.ClientSession() as session:
        try:
            print(f"发送请求到: {url}\n")

            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line:
                            try:
                                data = json.loads(line)
                                if 'data' in data and 'steps' in data['data']:
                                    steps = data['data']['steps']

                                    for step in steps:
                                        print(f"步骤: {step.get('tool_type')}")
                                        print(f"  状态: {step.get('tool_status')}")

                                        # 打印observation字段
                                        if 'observation' in step:
                                            obs = step['observation']
                                            if obs:
                                                print(f"  Observation: {str(obs)[:200]}...")
                                            else:
                                                print(f"  Observation: None")
                                        print()

                            except json.JSONDecodeError:
                                pass

                else:
                    error_text = await response.text()
                    print(f"请求失败: {response.status} - {error_text}")

        except Exception as e:
            print(f"请求异常: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_text_observation())
