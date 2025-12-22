#!/usr/bin/env python3
"""
诊断 MCP 客户端问题的测试脚本
"""
import asyncio
import sys
import traceback
from config import settings

# 尝试导入
try:
    from services.multi_mcp_client import MultiMCPClient
    from services.mcp_client import FastMCPClient
    print("✅ 成功导入 MCP 相关模块")
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    sys.exit(1)

async def test_servers():
    """测试各个 MCP 服务器的连接性"""
    print("\n" + "=" * 70)
    print("MCP 服务器连接性诊断")
    print("=" * 70)

    # 测试配置
    print("\n📋 当前配置:")
    print(f"  - MCP_SERVER_URL: {settings.mcp_server_url}")
    print(f"  - TEST_MCP_BASE_URL: {settings.test_mcp_base_url}")
    print(f"  - MCP_SERVICE_TOKEN: {settings.mcp_service_token}")

    # 测试 bing-cn-search 服务器
    print("\n" + "-" * 70)
    print("测试 1: bing-cn-search 服务器")
    print("-" * 70)
    try:
        url = settings.mcp_server_url
        print(f"连接 URL: {url}")
        async with FastMCPClient(url) as client:
            print("✅ 连接成功")
            tools = await client.list_tools()
            print(f"✅ 成功获取 {len(tools)} 个工具")
            for tool in tools[:3]:  # 只显示前3个
                tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                print(f"  - {tool_name}")
            if len(tools) > 3:
                print(f"  ... 还有 {len(tools) - 3} 个工具")
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        traceback.print_exc()

    # 测试 test_mcp 服务器
    print("\n" + "-" * 70)
    print("测试 2: test_mcp 服务器")
    print("-" * 70)
    try:
        url = settings.test_mcp_base_url
        print(f"连接 URL: {url}")
        print(f"Service Token: {settings.mcp_service_token}")
        async with FastMCPClient(url, settings.mcp_service_token) as client:
            print("✅ 连接成功")
            tools = await client.list_tools()
            print(f"✅ 成功获取 {len(tools)} 个工具")
            for tool in tools:
                tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                print(f"  - {tool_name}")
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        traceback.print_exc()

    # 测试 MultiMCPClient
    print("\n" + "-" * 70)
    print("测试 3: MultiMCPClient")
    print("-" * 70)
    try:
        multi_mcp = MultiMCPClient()
        print(f"✅ 成功初始化 MultiMCPClient")
        print(f"已配置 {len(multi_mcp.servers)} 个服务器")

        all_tools = await multi_mcp.list_all_tools()
        print(f"✅ 成功获取所有工具列表")
        print(f"总共发现 {len(multi_mcp.get_available_tools())} 个工具")

        if multi_mcp.get_available_tools():
            print("\n可用工具:")
            for tool_name in multi_mcp.get_available_tools():
                server = multi_mcp.get_tool_server(tool_name)
                print(f"  - {tool_name} (来自 {server})")
        else:
            print("\n⚠️  未发现任何工具")
    except Exception as e:
        print(f"❌ MultiMCPClient 测试失败: {str(e)}")
        traceback.print_exc()

async def test_tool_calls():
    """测试工具调用"""
    print("\n" + "=" * 70)
    print("工具调用测试")
    print("=" * 70)

    try:
        multi_mcp = MultiMCPClient()
        await multi_mcp.list_all_tools()

        # 测试各种工具
        test_cases = [
            {
                "name": "contacts_search",
                "args": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",  # 使用正确的 UUID 格式
                    "name": "测试"
                }
            },
            {
                "name": "schedules_search",
                "args": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "测试"
                }
            }
        ]

        for test_case in test_cases:
            tool_name = test_case["name"]
            args = test_case["args"]

            print(f"\n🧪 测试工具: {tool_name}")
            print(f"   参数: {args}")

            if tool_name in multi_mcp.get_available_tools():
                result = await multi_mcp.call_tool(tool_name, args)
                if result.get("success"):
                    print(f"   ✅ 调用成功")
                    print(f"   结果: {str(result.get('result'))[:200]}...")
                else:
                    print(f"   ❌ 调用失败: {result.get('error')}")
            else:
                print(f"   ⚠️  工具不可用")

    except Exception as e:
        print(f"❌ 工具调用测试失败: {str(e)}")
        traceback.print_exc()

async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("MCP 客户端诊断工具")
    print("=" * 70)

    await test_servers()
    await test_tool_calls()

    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
