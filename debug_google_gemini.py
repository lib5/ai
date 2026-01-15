#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Google Gemini API调用 (修正版)
"""

import asyncio
import aiohttp
import json

async def test_google_gemini_api():
    """测试Google Gemini API调用 (修正版)"""
    api_key = "AQ.Ab8RN6J9GWr-zLevwtQ-kjFdSlZRy2wIabqdn4sNbszpacBJ0A"  # ⚠️ 请使用你在Google AI Studio获取的真实有效Key
    base_url = "https://generativelanguage.googleapis.com"
    model = "gemini-3-flash-preview"  # 建议使用公开可用的模型进行测试

    # ⚠️ 重要变更：使用Bearer Token认证，而非URL参数
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"  # 正确的认证方式
    }

    # 简化测试负载
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "你好，请用一句话介绍一下你自己。"}  # 更明确的指令
                ]
            }
        ]
        # 移除了 generationConfig，如需设置可参考官方文档
    }

    # ⚠️ 重要变更：更新URL路径
    # 为预览模型使用正确的端点。对于gemini-1.5-pro等非预览模型，可使用 `:generateContent`
    api_url = f"{base_url}/v1beta/models/{model}:streamGenerateContent"
    # 或者对于稳定模型（如gemini-1.5-pro）：
    # api_url = f"{base_url}/v1/models/{model}:generateContent"

    print(f"API URL: {api_url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    timeout = aiohttp.ClientTimeout(total=60)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(api_url, json=payload, headers=headers) as resp:

                print(f"\n状态码: {resp.status}")
                print(f"响应头: {dict(resp.headers)}")

                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"错误响应: {error_text}")
                    return

                print(f"\n✅ API响应正常")

                # 注意：由于使用了 `streamGenerateContent`，响应是流式的
                # 我们需要按行读取并解析JSON
                full_response = ""
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line:  # 忽略空行
                        # 流式响应每行是一个JSON对象，前缀为 "data: "
                        if line.startswith("data: "):
                            json_str = line[6:]  # 去掉 "data: " 前缀
                            try:
                                chunk_data = json.loads(json_str)
                                # 提取文本部分
                                if "candidates" in chunk_data and chunk_data["candidates"]:
                                    for part in chunk_data["candidates"][0].get("content", {}).get("parts", []):
                                        if "text" in part:
                                            full_response += part["text"]
                            except json.JSONDecodeError:
                                print(f"解析JSON块时出错: {json_str}")

                print(f"\n完整响应内容:\n{full_response}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

# 运行测试（如果在异步环境中）
if __name__ == "__main__":
    asyncio.run(test_google_gemini_api())