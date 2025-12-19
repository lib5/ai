"""
MCP 接口测试脚本 - 使用 FastMCP Client（推荐方式）
需要安装: pip install fastmcp>=2.8.0,<2.12.0
"""
import asyncio
import json
import os
from uuid import uuid4

try:
    # 尝试使用新的 API
    try:
        from fastmcp import streamable_http_client
        USE_NEW_API = True
    except ImportError:
        USE_NEW_API = False
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport
except ImportError:
    print("❌ 错误: 未安装 fastmcp")
    print("   请运行: pip install fastmcp>=2.8.0,<2.12.0")
    exit(1)

# 测试配置
# FastAPI 服务器地址
API_BASE_URL = os.getenv("TEST_BASE_URL", "http://192.168.106.108:8000")
# MCP 服务器地址（独立端口）
# MCP_BASE_URL_RAW = os.getenv("TEST_MCP_BASE_URL", "http://192.168.106.108:8001")
MCP_BASE_URL_RAW = os.getenv("TEST_MCP_BASE_URL", "http://192.168.106.108:8001")
SERVICE_TOKEN = os.getenv("MCP_SERVICE_TOKEN", "test-service-token")
# 将 key 放到 URL 参数中
MCP_BASE_URL = f"{MCP_BASE_URL_RAW}?key={SERVICE_TOKEN}"
TEST_USER_ID = str(uuid4())

print(f"API_BASE_URL: {API_BASE_URL}")
print(f"MCP_BASE_URL: {MCP_BASE_URL}")
print(f"TEST_USER_ID: {TEST_USER_ID}")

def format_result(result):
    """格式化结果，将 CallToolResult、TextContent 等对象转换为可序列化的格式"""
    # 处理 None
    if result is None:
        return None
    
    # 处理基本类型
    if isinstance(result, (str, int, float, bool)):
        return result
    
    # 处理列表
    if isinstance(result, list):
        return [format_result(item) for item in result]
    
    # 处理字典
    if isinstance(result, dict):
        return {key: format_result(value) for key, value in result.items()}
    
    # 处理 CallToolResult 对象
    if hasattr(result, 'content'):
        formatted_content = format_result(result.content)
        return {
            "content": formatted_content,
            "isError": getattr(result, 'isError', False),
        }
    
    # 处理 TextContent 对象
    if hasattr(result, 'text'):
        return {
            "type": "text",
            "text": getattr(result, 'text', str(result)),
        }
    
    # 处理其他有 __dict__ 的对象
    if hasattr(result, '__dict__'):
        return {key: format_result(value) for key, value in result.__dict__.items()}
    
    # 处理其他对象，尝试获取常见属性
    if hasattr(result, '__class__'):
        # 尝试获取对象的常见属性
        obj_dict = {}
        for attr in ['text', 'content', 'data', 'value', 'message', 'error']:
            if hasattr(result, attr):
                obj_dict[attr] = format_result(getattr(result, attr))
        if obj_dict:
            return obj_dict
    
    # 最后尝试转换为字符串
    return str(result)

def format_tools_for_llm(tool) -> str:
    args_desc = []
    
    # FastMCP 工具对象可能使用 inputSchema 或 input_schema
    schema = None
    for attr_name in ['inputSchema', 'input_schema', 'schema', 'parameters']:
        schema = getattr(tool, attr_name, None)
        if schema is not None:
            break
    
    # 如果 schema 是对象而非字典，尝试转换
    if schema is not None and hasattr(schema, '__dict__'):
        schema = vars(schema) if not isinstance(schema, dict) else schema
    
    # 如果 schema 有 model_dump 方法（Pydantic 模型）
    if schema is not None and hasattr(schema, 'model_dump'):
        schema = schema.model_dump()
    
    if isinstance(schema, dict) and "properties" in schema:
        properties = schema["properties"]
        required = schema.get("required", [])
        for param_name, param_info in properties.items():
            if isinstance(param_info, dict):
                desc = param_info.get('description', 'No description')
            else:
                desc = getattr(param_info, 'description', 'No description')
            arg_desc = f"- {param_name}: {desc}"
            if param_name in required:
                arg_desc += " (required)"
            args_desc.append(arg_desc)
    
    tool_name = getattr(tool, 'name', 'unknown')
    tool_desc = getattr(tool, 'description', '')
    return f"Tool: {tool_name}\nDescription: {tool_desc}\nArguments:\n{chr(10).join(args_desc)}"

async def run_tests(client):
    """运行测试用例"""
    try:
        # 列出所有可用工具
        print("\n📋 列出所有可用工具...")
        try:
            tools = await client.list_tools()
            print(f"✅ 可用工具数量: {len(tools) if tools else 0}")
            if tools:
                # 调试：打印第一个工具的属性结构
                first_tool = tools[0]
                print(f"\n🔍 调试 - 工具对象类型: {type(first_tool)}")
                print(f"🔍 调试 - 工具对象属性: {dir(first_tool)}")
                if hasattr(first_tool, 'inputSchema'):
                    print(f"🔍 调试 - inputSchema: {first_tool.inputSchema}")
                if hasattr(first_tool, 'input_schema'):
                    print(f"🔍 调试 - input_schema: {first_tool.input_schema}")
                
                for tool in tools:
                    tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                    print(f"   - {tool_name}")
                tools_description = "\n".join([format_tools_for_llm(tool) for tool in tools])
                print(f"工具描述:\n{tools_description}")
        except Exception as e:
            print(f"⚠️  列出工具失败: {str(e)}")
            print("   继续测试工具调用...")
        
        # 测试创建联系人
        print("\n📝 测试创建联系人...")
        result = await client.call_tool("contacts_create", {
            "user_id": TEST_USER_ID,
            "name": "测试联系人",
            "company": "测试公司",
            "phone": "13800138000",
            "email": "test@example.com",
            "relationship_type": "client",
        })
        formatted_result = format_result(result)
        print(f"✅ 创建结果: {json.dumps(formatted_result, indent=2, ensure_ascii=False)}")
        
        # 提取联系人ID（如果返回的是标准格式）
        contact_id = None
        result_dict = formatted_result if isinstance(formatted_result, dict) else {}
        if "data" in result_dict and isinstance(result_dict["data"], dict) and "id" in result_dict["data"]:
            contact_id = result_dict["data"]["id"]
        elif "id" in result_dict:
            contact_id = result_dict["id"]
        elif hasattr(result, 'content') and isinstance(result.content, dict):
            if "data" in result.content and "id" in result.content.get("data", {}):
                contact_id = result.content["data"]["id"]
            elif "id" in result.content:
                contact_id = result.content["id"]
        
        # 测试列表查询
        print("\n📋 测试列表查询联系人...")
        result = await client.call_tool("contacts_list", {
            "user_id": TEST_USER_ID,
            "page": 1,
            "page_size": 20,
        })
        formatted_result = format_result(result)
        print(f"✅ 查询结果: {json.dumps(formatted_result, indent=2, ensure_ascii=False)}")
        
        # 如果创建成功，测试读取和删除
        if contact_id:
            print(f"\n📖 测试读取联系人: {contact_id}...")
            result = await client.call_tool("contacts_read", {
                "user_id": TEST_USER_ID,
                "id": contact_id,
            })
            formatted_result = format_result(result)
            print(f"✅ 读取结果: {json.dumps(formatted_result, indent=2, ensure_ascii=False)}")
            
            print(f"\n🗑️  测试删除联系人: {contact_id}...")
            result = await client.call_tool("contacts_delete", {
                "user_id": TEST_USER_ID,
                "id": contact_id,
            })
            formatted_result = format_result(result)
            print(f"✅ 删除结果: {json.dumps(formatted_result, indent=2, ensure_ascii=False)}")
        
        # 测试其他资源
        print("\n📄 测试创建文件记录...")
        result = await client.call_tool("files_create", {
            "user_id": TEST_USER_ID,
            "file_name": "test_file.pdf",
            "file_url": "https://example.com/files/test.pdf",
            "file_type": "application/pdf",
            "file_size": 1024,
        })
        formatted_result = format_result(result)
        print(f"✅ 创建结果: {json.dumps(formatted_result, indent=2, ensure_ascii=False)}")
        
        print("\n📅 测试创建日程...")
        result = await client.call_tool("schedules_create", {
            "user_id": TEST_USER_ID,
            "title": "测试日程",
            "start_time": "2024-01-15T10:00:00",
            "end_time": "2024-01-15T12:00:00",
            "category": "meeting",
        })
        formatted_result = format_result(result)
        print(f"✅ 创建结果: {json.dumps(formatted_result, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_with_client():
    """使用 FastMCP Client 测试"""
    print("=" * 60)
    print("MCP 接口测试 - 使用 FastMCP Client")
    print("=" * 60)
    print(f"Base URL: {MCP_BASE_URL}")
    print(f"User ID: {TEST_USER_ID}")
    print(f"Service Token: {SERVICE_TOKEN[:10]}...")
    print("=" * 60)
    
    # 使用新的 API 或旧的 API
    # 注意：service_token 已经包含在 MCP_BASE_URL 中
    if USE_NEW_API:
        # 使用新的 streamable_http_client API
        print("使用新的 streamable_http_client API")
        async with streamable_http_client(MCP_BASE_URL) as client:
            await run_tests(client)
    else:
        # 使用旧的 API
        print("使用 StreamableHttpTransport API")
        transport = StreamableHttpTransport(url=MCP_BASE_URL)
        async with Client(transport) as client:
            await run_tests(client)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


async def check_mcp_server():
    """检查 MCP 服务器是否运行"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 尝试连接 MCP 服务器（带认证）
            response = await client.get(f"{MCP_BASE_URL}")
            # MCP 服务器可能返回各种状态码，只要不是连接错误就认为服务器在运行
            return True
    except Exception as e:
        print(f"   连接错误: {str(e)}")
        return False


async def main():
    """主测试流程"""
    print("检查 MCP 服务器状态...")
    if not await check_mcp_server():
        print(f"❌ MCP 服务器未运行，请先启动服务: {MCP_BASE_URL_RAW}")
        print("   启动命令: python run_mcp.py")
        return
    
    print(f"✅ MCP 服务器运行正常: {MCP_BASE_URL_RAW}\n")
    
    await test_with_client()


if __name__ == "__main__":
    asyncio.run(main())
