#!/usr/bin/env python3
"""
测试新的输入输出格式
支持三种输入模式：
1. 仅文本 (input_text)
2. 仅图像 (input_image)
3. 文本+图像 (input_text + input_image)
"""

import aiohttp
import asyncio
import base64
import json

# 测试文本
TEST_TEXT = "你好，请介绍一下你自己"

# 测试图像 (1x1 像素的红色图像)
TEST_IMAGE = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/wA=="

async def test_text_only():
    """测试仅文本输入"""
    print("\n" + "="*60)
    print("测试 1: 仅文本输入")
    print("="*60)

    request_data = {
        "user_id": "user_123",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": TEST_TEXT}
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "http://localhost:8000/api/chat",
                json=request_data
            ) as response:
                print(f"状态码: {response.status}")
                print("\n流式响应:")

                step_count = 0
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line:
                        step_count += 1
                        try:
                            data = json.loads(line)
                            print(f"\n步骤 {step_count}:")
                            print(f"  Code: {data.get('code')}")
                            print(f"  Message: {data.get('message')}")
                            print(f"  RequestID: {data.get('requestId')}")
                            if 'data' in data and 'steps' in data['data']:
                                for step in data['data']['steps']:
                                    print(f"  Step:")
                                    print(f"    - MessageID: {step.get('message_id')}")
                                    print(f"    - Present: {step.get('present_content', '')[:60]}...")
                                    print(f"    - Type: {step.get('tool_type')}")
                                    print(f"    - Status: {step.get('tool_status')}")
                                    if step.get('observation'):
                                        print(f"    - Observation: {step.get('observation', '')[:60]}...")
                                    if step.get('execution_duration'):
                                        print(f"    - Duration: {step.get('execution_duration')}ms")
                        except json.JSONDecodeError:
                            print(f"  原始数据: {line[:100]}...")

                print(f"\n✅ 文本测试完成，共 {step_count} 个步骤")

        except Exception as e:
            print(f"❌ 错误: {e}")

async def test_image_only():
    """测试仅图像输入"""
    print("\n" + "="*60)
    print("测试 2: 仅图像输入")
    print("="*60)

    request_data = {
        "user_id": "user_456",
        "query": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{TEST_IMAGE}"
                    }
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "http://localhost:8000/api/chat",
                json=request_data
            ) as response:
                print(f"状态码: {response.status}")
                print("\n流式响应:")

                step_count = 0
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line:
                        step_count += 1
                        try:
                            data = json.loads(line)
                            print(f"\n步骤 {step_count}:")
                            print(f"  Code: {data.get('code')}")
                            print(f"  Message: {data.get('message')}")
                            if 'data' in data and 'steps' in data['data']:
                                for step in data['data']['steps']:
                                    print(f"  Step:")
                                    print(f"    - Present: {step.get('present_content', '')[:60]}...")
                                    print(f"    - Status: {step.get('tool_status')}")
                        except json.JSONDecodeError:
                            print(f"  原始数据: {line[:100]}...")

                print(f"\n✅ 图像测试完成，共 {step_count} 个步骤")

        except Exception as e:
            print(f"❌ 错误: {e}")

async def test_text_and_image():
    """测试文本+图像输入"""
    print("\n" + "="*60)
    print("测试 3: 文本 + 图像输入")
    print("="*60)

    request_data = {
        "user_id": "user_789",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "这是什么图像？"},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{TEST_IMAGE}"
                    }
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "http://localhost:8000/api/chat",
                json=request_data
            ) as response:
                print(f"状态码: {response.status}")
                print("\n流式响应:")

                step_count = 0
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line:
                        step_count += 1
                        try:
                            data = json.loads(line)
                            print(f"\n步骤 {step_count}:")
                            print(f"  Code: {data.get('code')}")
                            print(f"  Message: {data.get('message')}")
                            if 'data' in data and 'steps' in data['data']:
                                for step in data['data']['steps']:
                                    print(f"  Step:")
                                    print(f"    - Present: {step.get('present_content', '')[:60]}...")
                                    print(f"    - Status: {step.get('tool_status')}")
                        except json.JSONDecodeError:
                            print(f"  原始数据: {line[:100]}...")

                print(f"\n✅ 文本+图像测试完成，共 {step_count} 个步骤")

        except Exception as e:
            print(f"❌ 错误: {e}")

async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试新的输入输出格式")
    print("="*60)

    # 等待服务器启动
    await asyncio.sleep(1)

    # 运行测试
    await test_text_only()
    await asyncio.sleep(1)

    await test_image_only()
    await asyncio.sleep(1)

    await test_text_and_image()

    print("\n" + "="*60)
    print("所有测试完成")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
