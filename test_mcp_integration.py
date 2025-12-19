#!/usr/bin/env python3
"""
测试 MCP 集成脚本
测试 ReAct Agent 与 MCP 服务器的集成
"""
import asyncio
import json
from services.true_react_agent import TrueReActAgent

# 检查是否使用新 API
try:
    from fastmcp import streamable_http_client
    USE_NEW_API = True
except ImportError:
    try:
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport
        USE_NEW_API = False
    except ImportError:
        print("❌ 错误: 未安装 fastmcp")
        print("   请运行: pip install fastmcp>=2.8.0,<2.12.0")
        exit(1)


async def test_mcp_weather():
    """测试天气 MCP 服务"""
    print("=" * 60)
    print("测试 MCP 集成 - 天气查询")
    print("=" * 60)

    # 创建 ReAct Agent
    agent = TrueReActAgent()

    try:
        # 初始化 Agent
        await agent.initialize()

        # 测试查询：获取天气信息
        query = "请帮我查询北京的天气情况"

        print(f"\n查询: {query}")
        print("-" * 60)

        # 运行 ReAct Agent
        result = await agent.run(query)

        # 打印结果
        print("\n" + "=" * 60)
        print("执行结果:")
        print("=" * 60)
        print(f"查询: {result.get('query', '')}")
        print(f"答案: {result.get('answer', '')}")
        print(f"迭代次数: {result.get('iterations', 0)}")
        print(f"成功: {result.get('success', False)}")

        # 打印详细步骤
        print("\n详细步骤:")
        print("-" * 60)
        for step in result.get('steps', []):
            print(f"\n步骤 {step.get('iteration', 0)} - {step.get('type', '')}")
            if step.get('tool_name'):
                print(f"  工具: {step.get('tool_name', '')}")
            if step.get('tool_args'):
                print(f"  参数: {json.dumps(step.get('tool_args', {}), ensure_ascii=False)}")
            if step.get('tool_result'):
                print(f"  结果: {json.dumps(step.get('tool_result', {}), ensure_ascii=False)}")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


async def test_mcp_direct():
    """直接测试 MCP 工具调用"""
    print("\n" + "=" * 60)
    print("直接测试 MCP 工具调用")
    print("=" * 60)

    from services.mcp_client import FastMCPClient

    # MCP 服务器 URL（用户提供的天气 MCP 服务）
    mcp_url = "https://mcp.api-inference.modelscope.net/ae89533f5f7741/mcp"

    print(f"\nMCP 服务器: {mcp_url}")

    try:
        # 尝试连接并列出工具
        if USE_NEW_API:
            from fastmcp import streamable_http_client

            async with streamable_http_client(mcp_url) as mcp_client:
                print("\n📋 列出可用工具...")
                tools = await mcp_client.list_tools()
                print(f"✅ 可用工具数量: {len(tools) if tools else 0}")

                if tools:
                    for tool in tools:
                        tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                        tool_desc = tool.get('description', '') if isinstance(tool, dict) else getattr(tool, 'description', '')
                        print(f"  - {tool_name}: {tool_desc}")

                    # 尝试调用第一个工具（如果有）
                    if len(tools) > 0:
                        first_tool = tools[0]
                        tool_name = first_tool.get('name', 'unknown') if isinstance(first_tool, dict) else getattr(first_tool, 'name', 'unknown')
                        print(f"\n🧪 尝试调用工具: {tool_name}")

                        # 准备参数（根据工具类型）
                        args = {}
                        if tool_name == "get_weather" or "weather" in tool_name.lower():
                            args = {"location": "北京"}
                        elif "contacts" in tool_name.lower():
                            args = {"user_id": "test_user"}
                        else:
                            # 通用参数
                            args = {"query": "测试"}

                        try:
                            client_instance = FastMCPClient(mcp_url)
                            result = await mcp_client.call_tool(tool_name, args)
                            formatted_result = client_instance._format_result(result)
                            extracted_data = client_instance.extract_response_data(formatted_result)
                            print(f"✅ 调用成功: {json.dumps(extracted_data, indent=2, ensure_ascii=False)}")
                        except Exception as e:
                            print(f"⚠️  调用工具失败: {str(e)}")
        else:
            # 旧版 API
            async with FastMCPClient(mcp_url) as client:
                tools = await client.list_tools()
                print(f"可用工具: {tools}")

    except Exception as e:
        print(f"\n❌ 直接测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


async def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("MCP 集成测试")
    print("=" * 60)

    # 测试 1: 直接测试 MCP 工具
    await test_mcp_direct()

    # 测试 2: 测试 ReAct Agent 与 MCP 集成
    await test_mcp_weather()

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
