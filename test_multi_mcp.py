#!/usr/bin/env python3
"""
测试多 MCP 服务器集成
"""
import asyncio
import json
from services.multi_mcp_client import MultiMCPClient
from services.true_react_agent import TrueReActAgent
from config import settings


async def test_multi_mcp_client():
    """测试多 MCP 客户端"""
    print("\n" + "=" * 60)
    print("多 MCP 客户端测试")
    print("=" * 60)

    # 创建客户端
    multi_mcp = MultiMCPClient()

    # 列出所有工具
    print("\n📋 列出所有 MCP 服务器的工具...")
    all_tools = await multi_mcp.list_all_tools()

    print(f"\n✅ 总共找到 {len(multi_mcp.get_available_tools())} 个工具:")
    for tool_name in multi_mcp.get_available_tools():
        server = multi_mcp.get_tool_server(tool_name)
        print(f"  - {tool_name} (来自 {server})")

    # 测试调用工具
    print("\n🧪 测试调用工具...")

    # 测试天气工具（如果存在）
    if "get_weather" in multi_mcp.get_available_tools():
        print("\n测试天气工具:")
        result = await multi_mcp.call_tool("get_weather", {
            "city": "北京",
            "units": "metric",
            "lang": "zh_cn"
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 测试联系人工具（如果存在）
    if "contacts_create" in multi_mcp.get_available_tools():
        print("\n测试联系人工具:")
        result = await multi_mcp.call_tool("contacts_create", {
            "user_id": "test_user",
            "name": "测试联系人",
            "company": "测试公司",
            "phone": "13800138000",
            "email": "test@example.com",
            "relationship_type": "client",
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 测试用户工具（如果存在）
    if "users_add_metadata" in multi_mcp.get_available_tools():
        print("\n测试用户工具:")
        result = await multi_mcp.call_tool("users_add_metadata", {
            "user_id": "test_user",
            "username": "test_user",
            "email": "test@example.com",
            "city": "北京",
            "company": "测试公司",
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    print("\n" + "=" * 60)


async def test_react_with_multi_mcp():
    """测试 ReAct Agent 与多 MCP 集成"""
    print("\n" + "=" * 60)
    print("测试 ReAct Agent 与多 MCP 集成")
    print("=" * 60)

    # 创建 ReAct Agent
    agent = TrueReActAgent()

    try:
        # 初始化 Agent
        await agent.initialize()

        print(f"\n✅ ReAct Agent 初始化成功")
        print(f"   多 MCP 客户端: {agent.multi_mcp_client}")

        # 手动调用 MCP 工具
        print(f"\n🧪 手动调用 MCP 工具...")

        # 测试联系人工具
        if agent.multi_mcp_client and "contacts_create" in agent.multi_mcp_client.get_available_tools():
            print(f"\n测试联系人工具:")
            mcp_result = await agent._tool_mcp_call_tool("contacts_create", {
                "user_id": "test_user",
                "name": "测试联系人",
                "company": "测试公司",
                "phone": "13800138000",
                "email": "test@example.com",
                "relationship_type": "client",
            })

            if mcp_result.get('success'):
                print(f"✅ MCP 工具调用成功!")
                if 'result' in mcp_result:
                    print(f"结果:")
                    print(json.dumps(mcp_result['result'], indent=2, ensure_ascii=False))
            else:
                print(f"⚠️  MCP 工具调用失败:")
                print(f"错误: {mcp_result.get('error')}")
        else:
            print(f"⚠️  联系人工具不可用")

        # 测试用户工具
        if agent.multi_mcp_client and "users_add_metadata" in agent.multi_mcp_client.get_available_tools():
            print(f"\n测试用户工具:")
            mcp_result = await agent._tool_mcp_call_tool("users_add_metadata", {
                "user_id": "test_user",
                "username": "test_user",
                "email": "test@example.com",
                "city": "北京",
                "company": "测试公司",
            })

            if mcp_result.get('success'):
                print(f"✅ MCP 工具调用成功!")
                if 'result' in mcp_result:
                    print(f"结果:")
                    print(json.dumps(mcp_result['result'], indent=2, ensure_ascii=False))
            else:
                print(f"⚠️  MCP 工具调用失败:")
                print(f"错误: {mcp_result.get('error')}")
        else:
            print(f"⚠️  用户工具不可用")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


async def test_react_queries():
    """测试 ReAct Agent 处理各种查询"""
    print("\n" + "=" * 60)
    print("测试 ReAct Agent 处理各种查询")
    print("=" * 60)

    agent = TrueReActAgent()
    await agent.initialize()

    # 测试查询列表
    test_queries = [
        "请帮我创建一个联系人",
        "查询用户信息",
        "获取北京天气",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"查询: {query}")
        print(f"{'='*60}")

        try:
            result = await agent.run(query)

            print(f"\n执行结果:")
            print(f"  查询: {result.get('query', '')}")
            print(f"  答案: {result.get('answer', '')}")
            print(f"  迭代次数: {result.get('iterations', 0)}")
            print(f"  成功: {result.get('success', False)}")

            # 检查是否使用了 MCP 工具
            mcp_used = False
            for step in result.get('steps', []):
                if step.get('tool_name') == 'mcp_call_tool':
                    mcp_used = True
                    print(f"\n✅ 检测到使用了 MCP 工具!")
                    print(f"  工具参数: {json.dumps(step.get('tool_args', {}), ensure_ascii=False)}")
                    print(f"  工具结果: {json.dumps(step.get('tool_result', {}), ensure_ascii=False)}")

            if not mcp_used:
                print(f"\n⚠️  未使用 MCP 工具，可能使用了其他工具")

        except Exception as e:
            print(f"❌ 查询失败: {str(e)}")

    print("\n" + "=" * 60)


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("多 MCP 服务器集成测试")
    print("=" * 60)

    # 测试 1: 多 MCP 客户端
    await test_multi_mcp_client()

    # 测试 2: ReAct Agent 与多 MCP 集成
    await test_react_with_multi_mcp()

    # 测试 3: ReAct 查询处理
    await test_react_queries()

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
