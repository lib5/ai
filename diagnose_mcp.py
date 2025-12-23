#!/usr/bin/env python3
"""
诊断 MCP 工具无法获取的问题
"""
import asyncio
import sys
import traceback
from services.multi_mcp_client import MultiMCPClient
from config import settings

async def diagnose_mcp():
    print("=" * 80)
    print("MCP 工具获取诊断")
    print("=" * 80)

    # 1. 检查配置
    print("\n📋 1. 检查配置:")
    print(f"  MCP_SERVER_URL: {settings.mcp_server_url}")
    print(f"  TEST_MCP_BASE_URL: {settings.test_mcp_base_url}")
    print(f"  MCP_SERVICE_TOKEN: {settings.mcp_service_token}")

    # 2. 尝试创建 MultiMCPClient
    print("\n📋 2. 创建 MultiMCPClient:")
    try:
        multi_mcp = MultiMCPClient()
        print("  ✅ MultiMCPClient 创建成功")
    except Exception as e:
        print(f"  ❌ MultiMCPClient 创建失败: {e}")
        traceback.print_exc()
        return

    # 3. 尝试列出工具
    print("\n📋 3. 尝试列出所有工具:")
    try:
        all_tools = await multi_mcp.list_all_tools()
        print(f"  ✅ 工具列表获取成功")

        available_tools = multi_mcp.get_available_tools()
        print(f"\n  📊 统计信息:")
        print(f"    - 总共服务器数: {len(all_tools)}")
        print(f"    - 可用工具数: {len(available_tools)}")

        if available_tools:
            print(f"\n  🛠️  可用工具列表:")
            for tool_name in available_tools:
                server = multi_mcp.get_tool_server(tool_name)
                tool_info = multi_mcp.get_tool_info(tool_name)
                print(f"    - {tool_name} (来自 {server})")
                if tool_info and tool_info.get('schema'):
                    schema = tool_info['schema']
                    if isinstance(schema, dict) and 'properties' in schema:
                        props = schema['properties']
                        print(f"      参数: {list(props.keys())}")
        else:
            print(f"\n  ⚠️  没有找到任何可用工具!")

    except Exception as e:
        print(f"  ❌ 工具列表获取失败: {e}")
        traceback.print_exc()

    # 4. 尝试调用第一个工具（如果存在）
    print("\n📋 4. 尝试调用工具测试:")
    try:
        available_tools = multi_mcp.get_available_tools()
        if available_tools:
            first_tool = available_tools[0]
            print(f"  测试调用工具: {first_tool}")

            # 尝试获取工具信息
            tool_info = multi_mcp.get_tool_info(first_tool)
            if tool_info:
                schema = tool_info.get('schema')
                print(f"  工具描述: {tool_info.get('description', 'N/A')}")

                # 准备测试参数
                test_args = {}
                if isinstance(schema, dict) and 'properties' in schema:
                    for param_name in schema['properties'].keys():
                        # 设置测试值
                        if 'city' in param_name.lower():
                            test_args[param_name] = "北京"
                        elif 'user_id' in param_name.lower():
                            test_args[param_name] = "test_user"
                        elif 'query' in param_name.lower():
                            test_args[param_name] = "测试查询"
                        else:
                            test_args[param_name] = "test_value"

                print(f"  测试参数: {test_args}")

                result = await multi_mcp.call_tool(first_tool, test_args)
                print(f"  ✅ 工具调用完成")
                print(f"  结果: {result}")

            else:
                print(f"  ⚠️  无法获取工具信息")
        else:
            print(f"  ⚠️  没有可用工具进行测试")

    except Exception as e:
        print(f"  ❌ 工具调用失败: {e}")
        traceback.print_exc()

    # 5. 检查 fastmcp 版本
    print("\n📋 5. 检查 fastmcp 版本:")
    try:
        import fastmcp
        print(f"  ✅ fastmcp 版本: {fastmcp.__version__}")
    except ImportError:
        print(f"  ❌ fastmcp 未安装")
    except Exception as e:
        print(f"  ⚠️  无法获取 fastmcp 版本: {e}")

    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(diagnose_mcp())
