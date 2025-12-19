#!/usr/bin/env python3
"""
测试带metadata的请求格式
这个脚本演示了如何使用新的输入格式，包含完整的metadata信息
"""

import asyncio
import aiohttp
import json
import sys

# 测试用的 base64 图像（1x1 像素的透明 PNG）
TEST_IMAGE_BASE64 = """iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="""

async def test_with_metadata(base_url: str = "http://localhost:8000"):
    """测试带metadata的完整请求"""
    print("\n" + "=" * 60)
    print("测试带metadata的完整请求格式")
    print("=" * 60)

    # 完整的请求数据，包含metadata
    request_data = {
        "user_id": "xxxxx",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "what is in this image?"},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{TEST_IMAGE_BASE64}"
                    }
                ]
            }
        ],
        "metadata": {
            "user": {
                "id": "ac66c8b6-b138-4c67-8688-f165f46d730f",
                "username": "test_user_2e3b6b0f",
                "email": "test_29bd727c@example.com",
                "phone": "13900139000",
                "city": "上海",
                "wechat": "test_wechat",
                "company": "新测试公司",
                "birthday": "1990-01-01T00:00:00",
                "industry": "互联网",
                "longitude": 116.397128,
                "latitude": 39.916527,
                "address": "北京市朝阳区望京街道望京SOHO塔3号楼",
                "country": "中国",
                "location_updated_at": "2025-12-18T09:50:53.615000",
                "created_at": "2025-12-18T09:50:53.442000",
                "updated_at": "2025-12-18T09:50:53.615000"
            }
        }
    }

    print("\n请求数据:")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))

    url = f"{base_url}/api/chat"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data) as response:
                if response.status == 200:
                    print(f"\n✅ 请求成功 (状态码: {response.status})")

                    # 收集所有SSE数据块
                    content = await response.text()

                    # 解析流式JSON格式的响应
                    all_steps = []
                    request_id = "N/A"
                    final_result = None

                    for line in content.split('\n'):
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)

                                # 如果是新的流式格式（包含data.steps）
                                if 'data' in data and 'steps' in data['data']:
                                    final_result = data
                                    all_steps = data['data']['steps']
                                    request_id = data.get('requestId', request_id)
                                # 如果是SSE格式的响应
                                elif 'event' in data:
                                    if data.get('event') == 'start':
                                        request_id = data.get('requestId', 'N/A')
                                    elif data.get('event') == 'step':
                                        step_data = data.get('stepData')
                                        if step_data:
                                            all_steps.append(step_data)
                                        if request_id == "N/A":
                                            request_id = data.get('requestId', 'N/A')
                            except json.JSONDecodeError:
                                continue

                    # 如果没有找到响应，尝试直接解析整个content
                    if final_result is None:
                        try:
                            final_result = json.loads(content)
                        except json.JSONDecodeError:
                            final_result = {
                                "code": 200,
                                "message": "成功",
                                "requestId": request_id,
                                "data": {
                                    "steps": all_steps
                                }
                            }

                    print(f"\n请求 ID: {final_result.get('requestId', request_id)}")
                    print(f"消息: {final_result.get('message', 'N/A')}")
                    print(f"步骤数量: {len(final_result.get('data', {}).get('steps', []))}")

                    # 显示AI的回答
                    data = final_result.get('data', {})
                    if 'answer' in data:
                        print(f"\n=== AI 回答 ===")
                        print(f"{data['answer']}")
                        print(f"=" * 60)

                    # 显示推理过程
                    if 'reasoning_trace' in data and data['reasoning_trace']:
                        print(f"\n=== ReAct 推理过程 ===")
                        for trace in data['reasoning_trace']:
                            print(f"  {trace.get('type').upper()}: {trace.get('content', '')}")
                        print(f"=" * 60)

                    # 打印所有步骤的详细信息
                    print(f"\n=== 详细处理步骤 ===")
                    steps = final_result.get('data', {}).get('steps', [])
                    for i, step in enumerate(steps[:], 1):
                        print(f"\n  步骤 {i}:")
                        # 只打印实际存在的字段
                        for key, value in step.items():
                            print(f"    {key}: {value}")

                    return final_result
                else:
                    error_text = await response.text()
                    print(f"\n❌ 请求失败: {response.status} - {error_text}")
                    return {"error": error_text, "status": response.status}

    except Exception as e:
        print(f"\n❌ 请求异常: {str(e)}")
        return {"error": str(e)}

async def test_text_only_with_metadata(base_url: str = "http://localhost:8000"):
    """测试纯文本输入带metadata"""
    print("\n" + "=" * 60)
    print("测试纯文本输入（带metadata）")
    print("=" * 60)

    request_data = {
        "user_id": "test_user_001",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "搜索关于 Python 编程的信息"}
                ]
            }
        ],
        "metadata": {
            "user": {
                "id": "ac66c8b6-b138-4c67-8688-f165f46d730f",
                "username": "test_user_001",
                "email": "test_001@example.com",
                "phone": "13900139001",
                "city": "北京",
                "wechat": "test_wechat_001",
                "company": "测试公司",
                "birthday": "1990-01-01T00:00:00",
                "industry": "互联网",
                "longitude": 116.397128,
                "latitude": 39.916527,
                "address": "北京市朝阳区望京街道望京SOHO塔3号楼",
                "country": "中国",
                "location_updated_at": "2025-12-18T09:50:53.615000",
                "created_at": "2025-12-18T09:50:53.442000",
                "updated_at": "2025-12-18T09:50:53.615000"
            }
        }
    }

    url = f"{base_url}/api/chat"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=request_data) as response:
                content = await response.text()
                print(f"响应内容:\n{content}")
                return json.loads(content) if content else {}

    except Exception as e:
        print(f"错误: {str(e)}")
        return {"error": str(e)}

async def main():
    """主函数"""
    print("=" * 60)
    print("测试带metadata的API请求")
    print("=" * 60)

    # 检查命令行参数
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"\n测试目标: {base_url}")

    # 测试1: 纯文本输入
    await test_text_only_with_metadata(base_url)

    # 测试2: 文本+图像输入
    await test_with_metadata(base_url)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
