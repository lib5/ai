#!/usr/bin/env python3
"""
测试Azure OpenAI API连接
"""

import os
import json
import asyncio
import aiohttp
from dotenv import load_dotenv

# 加载.env文件
load_dotenv('/home/libo/chatapi/.env')

# 获取配置
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1')

print("="*60)
print("Azure OpenAI API 测试")
print("="*60)

print(f"端点: {AZURE_ENDPOINT}")
print(f"API版本: {AZURE_API_VERSION}")
print(f"部署名称: {DEPLOYMENT_NAME}")
print(f"API密钥长度: {len(AZURE_API_KEY) if AZURE_API_KEY else 0}")
print()

# 测试API连接
async def test_api():
    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_API_VERSION}"

    headers = {
        "Authorization": f"Bearer {AZURE_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "max_tokens": 10
    }

    try:
        print("正在测试API连接...")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=30) as response:
                print(f"响应状态: {response.status}")

                if response.status == 200:
                    result = await response.json()
                    print("✓ API连接成功！")
                    print(f"响应内容: {json.dumps(result, indent=2)[:200]}...")
                else:
                    error_text = await response.text()
                    print(f"✗ API调用失败: {response.status}")
                    print(f"错误信息: {error_text[:300]}")

    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_api())
