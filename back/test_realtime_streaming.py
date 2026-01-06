#!/usr/bin/env python3
"""
实时显示流式输出 - 演示真正的逐字符流式传输
"""
import asyncio
import aiohttp
import json
import time
import sys

async def test_realtime_streaming():
    """实时流式输出测试 - 显示每个字符的到达时间"""
    print("\n" + "="*80)
    print("🚀 实时流式输出测试 - 逐字符显示 (显示时间戳)")
    print("="*80 + "\n")

    request_data = {
        "user_id": "test_realtime_001",
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
            start_time = time.time()
            print(f"⏰ 开始时间: {time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"{'-'*80}\n")

            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    char_count = 0
                    byte_count = 0

                    async for chunk in response.content:
                        byte_count += len(chunk)
                        chunk_str = chunk.decode('utf-8', errors='ignore')

                        # 显示每个字符
                        for char in chunk_str:
                            if char.strip():  # 只显示非空白字符
                                elapsed = (time.time() - start_time) * 1000
                                print(f"⏱️  {elapsed:8.1f}ms | 📝 字符: {repr(char):6s} | 累计: {char_count+1:3d} 字符 | {byte_count:5d} 字节", end='\r')
                                char_count += 1

                                # 对于可见字符，也显示在屏幕上
                                if char.isprintable() or char in '，。！？；：':
                                    sys.stdout.write(char)
                                    sys.stdout.flush()

                    print(f"\n{'-'*80}")
                    elapsed = (time.time() - start_time) * 1000
                    print(f"\n✅ 传输完成!")
                    print(f"   ⏱️  总耗时: {elapsed:.1f}ms")
                    print(f"   📊 总字符数: {char_count}")
                    print(f"   📦 总字节数: {byte_count}")
                    print(f"   🚀 平均速度: {byte_count/elapsed*1000:.0f} 字节/秒")
                    print("\n" + "="*80)

                else:
                    print(f"❌ 请求失败: {response.status}")

    except Exception as e:
        print(f"\n❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_realtime_streaming())