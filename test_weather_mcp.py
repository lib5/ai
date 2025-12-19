#!/usr/bin/env python3
"""
直接测试天气 MCP 服务器
"""
import asyncio
import json

# 检查是否使用新 API
try:
    from fastmcp import streamable_http_client
    USE_NEW_API = True
    print("✅ 使用新的 streamable_http_client API")
except ImportError:
    try:
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport
        USE_NEW_API = False
        print("✅ 使用旧的 Client API")
    except ImportError:
        print("❌ 错误: 未安装 fastmcp")
        print("   请运行: pip install fastmcp>=2.8.0,<2.12.0")
        exit(1)


async def test_mcp_server():
    """测试 MCP 服务器"""
    mcp_url = "https://mcp.api-inference.modelscope.net/ae89533f5f7741/mcp"

    print(f"\n{'='*60}")
    print(f"测试 MCP 服务器: {mcp_url}")
    print(f"{'='*60}")

    try:
        if USE_NEW_API:
            print("\n📋 列出可用工具...")
            async with streamable_http_client(mcp_url) as client:
                tools = await client.list_tools()
                print(f"✅ 可用工具数量: {len(tools) if tools else 0}")

                if tools:
                    print("\n工具列表:")
                    for i, tool in enumerate(tools, 1):
                        tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                        tool_desc = tool.get('description', '') if isinstance(tool, dict) else getattr(tool, 'description', '')
                        print(f"  {i}. {tool_name}: {tool_desc}")

                    # 尝试调用天气工具
                    print(f"\n🧪 尝试调用天气工具...")
                    weather_tools = [t for t in tools if 'weather' in (t.get('name', '') if isinstance(t, dict) else getattr(t, 'name', '')).lower()]

                    if weather_tools:
                        tool = weather_tools[0]
                        tool_name = tool.get('name', 'unknown') if isinstance(tool, dict) else getattr(tool, 'name', 'unknown')
                        print(f"   工具名称: {tool_name}")

                        # 尝试不同的参数
                        for args in [
                            {"location": "北京"},
                            {"location": "Beijing"},
                            {"city": "北京"},
                            {"query": "北京天气"}
                        ]:
                            try:
                                print(f"\n   尝试参数: {json.dumps(args, ensure_ascii=False)}")
                                result = await client.call_tool(tool_name, args)
                                print(f"   ✅ 调用成功!")
                                print(f"   结果: {json.dumps(result, indent=4, ensure_ascii=False)}")
                                break
                            except Exception as e:
                                print(f"   ⚠️  参数 {json.dumps(args, ensure_ascii=False)} 失败: {str(e)[:100]}")
                    else:
                        print("   未找到天气相关工具，尝试调用第一个工具...")
                        first_tool = tools[0]
                        tool_name = first_tool.get('name', 'unknown') if isinstance(first_tool, dict) else getattr(first_tool, 'name', 'unknown')
                        print(f"   工具名称: {tool_name}")

                        # 尝试通用参数
                        try:
                            result = await client.call_tool(tool_name, {"query": "test"})
                            print(f"   ✅ 调用成功!")
                            print(f"   结果: {json.dumps(result, indent=4, ensure_ascii=False)}")
                        except Exception as e:
                            print(f"   ⚠️  调用失败: {str(e)[:100]}")
        else:
            print("\n📋 使用旧版 API 列出工具...")
            transport = StreamableHttpTransport(url=mcp_url)
            async with Client(transport) as client:
                tools = await client.list_tools()
                print(f"✅ 可用工具数量: {len(tools) if tools else 0}")

                if tools:
                    for tool in tools:
                        print(f"  - {tool}")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*60}")


async def test_react_with_mcp():
    """测试 ReAct Agent 与 MCP 集成"""
    print(f"\n{'='*60}")
    print(f"测试 ReAct Agent 与 MCP 集成")
    print(f"{'='*60}")

    from services.true_react_agent import TrueReActAgent
    from config import settings

    # 打印当前配置
    print(f"\n当前 MCP 服务器配置: {settings.mcp_server_url}")

    # 创建 ReAct Agent
    agent = TrueReActAgent()

    try:
        # 初始化 Agent
        await agent.initialize()

        # 测试查询
        query = "请帮我查询北京今天天气"

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

        # 检查是否使用了 MCP 工具
        mcp_used = False
        for step in result.get('steps', []):
            if step.get('tool_name') == 'mcp_call_tool':
                mcp_used = True
                print(f"\n✅ 检测到使用了 MCP 工具!")
                print(f"工具参数: {json.dumps(step.get('tool_args', {}), ensure_ascii=False)}")
                print(f"工具结果: {json.dumps(step.get('tool_result', {}), ensure_ascii=False)}")

        if not mcp_used:
            print(f"\n⚠️  未使用 MCP 工具，可能使用了其他工具（如 web_search）")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*60}")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("天气 MCP 服务器测试")
    print("=" * 60)

    # 测试 1: 直接测试 MCP 服务器
    await test_mcp_server()

    # 测试 2: 测试 ReAct Agent 与 MCP 集成
    await test_react_with_mcp()

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
