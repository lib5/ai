#!/usr/bin/env python3
"""
简单的 Prompt 测试脚本

在这个文件中维护你的 messages，然后运行脚本来查看 API 的输出结果。
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any, List


class SimplePromptTester:
    """简单的 Prompt 测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: aiohttp.ClientSession = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def send_chat_request(self, messages: List[Dict[str, Any]], user_id: str = "test_user_001") -> Dict[str, Any]:
        """
        发送聊天请求

        Args:
            messages: 消息列表，每个消息包含 role 和 content
            user_id: 用户ID

        Returns:
            API 响应数据
        """
        # 构建请求数据
        request_data = {
            "user_id": user_id,
            "query": []
        }

        # 转换 messages 为 API 格式
        for msg in messages:
            role = msg.get("role", "user")
            content_type = msg.get("type", "text")  # "text" 或 "image"

            if content_type == "text":
                content_item = {
                    "type": "input_text",
                    "text": msg.get("content", "")
                }
            elif content_type == "image":
                content_item = {
                    "type": "input_image",
                    "image_url": msg.get("content", "")
                }
            else:
                raise ValueError(f"不支持的内容类型: {content_type}")

            request_data["query"].append({
                "role": role,
                "content": [content_item]
            })

        # 发送请求
        url = f"{self.base_url}/api/chat"
        print(f"\n🚀 发送请求到: {url}")
        print(f"📝 请求数据:")
        print(json.dumps(request_data, indent=2, ensure_ascii=False))
        print("\n" + "=" * 80)

        try:
            async with self.session.post(url, json=request_data) as response:
                response_text = await response.text()
                print(f"📊 响应状态码: {response.status}")
                print("\n📄 响应内容:")
                print("=" * 80)

                if response.status == 200:
                    try:
                        response_data = json.loads(response_text)
                        # 美化输出
                        print(json.dumps(response_data, indent=2, ensure_ascii=False))
                        return response_data
                    except json.JSONDecodeError:
                        print("❌ 响应不是有效的 JSON 格式")
                        print(response_text)
                        return {"error": "Invalid JSON response"}
                else:
                    print(f"❌ 请求失败: {response.status}")
                    print(response_text)
                    return {"error": f"HTTP {response.status}", "response": response_text}

        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return {"error": str(e)}


# =============================================================================
# 在这里维护你的测试消息
# =============================================================================

# 示例 1: 简单的文本对话
SIMPLE_TEXT_MESSAGES = [
    {
        "role": "user",
        "type": "text",
        "content": "你好，请介绍一下你自己"
    }
]

# 示例 2: 多轮对话
MULTI_TURN_MESSAGES = [
    {
        "role": "user",
        "type": "text",
        "content": "我想了解 Python 编程"
    },
    {
        "role": "user",
        "type": "text",
        "content": "能详细说说变量和数据类型吗？"
    }
]

# 示例 3: 带图像的消息（需要提供有效的 base64 图像或图像 URL）
IMAGE_MESSAGES = [
    {
        "role": "user",
        "type": "text",
        "content": "请分析这张图片中的内容"
    },
    {
        "role": "user",
        "type": "image",
        "content": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    }
]

# 示例 4: 自定义消息 - 在这里修改你的测试内容
MY_CUSTOM_MESSAGES = [
    {
        "role": "user",
        "type": "text",
        "content": "你能帮我写一个 Python 函数来计算斐波那契数列吗？"
    },
    {
        "role": "user",
        "type": "text",
        "content": "谢谢，现在请添加注释说明每个步骤"
    }
]


async def run_test(test_name: str, messages: List[Dict[str, Any]], user_id: str = "test_user_001"):
    """运行单个测试"""
    print(f"\n{'=' * 80}")
    print(f"🧪 测试: {test_name}")
    print(f"{'=' * 80}")

    async with SimplePromptTester() as tester:
        result = await tester.send_chat_request(messages, user_id)

        # 检查是否有错误
        if "error" in result:
            print(f"\n❌ 测试失败: {result['error']}")
        else:
            print(f"\n✅ 测试成功")

        return result


async def main():
    """主函数 - 运行所有测试"""
    print("=" * 80)
    print("🎯 简单 Prompt 测试脚本")
    print("=" * 80)
    print("\n📌 使用说明:")
    print("1. 修改上面的 MY_CUSTOM_MESSAGES 来测试你的内容")
    print("2. 运行: python test_prompt.py")
    print("3. 查看 API 输出结果")

    # 如果有命令行参数，使用它作为服务器 URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"\n🔗 使用服务器: {base_url}")

    tests = [
        ("简单文本对话", SIMPLE_TEXT_MESSAGES)
    ]

    results = []
    for test_name, messages in tests:
        result = await run_test(test_name, messages)
        results.append((test_name, result))

        # 在测试之间添加延迟，避免请求过快
        print("\n⏳ 等待 2 秒...")
        await asyncio.sleep(2)

    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    for test_name, result in results:
        status = "✅ 成功" if "error" not in result else "❌ 失败"
        print(f"{status} - {test_name}")

    print("\n🎉 所有测试完成!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 脚本异常: {str(e)}")
        import traceback
        traceback.print_exc()