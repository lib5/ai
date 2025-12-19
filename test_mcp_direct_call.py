#!/usr/bin/env python3
"""
手动调用 MCP 工具测试
"""
import asyncio
import json

try:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport
    USE_NEW_API = False
    print("✅ 使用旧的 Client API")
except ImportError:
    try:
        from fastmcp import streamable_http_client
        USE_NEW_API = True
        print("✅ 使用新的 streamable_http_client API")
    except ImportError:
        print("❌ 错误: 未安装 fastmcp")
        exit(1)


async def test_mcp_weather_tool():
    """测试天气 MCP 工具"""
    mcp_url = "https://mcp.api-inference.modelscope.net/ae89533f5f7741/mcp"

    print(f"\n{'='*60}")
    print(f"手动调用天气 MCP 工具")
    print(f"{'='*60}")

    try:
        if USE_NEW_API:
            from fastmcp import streamable_http_client

            async with streamable_http_client(mcp_url) as client:
                print("\n📋 列出工具...")
                tools = await client.list_tools()
                print(f"✅ 可用工具数量: {len(tools) if tools else 0}")

                if tools:
                    for tool in tools:
                        tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                        print(f"  - {tool_name}")

                # 测试调用 get_weather
                print(f"\n🧪 测试调用 get_weather 工具...")
                result = await client.call_tool("get_weather", {
                    "city": "北京",
                    "units": "metric",
                    "lang": "zh_cn"
                })
                print(f"✅ 调用成功!")
                print(f"结果类型: {type(result)}")
                print(f"结果内容:")
                print(json.dumps(result, indent=2, ensure_ascii=False))

                # 测试调用 get_weather_forecast
                print(f"\n🧪 测试调用 get_weather_forecast 工具...")
                result = await client.call_tool("get_weather_forecast", {
                    "city": "北京",
                    "days": 3,
                    "units": "metric",
                    "lang": "zh_cn"
                })
                print(f"✅ 调用成功!")
                print(f"结果类型: {type(result)}")
                print(f"结果内容:")
                print(json.dumps(result, indent=2, ensure_ascii=False))

        else:
            transport = StreamableHttpTransport(url=mcp_url)
            async with Client(transport) as client:
                print("\n📋 列出工具...")
                tools = await client.list_tools()
                print(f"✅ 可用工具数量: {len(tools) if tools else 0}")

                if tools:
                    for tool in tools:
                        tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                        print(f"  - {tool_name}")

                # 测试调用 get_weather
                print(f"\n🧪 测试调用 get_weather 工具...")
                result = await client.call_tool("get_weather", {
                    "city": "北京",
                    "units": "metric",
                    "lang": "zh_cn"
                })
                print(f"✅ 调用成功!")
                print(f"结果类型: {type(result)}")
                print(f"结果内容:")
                print(json.dumps(result, indent=2, ensure_ascii=False))

                # 测试调用 get_weather_forecast
                print(f"\n🧪 测试调用 get_weather_forecast 工具...")
                result = await client.call_tool("get_weather_forecast", {
                    "city": "北京",
                    "days": 3,
                    "units": "metric",
                    "lang": "zh_cn"
                })
                print(f"✅ 调用成功!")
                print(f"结果类型: {type(result)}")
                print(f"结果内容:")
                print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*60}")


async def test_react_agent_mcp_call():
    """测试 ReAct Agent 手动调用 MCP 工具"""
    print(f"\n{'='*60}")
    print(f"测试 ReAct Agent 手动调用 MCP 工具")
    print(f"{'='*60}")

    from services.true_react_agent import TrueReActAgent
    from services.mcp_client import FastMCPClient

    # 创建 ReAct Agent
    agent = TrueReActAgent()

    try:
        # 初始化 Agent
        await agent.initialize()

        print(f"\n✅ ReAct Agent 初始化成功")
        print(f"   MCP 客户端: {agent.mcp_client}")

        # 手动调用 MCP 工具
        print(f"\n🧪 手动调用 MCP 工具...")
        mcp_result = await agent._tool_mcp_call_tool("get_weather", {
            "city": "北京",
            "units": "metric",
            "lang": "zh_cn"
        })

        print(f"✅ MCP 工具调用成功!")
        print(f"结果:")
        print(json.dumps(mcp_result, indent=2, ensure_ascii=False))

        # 检查结果
        if mcp_result.get('success'):
            print(f"\n✅ MCP 工具调用成功!")
            print(f"   工具名称: {mcp_result.get('tool_name')}")
            if 'result' in mcp_result:
                print(f"   结果数据: {json.dumps(mcp_result['result'], indent=2, ensure_ascii=False)}")
        else:
            print(f"\n⚠️  MCP 工具调用失败:")
            print(f"   错误: {mcp_result.get('error')}")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*60}")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("手动 MCP 工具调用测试")
    print("=" * 60)

    # 测试 1: 直接调用 MCP 工具
    await test_mcp_weather_tool()

    # 测试 2: 通过 ReAct Agent 调用 MCP 工具
    await test_react_agent_mcp_call()

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
