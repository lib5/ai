"""
MCP 用户接口测试脚本
测试 users_add_metadata、users_metadata、users_get_location、users_update_metadata
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
MCP_BASE_URL_RAW = os.getenv("TEST_MCP_BASE_URL", "http://192.168.106.108:8001")
# MCP_BASE_URL_RAW = os.getenv("TEST_MCP_BASE_URL", "http://127.0.0.1:8001")
SERVICE_TOKEN = os.getenv("MCP_SERVICE_TOKEN", "test-service-token")
# 将 key 放到 URL 参数中
MCP_BASE_URL = f"{MCP_BASE_URL_RAW}?key={SERVICE_TOKEN}"
TEST_USER_ID = str(uuid4())

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


def extract_response_data(formatted_result):
    """从 FastMCP 返回的格式化结果中提取实际的响应数据"""
    if not isinstance(formatted_result, dict):
        return formatted_result
    
    # 如果直接包含 status，说明已经是解析后的数据
    if "status" in formatted_result:
        return formatted_result
    
    # 尝试从 content 中提取
    if "content" in formatted_result:
        content = formatted_result["content"]
        if isinstance(content, list) and len(content) > 0:
            first_item = content[0]
            if isinstance(first_item, dict) and "text" in first_item:
                text = first_item["text"]
                # 尝试解析 JSON 字符串
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    pass
    
    # 如果无法提取，返回原始格式
    return formatted_result


async def test_users(client):
    """测试用户相关接口"""
    try:
        print("\n" + "=" * 60)
        print("👤 测试用户相关接口")
        print("=" * 60)
        
        # 先列出所有可用工具，检查用户相关工具是否存在
        print("\n📋 检查可用工具...")
        try:
            tools = await client.list_tools()
            tool_names = [tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown') for tool in tools]
            print(f"✅ 可用工具数量: {len(tools) if tools else 0}")
            print(f"   用户相关工具: {[name for name in tool_names if 'user' in name.lower()]}")
            
            # 检查需要的工具是否存在
            required_tools = ["users_add_metadata", "users_metadata", "users_get_location", "users_update_metadata"]
            missing_tools = [tool for tool in required_tools if tool not in tool_names]
            if missing_tools:
                print(f"⚠️  缺少工具: {missing_tools}")
                print("   请确保 MCP 服务器已重启并加载了最新代码")
                return
        except Exception as e:
            print(f"⚠️  列出工具失败: {str(e)}")
            print("   继续测试...")
        
        # 测试创建用户并设置元数据
        print("\n📝 测试创建用户并设置元数据 (users_add_metadata)...")
        test_username = f"test_user_{uuid4().hex[:8]}"
        test_email = f"test_{uuid4().hex[:8]}@example.com"
        result = await client.call_tool("users_add_metadata", {
            "user_id": TEST_USER_ID,
            "username": test_username,
            "email": test_email,
            "phone": "13800138000",
            "city": "北京",
            "company": "测试公司",
            "industry": "互联网",
            "wechat": "test_wechat",
            "longitude": 116.397128,
            "latitude": 39.916527,
            "address": "北京市朝阳区望京街道望京SOHO塔3号楼",
            "country": "中国",
            "birthday": "1990-01-01T00:00:00",
        })
        formatted_result = format_result(result)
        print(f"✅ 创建用户结果: {json.dumps(formatted_result, indent=2, ensure_ascii=False)}")
        
        # 提取实际的响应数据
        response_data = extract_response_data(formatted_result)
        
        # 检查创建是否成功
        if isinstance(response_data, dict):
            status = response_data.get("status")
            if status != 200:
                print(f"⚠️  创建用户失败，状态码: {status}")
                if "data" in response_data and "error" in response_data.get("data", {}):
                    print(f"   错误信息: {response_data['data']['error']}")
                return
        
        # 测试查询用户元数据
        print("\n📖 测试查询用户元数据 (users_metadata)...")
        result = await client.call_tool("users_metadata", {
            "user_id": TEST_USER_ID,
        })
        formatted_result = format_result(result)
        response_data = extract_response_data(formatted_result)
        print(f"✅ 查询用户结果: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        # 测试获取用户位置
        print("\n📍 测试获取用户位置 (users_get_location)...")
        result = await client.call_tool("users_get_location", {
            "user_id": TEST_USER_ID,
        })
        formatted_result = format_result(result)
        response_data = extract_response_data(formatted_result)
        print(f"✅ 获取位置结果: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        # 测试更新用户元数据
        print("\n✏️  测试更新用户元数据 (users_update_metadata)...")
        result = await client.call_tool("users_update_metadata", {
            "user_id": TEST_USER_ID,
            "phone": "13900139000",
            "city": "上海",
            "company": "新测试公司",
        })
        formatted_result = format_result(result)
        response_data = extract_response_data(formatted_result)
        print(f"✅ 更新用户结果: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        # 再次查询验证更新
        print("\n📖 再次查询用户元数据验证更新...")
        result = await client.call_tool("users_metadata", {
            "user_id": TEST_USER_ID,
        })
        formatted_result = format_result(result)
        response_data = extract_response_data(formatted_result)
        print(f"✅ 验证结果: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        print("\n" + "=" * 60)
        print("✅ 用户接口测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_with_client():
    """使用 FastMCP Client 测试"""
    print("=" * 60)
    print("MCP 用户接口测试 - 使用 FastMCP Client")
    print("=" * 60)
    print(f"Base URL: {MCP_BASE_URL}")
    print(f"User ID: {TEST_USER_ID}")
    print(f"Service Token: {SERVICE_TOKEN[:10]}...")
    print("=" * 60)
    
    # 使用新的 API 或旧的 API
    if USE_NEW_API:
        # 使用新的 streamable_http_client API
        print("使用新的 streamable_http_client API")
        async with streamable_http_client(MCP_BASE_URL) as client:
            await test_users(client)
    else:
        # 使用旧的 API
        print("使用 StreamableHttpTransport API")
        transport = StreamableHttpTransport(url=MCP_BASE_URL)
        async with Client(transport) as client:
            await test_users(client)
    
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
