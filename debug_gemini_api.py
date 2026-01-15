#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Gemini API调用
"""

import asyncio
import aiohttp
import json

async def test_gemini_api():
    """测试Gemini API调用"""
    api_key = "sk-i1OxltYB6g1sc4WFeLeqg088af7tDhiWFBrqbyvlDB30hmKF"
    base_url = "https://wsa.147ai.cn"
    model = "gemini-3-flash-preview-low"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 简单的测试prompt
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"type": "text", "text": "你好，请简单回复一下"}
                ]
            }
        ],
        "generationConfig": {
            "thinkingConfig": {
                "thinkingBudget": 1
            }
        }
    }

    api_url = f"{base_url}/v1beta/models/{model}:generateContent"

    print(f"API URL: {api_url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    timeout = aiohttp.ClientTimeout(total=60)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                api_url,
                json=payload,
                headers=headers
            ) as resp:

                print(f"\n状态码: {resp.status}")
                print(f"响应头: {dict(resp.headers)}")

                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"错误响应: {error_text}")
                    return

                print(f"\n✅ API响应正常，开始接收流式数据...")

                async for line in resp.content:
                    if line:
                        line = line.decode('utf-8').strip()
                        print(f"原始行: {line}")

                        # 跳过空行和事件类型声明
                        if not line or line.startswith(':'):
                            continue

                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                print("\n完成")
                                break

                            try:
                                data = json.loads(data_str)
                                print(f"\n解析的数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
                            except json.JSONDecodeError as e:
                                print(f"\n⚠️ 解析JSON失败: {e}")
                                print(f"原始数据: {data_str[:200]}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini_api())
