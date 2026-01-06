#!/usr/bin/env python3
"""
流式输出演示 - 显示真正的逐字符流式传输
"""
import asyncio
import aiohttp
import json
import time

async def demo_streaming():
    """演示流式输出效果"""
    print("\n" + "="*80)
    print("🎬 Chat API 流式输出演示")
    print("="*80)
    print("\n📝 请求: 请用一句话介绍人工智能")
    print("\n📡 响应 (逐字符显示):\n")
    print("-"*80)

    request_data = {
        "user_id": "demo_user",
        "query": [{"role": "user", "content": [{"type": "input_text", "text": "请用一句话介绍人工智能"}]}]
    }

    url = "http://localhost:8000/api/chat"

    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        full_text = ""
        async with session.post(url, json=request_data) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line:
                    try:
                        data = json.loads(line)
                        steps = data.get('data', {}).get('steps', [])
                        if steps:
                            for step in steps:
                                present = step.get('present_content', '')
                                if present:
                                    # 逐字符显示文本内容
                                    for char in present:
                                        print(char, end='', flush=True)
                                        full_text += char
                                        await asyncio.sleep(0.02)  # 20ms延迟
                    except:
                        # 非JSON行，可能是纯文本
                        for char in line:
                            if char.isprintable() or char in '，。！？；：""''()（）【】《》':
                                print(char, end='', flush=True)
                                full_text += char
                                await asyncio.sleep(0.02)

        elapsed = (time.time() - start_time) * 1000
        print("\n" + "-"*80)
        print(f"\n✅ 响应完成! 耗时: {elapsed:.0f}ms")
        print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(demo_streaming())