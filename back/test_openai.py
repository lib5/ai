#!/usr/bin/env python3
"""
OpenAI 接口直接测试脚本

直接调用 OpenAI API，无需通过 FastAPI 服务器。
在这个文件中维护你的 messages，然后运行脚本查看 OpenAI 的响应。
"""

import asyncio
import json
import sys
from typing import List, Dict, Any

# 导入项目中的 OpenAI 服务
import os
from dotenv import load_dotenv

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from services.azure_openai_service import OpenAIService


class OpenAIChatTester:
    """OpenAI 聊天接口测试器"""

    def __init__(self):
        # 从环境变量获取配置
        self.api_key = os.getenv("OPENAI_API_KEY", "sk-hk69mLmsHF6FfIM8cPn2Zitfk0Jca6suzwIptZymPn6h1u6x")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://llm.onerouter.pro/v1")
        self.model = os.getenv("OPENAI_MODEL", "gemini-3-flash-preview")

        print(f"🔑 OpenAI 配置:")
        print(f"   API Key: {self.api_key[:20]}...")
        print(f"   Base URL: {self.base_url}")
        print(f"   Model: {self.model}")

        # 初始化 OpenAI 服务
        self.openai_service = OpenAIService(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        发送聊天请求到 OpenAI

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            max_tokens: 最大令牌数
            temperature: 温度参数
            stream: 是否使用流式输出

        Returns:
            OpenAI API 响应
        """
        print("\n" + "=" * 80)
        print("🚀 发送请求到 OpenAI")
        print("=" * 80)
        print(f"📝 请求参数:")
        print(f"   Model: {self.model}")
        print(f"   Max Tokens: {max_tokens}")
        print(f"   Temperature: {temperature}")
        print(f"   Stream: {stream}")
        print(f"\n📄 消息列表:")
        for i, msg in enumerate(messages, 1):
            print(f"   {i}. [{msg['role']}] {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")

        print("\n" + "=" * 80)
        print("📊 OpenAI 响应:")
        print("=" * 80)

        try:
            if stream:
                # 流式输出
                print("🔄 流式响应:")
                full_content = ""
                async for chunk in self.openai_service.chat_completion_stream(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                ):
                    print(chunk, end="", flush=True)
                    full_content += chunk

                print("\n")  # 换行
                return {"choices": [{"message": {"content": full_content}}]}

            else:
                # 普通响应
                response = await self.openai_service.chat_completion(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=stream
                )

                # 美化输出
                print(json.dumps(response, indent=2, ensure_ascii=False))

                return response

        except Exception as e:
            print(f"\n❌ 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}


# =============================================================================
# 在这里维护你的测试消息
# =============================================================================

# OpenAI 消息格式： [{"role": "user", "content": "..."}]

# 示例 1: 简单对话
SIMPLE_MESSAGES = [
    {"role": "user", "content": "你好，请介绍一下你自己"}
]

# 示例 2: 多轮对话
MULTI_TURN_MESSAGES = [
    {"role": "user", "content": "我想学习 Python 编程"},
    {"role": "user", "content": "能详细说说变量和数据类型吗？"}
]

# 示例 3: 带系统提示的对话
SYSTEM_PROMPT_MESSAGES = [
    {"role": "system", "content": "你是一个 Python 编程专家，专门帮助初学者学习编程。"},
    {"role": "user", "content": "请解释一下 Python 中的列表和字典的区别"}
]

# 示例 4: 代码生成
CODE_GENERATION_MESSAGES = [
    {"role": "user", "content": "请写一个 Python 函数，计算两个数的最大公约数"}
]

# 示例 5: 自定义测试 - 在这里修改你的消息
MY_CUSTOM_MESSAGES = [
    {"role": "user", "content": "请解释一下什么是机器学习"},
    {"role": "user", "content": "能举个具体的例子吗？"}
]

# 示例 6: 流式测试
STREAM_MESSAGES = [
    {"role": "user", "content": "请详细解释一下人工智能的发展历史"}
]


async def test_simple_chat():
    """测试简单对话"""
    print("\n" + "=" * 80)
    print("🧪 测试 1: 简单对话")
    print("=" * 80)

    tester = OpenAIChatTester()
    result = await tester.chat(SIMPLE_MESSAGES)
    return result


async def test_multi_turn_chat():
    """测试多轮对话"""
    print("\n" + "=" * 80)
    print("🧪 测试 2: 多轮对话")
    print("=" * 80)

    tester = OpenAIChatTester()
    result = await tester.chat(MULTI_TURN_MESSAGES)
    return result


async def test_system_prompt():
    """测试系统提示"""
    print("\n" + "=" * 80)
    print("🧪 测试 3: 系统提示")
    print("=" * 80)

    tester = OpenAIChatTester()
    result = await tester.chat(SYSTEM_PROMPT_MESSAGES, temperature=0.5)
    return result


async def test_code_generation():
    """测试代码生成"""
    print("\n" + "=" * 80)
    print("🧪 测试 4: 代码生成")
    print("=" * 80)

    tester = OpenAIChatTester()
    result = await tester.chat(CODE_GENERATION_MESSAGES, max_tokens=500)
    return result


async def test_custom():
    """测试自定义消息"""
    print("\n" + "=" * 80)
    print("🧪 测试 5: 自定义消息")
    print("=" * 80)

    tester = OpenAIChatTester()
    result = await tester.chat(MY_CUSTOM_MESSAGES, temperature=0.8)
    return result


async def test_stream():
    """测试流式输出"""
    print("\n" + "=" * 80)
    print("🧪 测试 6: 流式输出")
    print("=" * 80)

    tester = OpenAIChatTester()
    result = await tester.chat(STREAM_MESSAGES, stream=True, max_tokens=800)
    return result


async def main():
    """主函数"""
    print("=" * 80)
    print("🎯 OpenAI 接口直接测试脚本")
    print("=" * 80)
    print("\n📌 使用说明:")
    print("1. 修改上面的 MY_CUSTOM_MESSAGES 来测试你的内容")
    print("2. 运行: python test_openai.py")
    print("3. 查看 OpenAI API 的直接响应")
    print("\n📝 消息格式:")
    print("   [{\"role\": \"user\", \"content\": \"你的问题\"}]")
    print("   支持的角色: system, user, assistant")

    # 检查命令行参数
    test_choice = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"\n🔍 测试模式: {test_choice}")

    tests = {
        # "1": ("简单对话", test_simple_chat),
        "2": ("多轮对话", test_multi_turn_chat),
        # "3": ("系统提示", test_system_prompt),
        # "4": ("代码生成", test_code_generation),
        # "5": ("自定义消息", test_custom),
        # "6": ("流式输出", test_stream),
        # "all": ("所有测试", None)
    }

    if test_choice in tests:
        test_name, test_func = tests[test_choice]
        print(f"\n{'=' * 80}")
        print(f"🧪 正在运行: {test_name}")
        print(f"{'=' * 80}")

        if test_func:
            # 运行单个测试
            result = await test_func()
            if "error" in result:
                print(f"\n❌ 测试失败: {result['error']}")
            else:
                print(f"\n✅ 测试成功")
        else:
            # 运行所有测试
            results = []
            for key, (name, func) in tests.items():
                if key == "all":
                    continue

                print(f"\n\n{'=' * 80}")
                print(f"▶️  运行测试 {key}: {name}")
                print(f"{'=' * 80}")

                result = await func()
                results.append((name, "✅ 成功" if "error" not in result else "❌ 失败"))

                # 延迟避免请求过快
                print("\n⏳ 等待 2 秒...")
                await asyncio.sleep(2)

            # 打印总结
            print("\n" + "=" * 80)
            print("📊 测试总结")
            print("=" * 80)
            for name, status in results:
                print(f"{status} - {name}")
    else:
        print(f"\n❌ 无效的测试选择: {test_choice}")
        print(f"可用选项: {', '.join(tests.keys())}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 脚本异常: {str(e)}")
        import traceback
        traceback.print_exc()