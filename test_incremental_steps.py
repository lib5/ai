#!/usr/bin/env python3
"""
测试递增steps的流式响应功能
"""
import asyncio
import aiohttp
import json

async def test_incremental_steps():
    """测试流式响应中的steps是否递增"""
    print("=" * 60)
    print("测试递增Steps的流式响应")
    print("=" * 60)

    request_data = {
        "user_id": "test_user",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "请告诉我当前时间"}
                ]
            }
        ]
    }

    url = "http://localhost:8000/api/chat"

    async with aiohttp.ClientSession() as session:
        try:
            print(f"发送请求到: {url}")
            async with session.post(url, json=request_data) as response:
                print(f"响应状态: {response.status}")
                print(f"响应头 Content-Type: {response.headers.get('Content-Type')}")

                if response.status == 200:
                    print("\n收到流式响应，steps递增情况:\n")

                    step_count = 0
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        print(f"收到行: {line[:100]}...")  # 调试日志
                        if line:
                            try:
                                # 解析JSON响应
                                data = json.loads(line)

                                # 提取steps
                                if 'data' in data and 'steps' in data['data']:
                                    steps = data['data']['steps']
                                    current_step_count = len(steps)

                                    # 显示递增情况
                                    print(f"\n第 {current_step_count} 次响应:")
                                    print(f"  - Steps数量: {current_step_count}")
                                    print(f"  - 最新step: {steps[-1]['tool_type']} ({steps[-1]['tool_status']})")

                                    if current_step_count > step_count:
                                        print(f"  ✓ Steps递增正常: {step_count} -> {current_step_count}")
                                    else:
                                        print(f"  ✗ Steps未递增")

                                    step_count = current_step_count

                            except json.JSONDecodeError as e:
                                print(f"JSON解析错误: {e}")

                    print("\n" + "=" * 60)
                    print("测试完成！")
                    print("=" * 60)
                else:
                    error_text = await response.text()
                    print(f"请求失败: {response.status} - {error_text}")

        except Exception as e:
            print(f"请求异常: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_incremental_steps())
