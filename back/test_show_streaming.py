#!/usr/bin/env python3
"""
测试字符流式输出 - 显示流式过程
"""
import asyncio
import aiohttp
import json
import time

async def test_character_streaming_demo():
    """演示字符流式输出"""
    print("\n" + "="*80)
    print("🎬 测试字符流式输出 - 实时显示")
    print("="*80 + "\n")

    request_data = {}

    url = "http://localhost:8001/api/chat/char-stream"

    try:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    print("📡 连接成功，开始接收流式数据...\n")
                    print("-"*80)

                    char_count = 0
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line:
                            char_count += 1

                            try:
                                data = json.loads(line)
                                print(f"\n📦 第{char_count}个数据包 (JSON):")
                                print(json.dumps(data, ensure_ascii=False, indent=2)[:200])
                            except:
                                # 如果不是JSON，说明是流式文本内容
                                print(f"\n✍️  流式文本内容: {line}")
                                # 逐字符显示
                                for char in line:
                                    print(char, end='', flush=True)
                                    await asyncio.sleep(0.01)
                                print()

                    elapsed = time.time() - start_time
                    print("-"*80)
                    print(f"\n✅ 接收完成!")
                    print(f"   ⏱️  总耗时: {elapsed:.2f}秒")
                    print(f"   📦 数据包数: {char_count}")
                    print("\n" + "="*80)

                else:
                    print(f"❌ 请求失败: {response.status}")

    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_character_streaming_demo())