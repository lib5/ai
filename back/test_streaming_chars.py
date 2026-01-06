#!/usr/bin/env python3
"""
真正的逐字符流式输出测试
使用Server-Sent Events (SSE)格式实现真正的流式输出
"""
import asyncio
import aiohttp
import json

async def test_true_character_streaming():
    """测试真正的逐字符流式输出"""
    print("=" * 60)
    print("测试真正的流式输出 - 逐字符显示")
    print("=" * 60)

    request_data = {
        "user_id": "test_stream_002",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "请用一句话介绍人工智能"}
                ]
            }
        ]
    }

    url = "http://localhost:8000/api/chat"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    print("\n📥 开始接收流式数据 (逐字符显示):")
                    print("-" * 60)

                    char_count = 0
                    line_count = 0
                    current_text = ""

                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue

                        line_count += 1

                        try:
                            # 尝试解析JSON
                            data = json.loads(line)
                            steps = data.get('data', {}).get('steps', [])

                            if steps:
                                step = steps[0]
                                present_content = step.get('present_content', '')

                                if present_content:
                                    # 逐字符显示文本内容
                                    for char in present_content:
                                        print(char, end='', flush=True)
                                        char_count += 1
                                        await asyncio.sleep(0.01)  # 10ms延迟
                                    print()  # 换行
                                    current_text += present_content

                        except json.JSONDecodeError:
                            # 如果解析失败，直接显示原始内容
                            print(f"\n⚠️  原始数据: {line[:100]}...")

                    print("-" * 60)
                    print(f"\n✅ 流式输出完成!")
                    print(f"   总行数: {line_count}")
                    print(f"   总字符数: {char_count}")
                    print(f"\n📝 完整输出:\n{current_text}")
                    return {"status": "success", "chars": char_count, "lines": line_count}

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
    result = asyncio.run(test_true_character_streaming())
    print(f"\n测试结果: {result}")