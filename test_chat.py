import asyncio
import aiohttp
import json
import base64
import sys
from typing import Dict, Any, List

# 测试用的 base64 图像（1x1 像素的透明 PNG）
TEST_IMAGE_BASE64 = """iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="""

# 测试图片URL
TEST_IMAGE_URL = "https://minimax-algeng-chat-tts.oss-cn-wulanchabu.aliyuncs.com/ccv2%2F2025-12-22%2FMiniMax-M2%2F2000840603667013689%2F679e72f571cc53aad5399218b4676b8a7f692d10816aec1dae64b976b10ac833..png?Expires=1766478487&OSSAccessKeyId=LTAI5tGLnRTkBjLuYPjNcKQ8&Signature=401d5nc%2B4nhc88qxdRJXOZaFxkQ%3D"

# 坐标转换：原始图片 1320x2868，显示为 921x2000，需要乘以 1.43 映射到原始图片
COORDINATE_SCALE_FACTOR = 1.43

async def download_image_as_base64(url: str) -> str:
    """下载图片并转换为base64格式"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                return base64.b64encode(image_data).decode('utf-8')
            else:
                raise Exception(f"下载图片失败: {response.status}")

def scale_coordinates(x: float, y: float, scale_factor: float = COORDINATE_SCALE_FACTOR) -> tuple:
    """
    将显示坐标转换为原始图片坐标

    Args:
        x: 显示的x坐标
        y: 显示的y坐标
        scale_factor: 缩放因子，默认1.43

    Returns:
        tuple: (原始x坐标, 原始y坐标)
    """
    return (x * scale_factor, y * scale_factor)

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
            "user_id": "ac66c8b6-b138-4c67-8688-f165f46d730f",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "老李的电话多少"}
                    ]
                }
            ],
            "metadata": {
                "user":{
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

        return await self._send_request(request_data)

    async def test_text_and_image(self) -> Dict[str, Any]:
        """测试文本和图像混合输入"""
        print("\n=== 测试文本和图像混合输入 ===")

        # 下载实际图片并转换为base64
        print("正在下载测试图片...")
        try:
            image_base64 = await download_image_as_base64(TEST_IMAGE_URL)
            print(f"图片下载成功，base64长度: {len(image_base64)}")
        except Exception as e:
            print(f"图片下载失败，使用测试图片: {str(e)}")
            image_base64 = TEST_IMAGE_BASE64

        request_data = {
            "user_id": "test_user_002",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "提取图像文字并调用工具执行"},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_base64}"}
                    ]
                }
            ],
            "metadata": {
                "user":{
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

        return await self._send_request(request_data)

    async def test_image_with_coordinates(self) -> Dict[str, Any]:
        """测试图片和坐标功能"""
        print("\n=== 测试图片和坐标功能 ===")

        # 下载实际图片并转换为base64
        print("正在下载测试图片...")
        try:
            image_base64 = await download_image_as_base64(TEST_IMAGE_URL)
            print(f"图片下载成功，base64长度: {len(image_base64)}")
        except Exception as e:
            print(f"图片下载失败，使用测试图片: {str(e)}")
            image_base64 = TEST_IMAGE_BASE64

        # 测试坐标转换
        print("\n--- 坐标转换测试 ---")
        test_coords = [
            (100, 200),
            (300, 400),
            (500, 600),
            (750, 1000),
            (921, 2000)  # 最大显示尺寸
        ]

        for display_x, display_y in test_coords:
            orig_x, orig_y = scale_coordinates(display_x, display_y)
            print(f"显示坐标 ({display_x}, {display_y}) -> 原始坐标 ({orig_x:.1f}, {orig_y:.1f})")

        # 创建包含坐标信息的查询
        query_text = f"""请分析这张图片。图片显示尺寸为921x2000，原始尺寸为1320x2868。
如果需要参考特定位置，请使用以下坐标转换：
- 坐标缩放因子: {COORDINATE_SCALE_FACTOR}
- 显示坐标转换为原始坐标: 原始x = 显示x × {COORDINATE_SCALE_FACTOR}, 原始y = 显示y × {COORDINATE_SCALE_FACTOR}"""

        request_data = {
            "user_id": "test_user_006",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": query_text},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_base64}"}
                    ]
                }
            ],
            "metadata": {
                "user":{
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
      },
                "image_info": {
                    "display_width": 921,
                    "display_height": 2000,
                    "original_width": 1320,
                    "original_height": 2868,
                    "scale_factor": COORDINATE_SCALE_FACTOR
                }
            }
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
            ],
            "metadata": {
                "user":{
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
                        # 只打印实际存在的字段
                        for key, value in step.items():
                            print(f"    {key}: {value}")

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
                        {"type": "input_text", "text": "下周四要开会"}
                    ]
                }
            ],
            "metadata": {
                "user":{
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
            ],
            "metadata": {
               "user":{
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

        return await self._send_request(request_data)

    async def test_with_metadata(self, base64_image: str = None, use_real_image: bool = True) -> Dict[str, Any]:
        """测试带metadata的完整请求格式"""
        print("\n=== 测试带metadata的完整请求格式 ===")

        # 如果使用实际图片且没有提供base64_image，则下载
        if use_real_image and not base64_image:
            try:
                print("正在下载测试图片...")
                base64_image = await download_image_as_base64(TEST_IMAGE_URL)
                print(f"图片下载成功，base64长度: {len(base64_image)}")
            except Exception as e:
                print(f"图片下载失败，使用测试图片: {str(e)}")
                base64_image = TEST_IMAGE_BASE64

        request_data = {
            "user_id": "xxxxx",
            "query": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "what is in this image?"}
                    ]
                }
            ],
            "metadata": {
               "user":{
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

        # 如果提供了base64_image，则添加图像
        if base64_image:
            request_data["query"][0]["content"].append({
                "type": "input_image",
                "image_url": f"data:image/png;base64,{base64_image}"
            })

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
        #await tester.test_health_check()

        # 测试文本输入
        #await tester.test_text_only()

        # 测试文本和图像混合输入（使用实际图片）
        await tester.test_text_and_image()

        # 测试图片和坐标功能
        #await tester.test_image_with_coordinates()

        # 测试多个查询
        #await tester.test_multiple_queries()

        # 测试 MCP 工具调用
       # await tester.test_mcp_tools()

        # 测试流式响应
        #await tester.test_streaming_response()

    # 测试 MCP 客户端
   # await test_modelscope_mcp()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())