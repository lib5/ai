"""
聊天接口使用示例
演示如何使用 Azure OpenAI GPT-4.1 的聊天 API
"""

import asyncio
import aiohttp
import base64
import json

# 示例图像（1x1 像素的 PNG）
SAMPLE_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

async def example_text_only():
    """示例 1: 纯文本聊天"""
    print("\n" + "=" * 60)
    print("示例 1: 纯文本聊天")
    print("=" * 60)

    request_data = {
        "user_id": "user_001",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "你好，请介绍一下你自己"}
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/chat", json=request_data) as response:
            result = await response.json()
            print(f"请求 ID: {result.get('requestId')}")
            print(f"状态: {result.get('message')}")
            print(f"步骤数: {len(result.get('data', {}).get('steps', []))}")

            # 打印所有步骤
            for i, step in enumerate(result.get('data', {}).get('steps', []), 1):
                print(f"\n步骤 {i}:")
                print(f"  内容: {step.get('present_content')}")
                print(f"  工具: {step.get('tool_type')}")
                print(f"  状态: {step.get('tool_status')}")
                if step.get('observation'):
                    print(f"  结果: {step.get('observation')}")
                if step.get('execution_duration'):
                    print(f"  耗时: {step.get('execution_duration')}ms")

async def example_text_and_image():
    """示例 2: 文本和图像混合输入"""
    print("\n" + "=" * 60)
    print("示例 2: 文本和图像混合输入")
    print("=" * 60)

    request_data = {
        "user_id": "user_002",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "这是什么图像？请描述一下。"},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{SAMPLE_IMAGE}"}
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/chat", json=request_data) as response:
            result = await response.json()
            print(f"请求 ID: {result.get('requestId')}")
            print(f"状态: {result.get('message')}")

            # 打印关键步骤
            steps = result.get('data', {}).get('steps', [])
            for step in steps:
                if step.get('tool_type') == 'AzureOpenAI':
                    print(f"\nAI 响应:")
                    print(f"  {step.get('observation', 'N/A')}")
                    print(f"  耗时: {step.get('execution_duration', 0)}ms")

async def example_conversation():
    """示例 3: 多轮对话"""
    print("\n" + "=" * 60)
    print("示例 3: 多轮对话")
    print("=" * 60)

    request_data = {
        "user_id": "user_003",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "什么是机器学习？"}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "它有哪些应用场景？"}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "能给我一些学习建议吗？"}
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/chat", json=request_data) as response:
            result = await response.json()
            print(f"请求 ID: {result.get('requestId')}")
            print(f"总步骤数: {len(result.get('data', {}).get('steps', []))}")

            # 计算总耗时
            total_duration = sum(
                step.get('execution_duration', 0)
                for step in result.get('data', {}).get('steps', [])
            )
            print(f"总耗时: {total_duration}ms")

async def example_streaming():
    """示例 4: 流式响应"""
    print("\n" + "=" * 60)
    print("示例 4: 流式响应")
    print("=" * 60)

    request_data = {
        "user_id": "user_004",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "请用流式方式详细介绍一下深度学习的发展历史"}
                ]
            }
        ]
    }

    print("接收流式数据...")
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/chat", json=request_data) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line:
                    try:
                        data = json.loads(line)
                        if 'event' in data:
                            print(f"\n事件: {data['event']}")
                            if 'data' in data:
                                print(f"数据: {data['data']}")
                    except json.JSONDecodeError:
                        print(line)

async def example_error_handling():
    """示例 5: 错误处理"""
    print("\n" + "=" * 60)
    print("示例 5: 错误处理（无效图像格式）")
    print("=" * 60)

    # 故意使用无效的图像格式
    request_data = {
        "user_id": "user_005",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "这是什么图像？"},
                    {"type": "input_image", "image_url": "invalid_image_data"}
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post("http://localhost:8000/api/chat", json=request_data) as response:
                if response.status == 500:
                    result = await response.json()
                    print("✅ 正确捕获了错误")
                    print(f"错误信息: {result.get('message')}")

                    # 查找错误步骤
                    for step in result.get('data', {}).get('steps', []):
                        if step.get('tool_status') == 'Error':
                            print(f"错误详情: {step.get('observation')}")
                else:
                    print("⚠️  未预期的响应状态")
        except Exception as e:
            print(f"异常: {str(e)}")

async def example_health_check():
    """示例 6: 健康检查"""
    print("\n" + "=" * 60)
    print("示例 6: 健康检查")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8000/health") as response:
            result = await response.json()
            print(f"服务状态: {result.get('status')}")
            print(f"检查时间: {result.get('timestamp')}")

async def example_react_mode():
    """示例 7: ReAct模式（推理和行动）"""
    print("\n" + "=" * 60)
    print("示例 7: ReAct模式（推理-行动-观察循环）")
    print("=" * 60)

    request_data = {
        "user_id": "user_react_001",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "搜索关于机器学习的信息"}
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/chat", json=request_data) as response:
            result = await response.json()
            print(f"请求 ID: {result.get('requestId')}")
            print(f"ReAct模式: {result.get('data', {}).get('react_mode')}")
            print(f"迭代次数: {result.get('data', {}).get('iterations')}")

            # 打印推理轨迹
            trace = result.get('data', {}).get('reasoning_trace', [])
            print(f"\n推理轨迹 ({len(trace)} 步):")
            for i, step in enumerate(trace[:6], 1):  # 只显示前6步
                print(f"\n  步骤 {i}:")
                print(f"    类型: {step.get('type')}")
                print(f"    内容: {step.get('content', '')[:100]}...")

            # 打印最终答案
            answer = result.get('data', {}).get('answer', '')
            print(f"\n最终答案:")
            print(f"  {answer[:200]}...")

async def example_react_with_image():
    """示例 8: ReAct模式分析图像"""
    print("\n" + "=" * 60)
    print("示例 8: ReAct模式分析图像")
    print("=" * 60)

    request_data = {
        "user_id": "user_react_002",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "分析这张图像并描述你看到了什么"},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{SAMPLE_IMAGE}"}
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/chat", json=request_data) as response:
            result = await response.json()
            print(f"请求 ID: {result.get('requestId')}")

            trace = result.get('data', {}).get('reasoning_trace', [])
            print(f"\n推理过程 ({len(trace)} 步):")

            # 按类型分组显示轨迹
            thoughts = [s for s in trace if s.get('type') == 'thought']
            actions = [s for s in trace if s.get('type') == 'action']
            observations = [s for s in trace if s.get('type') == 'observation']

            if thoughts:
                print(f"\n  💭 推理 ({len(thoughts)} 步):")
                for i, thought in enumerate(thoughts, 1):
                    print(f"    {i}. {thought.get('content', '')[:80]}...")

            if actions:
                print(f"\n  🔧 行动 ({len(actions)} 步):")
                for i, action in enumerate(actions, 1):
                    print(f"    {i}. {action.get('content', '')}")

            if observations:
                print(f"\n  👁️ 观察 ({len(observations)} 步):")
                for i, obs in enumerate(observations, 1):
                    print(f"    {i}. {str(obs.get('content', ''))[:80]}...")

            print(f"\n  最终答案:")
            answer = result.get('data', {}).get('answer', '')
            print(f"    {answer[:200]}...")

async def run_all_examples():
    """运行所有示例"""
    print("=" * 60)
    print("Azure OpenAI GPT-4.1 聊天接口使用示例")
    print("=" * 60)
    print("\n注意: 请确保服务器已在 http://localhost:8000 启动")

    examples = [
        ("健康检查", example_health_check),
        ("纯文本聊天", example_text_only),
        ("文本和图像混合", example_text_and_image),
        ("多轮对话", example_conversation),
        ("流式响应", example_streaming),
        ("错误处理", example_error_handling),
        ("ReAct模式", example_react_mode),
        ("ReAct图像分析", example_react_with_image),
    ]

    for name, func in examples:
        try:
            await func()
            await asyncio.sleep(1)  # 避免请求过快
        except Exception as e:
            print(f"\n❌ 示例 '{name}' 执行失败: {str(e)}")

    print("\n" + "=" * 60)
    print("所有示例执行完成")
    print("=" * 60)

if __name__ == "__main__":
    # 运行所有示例
    asyncio.run(run_all_examples())

    # 或者只运行特定示例
    # asyncio.run(example_text_only())
    # asyncio.run(example_text_and_image())
    # asyncio.run(example_streaming())