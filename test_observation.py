#!/usr/bin/env python3
"""
测试observation字段
"""
import asyncio
import aiohttp
import json
import base64

async def test_observation():
    """测试observation字段是否正确填充"""
    print("=" * 60)
    print("测试 observation 字段")
    print("=" * 60)

    # 创建一个简单的红色图像（1x1像素）
    red_pixel = base64.b64encode(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    ).decode('utf-8')

    request_data = {
        "user_id": "test_user",
        "query": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{red_pixel}"
                    },
                    {
                        "type": "input_text",
                        "text": "请描述这张图片"
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
    asyncio.run(test_observation())
