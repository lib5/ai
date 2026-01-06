#!/usr/bin/env python3
"""
简单的流式输出测试 - 逐字显示文本
"""
import asyncio
import aiohttp
import json

async def test_character_streaming():
    """测试逐字流式输出"""
    print("=" * 60)
    print("测试流式输出 - 逐字显示")
    print("=" * 60)

    request_data = {
        "user_id": "test_stream_001",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "你好，请介绍一下自己"}
                ]
            }
        ]
    }

    url = "http://localhost:8000/api/chat"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    print("\n📥 开始接收流式数据 (逐字显示):")
                    print("-" * 60)

                    char_count = 0
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line:
                            char_count += 1
                            # 解析JSON并显示文本内容
                            try:
                                data = json.loads(line)
                                steps = data.get('data', {}).get('steps', [])
                                if steps:
                                    step = steps[0]
                                    present_content = step.get('present_content', '')
                                    if present_content:
                                        # 逐字显示文本内容
                                        for char in present_content:
                                            print(char, end='', flush=True)
                                            await asyncio.sleep(0.02)  # 20ms延迟
                                        print()  # 换行
                            except json.JSONDecodeError:
                                # 如果不是JSON，直接显示
                                print(f"\n⚠️  非JSON数据: {line[:100]}...")

                    print("-" * 60)
                    print(f"✅ 流式输出完成，共接收 {char_count} 行数据")
                    return {"status": "success"}

                else:
                    error_text = await response.text()
                    print(f"❌ 请求失败: {response.status}")
                    print(error_text)
                    return {"error": error_text}

    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_character_streaming())
    print(f"\n测试结果: {result}")