#!/usr/bin/env python3
"""
直接测试Azure OpenAI API调用
"""

import asyncio
import sys
sys.path.append('/home/libo/chatapi')

from services.azure_openai_service import AzureOpenAIService
from config import settings

async def test_azure_openai():
    """测试Azure OpenAI API调用"""

    print("=" * 80)
    print("测试Azure OpenAI API")
    print("=" * 80)
    print(f"\n配置信息:")
    print(f"  Endpoint: {settings.azure_endpoint}")
    print(f"  API Key: {settings.azure_api_key[:20]}...")
    print(f"  API Version: {settings.azure_api_version}")
    print(f"  Deployment: {settings.azure_deployment_name}")
    print()

    # 创建Azure OpenAI服务实例
    azure_service = AzureOpenAIService(
        endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key,
        api_version=settings.azure_api_version,
        deployment_name=settings.azure_deployment_name
    )

    try:
        print("正在调用Azure OpenAI API...")
        messages = [
            {"role": "system", "content": "你是一个智能的AI助手。"},
            {"role": "user", "content": "你好，请介绍一下你自己"}
        ]

        response = await azure_service.chat_completion(
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )

        print("\n✅ API调用成功!")
        print(f"\n响应内容:")
        print(json.dumps(response, indent=2, ensure_ascii=False))

        # 提取答案
        if "choices" in response and len(response["choices"]) > 0:
            answer = response["choices"][0].get("message", {}).get("content", "")
            print(f"\n📝 模型回答:")
            print(f"{'=' * 80}")
            print(answer)
            print(f"{'=' * 80}")

    except Exception as e:
        print(f"\n❌ API调用失败!")
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)

if __name__ == "__main__":
    import json
    asyncio.run(test_azure_openai())
