#!/usr/bin/env python3
"""
MCP 集成使用示例
展示如何在 ReAct Agent 中使用 MCP 工具
"""
import asyncio
import json
from services.true_react_agent import TrueReActAgent


async def example_weather_query():
    """示例 1: 查询天气"""
    print("\n" + "=" * 60)
    print("示例 1: 查询天气")
    print("=" * 60)

    agent = TrueReActAgent()
    await agent.initialize()

    # 查询天气
    query = "请帮我查询北京今天的天气"
    result = await agent.run(query)

    print(f"\n查询: {query}")
    print(f"答案: {result.get('answer', '')}")
    print(f"迭代次数: {result.get('iterations', 0)}")


async def example_general_mcp_tool():
    """示例 2: 使用通用 MCP 工具"""
    print("\n" + "=" * 60)
    print("示例 2: 使用通用 MCP 工具")
    print("=" * 60)

    agent = TrueReActAgent()
    await agent.initialize()

    # 通用查询（模型会自动选择是否使用 MCP 工具）
    query = "你能帮我做一些事情吗？"
    result = await agent.run(query)

    print(f"\n查询: {query}")
    print(f"答案: {result.get('answer', '')}")
    print(f"迭代次数: {result.get('iterations', 0)}")


async def example_list_mcp_tools():
    """示例 3: 列出 MCP 服务器上的所有工具"""
    print("\n" + "=" * 60)
    print("示例 3: 列出 MCP 服务器上的所有工具")
    print("=" * 60)

    from services.mcp_client import FastMCPClient

    mcp_url = "https://mcp.api-inference.modelscope.net/ae89533f5f7741/mcp"

    try:
        async with FastMCPClient(mcp_url) as client:
            if client.USE_NEW_API:
                from fastmcp import streamable_http_client

                async with streamable_http_client(mcp_url) as mcp_client:
                    tools = await mcp_client.list_tools()

                    print(f"\nMCP 服务器: {mcp_url}")
                    print(f"可用工具数量: {len(tools) if tools else 0}")

                    if tools:
                        print("\n工具列表:")
                        for tool in tools:
                            tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                            tool_desc = tool.get('description', '') if isinstance(tool, dict) else getattr(tool, 'description', '')

                            # 格式化工具信息
                            tool_info = FastMCPClient.format_tools_for_llm(tool)
                            print(f"\n{tool_info}")
    except Exception as e:
        print(f"❌ 列出工具失败: {str(e)}")


async def example_call_mcp_directly():
    """示例 4: 直接调用 MCP 工具"""
    print("\n" + "=" * 60)
    print("示例 4: 直接调用 MCP 工具")
    print("=" * 60)

    from services.mcp_client import FastMCPClient

    mcp_url = "https://mcp.api-inference.modelscope.net/ae89533f5f7741/mcp"

    try:
        async with FastMCPClient(mcp_url) as client:
            if client.USE_NEW_API:
                from fastmcp import streamable_http_client

                async with streamable_http_client(mcp_url) as mcp_client:
                    # 尝试调用天气工具（如果存在）
                    # 注意：实际工具名称需要根据 MCP 服务器返回的工具列表确定
                    tool_name = "get_weather"  # 示例工具名
                    args = {"location": "北京"}

                    print(f"\n调用工具: {tool_name}")
                    print(f"参数: {json.dumps(args, ensure_ascii=False)}")

                    try:
                        result = await mcp_client.call_tool(tool_name, args)
                        formatted_result = client._format_result(result)
                        extracted_data = client.extract_response_data(formatted_result)

                        print(f"\n结果:")
                        print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
                    except Exception as e:
                        print(f"⚠️  工具调用失败: {str(e)}")
                        print("   这可能是因为工具名称不正确或需要不同的参数")
    except Exception as e:
        print(f"❌ 直接调用失败: {str(e)}")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("MCP 集成使用示例")
    print("=" * 60)

    # 示例 1: 列出 MCP 工具
    await example_list_mcp_tools()

    # 示例 2: 直接调用 MCP 工具
    await example_call_mcp_directly()

    # 示例 3: 使用 ReAct Agent 查询天气
    await example_weather_query()

    # 示例 4: 通用 MCP 工具使用
    await example_general_mcp_tool()

    print("\n" + "=" * 60)
    print("所有示例运行完成")
    print("=" * 60)
    print("\n使用说明:")
    print("1. ReAct Agent 会自动根据查询内容选择合适的工具")
    print("2. MCP 工具通过 'mcp_call_tool' 工具在 ReAct 循环中使用")
    print("3. 可以直接使用 FastMCPClient 调用 MCP 服务器上的任何工具")
    print("4. 要列出 MCP 服务器上的工具，使用 list_tools() 方法")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
