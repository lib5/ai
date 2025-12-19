#!/usr/bin/env python3
"""
测试图像输入的递增steps功能
"""
import asyncio
import aiohttp
import json
import base64

async def test_image_input():
    """测试图像输入的流式响应"""
    print("=" * 60)
    print("测试图像输入的递增Steps流式响应")
    print("=" * 60)

    # 创建一个简单的红色图像（1x1像素）
    red_pixel = base64.b64encode(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    ).decode('utf-8')

    request_data = {
        "user_id": "test_user_image",
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
            print(f"发送图像+文本请求到: {url}")
            async with session.post(url, json=request_data) as response:
                print(f"响应状态: {response.status}")
                print(f"响应头 Content-Type: {response.headers.get('Content-Type')}")

                if response.status == 200:
                    print("\n收到流式响应，steps递增情况:\n")

                    step_count = 0
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line:
                            try:
                                data = json.loads(line)
                                if 'data' in data and 'steps' in data['data']:
                                    steps = data['data']['steps']
                                    current_step_count = len(steps)

                                    print(f"\n第 {current_step_count} 次响应:")
                                    print(f"  - Steps数量: {current_step_count}")
                                    print(f"  - 最新step: {steps[-1]['tool_type']} ({steps[-1]['tool_status']})")

                                    if current_step_count > step_count:
                                        print(f"  ✓ Steps递增正常: {step_count} -> {current_step_count}")
                                    else:
                                        print(f"  ✗ Steps未递增")

                                    step_count = current_step_count

                            except json.JSONDecodeError:
                                pass

                    print("\n" + "=" * 60)
                    print("图像输入测试完成！")
                    print("=" * 60)
                else:
                    error_text = await response.text()
                    print(f"请求失败: {response.status} - {error_text}")

        except Exception as e:
            print(f"请求异常: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_image_input())
