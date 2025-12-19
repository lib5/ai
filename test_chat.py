import asyncio
import aiohttp
import json
import base64
import sys
from typing import Dict, Any, List

# 测试用的 base64 图像（1x1 像素的透明 PNG）
TEST_IMAGE_BASE64 = """iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="""

class ChatAPITester:
    """聊天 API 测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: aiohttp.ClientSession = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_text_only(self) -> Dict[str, Any]:
        """测试纯文本输入 - 使用实际的 MCP 工具"""
        print("\n=== 测试纯文本输入 ===")

        request_data = {
            "user_id": "test_user_001",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "搜索关于 Python 编程的信息"}
                    ]
                }
            ]
        }

        return await self._send_request(request_data)

    async def test_text_and_image(self) -> Dict[str, Any]:
        """测试文本和图像混合输入"""
        print("\n=== 测试文本和图像混合输入 ===")

        request_data = {
            "user_id": "test_user_002",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "这是什么图像？"},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{TEST_IMAGE_BASE64}"}
                    ]
                }
            ]
        }

        return await self._send_request(request_data)

    async def test_multiple_queries(self) -> Dict[str, Any]:
        """测试多个查询"""
        print("\n=== 测试多个查询 ===")

        request_data = {
            "user_id": "test_user_003",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "什么是人工智能？"}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "它有哪些应用？"}
                    ]
                }
            ]
        }

        return await self._send_request(request_data)

    async def _send_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求并接收响应（支持SSE流式响应）"""
        url = f"{self.base_url}/api/chat"

        try:
            async with self.session.post(url, json=request_data) as response:
                if response.status == 200:
                    # 收集所有SSE数据块
                    content = await response.text()

                    # 解析流式JSON格式的响应
                    # 新格式：每行一个完整的JSON响应，包含累积的steps
                    all_steps = []
                    request_id = "N/A"
                    final_result = None

                    for line in content.split('\n'):
                        line = line.strip()
                        if line:
                            try:
                                # 尝试解析为JSON
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

                    print(f"响应状态: {response.status}")
                    print(f"请求 ID: {final_result.get('requestId', request_id)}")
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
                        print(f"    message_id: {step.get('message_id', '')}")
                        print(f"    present_content: {step.get('present_content', '')}")
                        print(f"    tool_type: {step.get('tool_type', '')}")
                        print(f"    parameters: {step.get('parameters', '')}")
                        print(f"    observation: {step.get('observation', '')}")
                        print(f"    tool_status: {step.get('tool_status', '')}")
                        print(f"    execution_duration: {step.get('execution_duration', 0)}ms")

                    return final_result
                else:
                    error_text = await response.text()
                    print(f"请求失败: {response.status} - {error_text}")
                    return {"error": error_text, "status": response.status}

        except Exception as e:
            print(f"请求异常: {str(e)}")
            return {"error": str(e)}

    async def test_streaming_response(self) -> Dict[str, Any]:
        """测试流式响应"""
        print("\n=== 测试流式响应 ===")

        request_data = {
            "user_id": "test_user_004",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "请用流式方式回答：什么是深度学习？"}
                    ]
                }
            ]
        }

        url = f"{self.base_url}/api/chat"

        try:
            async with self.session.post(url, json=request_data) as response:
                if response.status == 200:
                    print("流式响应内容:")
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line:
                            print(f"  {line}")
                    return {"status": "success", "streaming": True}
                else:
                    error_text = await response.text()
                    print(f"请求失败: {response.status} - {error_text}")
                    return {"error": error_text, "status": response.status}

        except Exception as e:
            print(f"请求异常: {str(e)}")
            return {"error": str(e)}

    async def test_mcp_tools(self) -> Dict[str, Any]:
        """测试 MCP 工具调用 - 使用实际的 MCP 工具"""
        print("\n=== 测试 MCP 工具调用 ===")

        request_data = {
            "user_id": "test_user_005",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "搜索关于人工智能的信息"}
                    ]
                }
            ]
        }

        return await self._send_request(request_data)

    async def test_health_check(self) -> Dict[str, Any]:
        """测试健康检查"""
        print("\n=== 测试健康检查 ===")

        url = f"{self.base_url}/health"

        try:
            async with self.session.get(url) as response:
                result = await response.json()
                print(f"健康检查状态: {result}")
                return result

        except Exception as e:
            print(f"健康检查异常: {str(e)}")
            return {"error": str(e)}

async def test_modelscope_mcp():
    """测试 ModelScope MCP 客户端"""
    print("\n=== 测试 ModelScope MCP 客户端 ===")

    try:
        from services.mcp_client import ModelscopeMCPClient

        async with ModelscopeMCPClient("http://localhost:3000") as client:
            # 测试列出工具
            print("获取可用工具列表...")
            tools = await client.list_tools()
            print(f"可用工具数量: {len(tools)}")

            # 测试搜索模型（如果 MCP 服务器可用）
            try:
                models = await client.search_model("computer vision", limit=5)
                print(f"找到 {len(models)} 个相关模型")
            except Exception as e:
                print(f"模型搜索失败（可能 MCP 服务器未启动）: {str(e)}")

    except Exception as e:
        print(f"MCP 客户端测试失败: {str(e)}")

async def main():
    """主测试函数"""
    print("=" * 60)
    print("聊天 API 测试套件")
    print("=" * 60)

    # 检查命令行参数
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"测试目标: {base_url}")

    async with ChatAPITester(base_url) as tester:
        # 测试健康检查
        await tester.test_health_check()

        # 测试文本输入
        await tester.test_text_only()

        # 测试文本和图像混合输入
        await tester.test_text_and_image()

        # 测试多个查询
        await tester.test_multiple_queries()

        # 测试 MCP 工具调用
        await tester.test_mcp_tools()

        # 测试流式响应
        await tester.test_streaming_response()

    # 测试 MCP 客户端
    await test_modelscope_mcp()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())