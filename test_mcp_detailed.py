#!/usr/bin/env python3
"""
详细的 MCP 工具调用测试
"""
import asyncio
import json
import uuid
from services.multi_mcp_client import MultiMCPClient

async def test_tool_calls():
    """测试各种工具调用"""
    print("=" * 70)
    print("MCP 工具调用详细测试")
    print("=" * 70)

    # 初始化客户端
    multi_mcp = MultiMCPClient()

    # 列出所有工具
    print("\n📋 获取工具列表...")
    all_tools = await multi_mcp.list_all_tools()
    available_tools = multi_mcp.get_available_tools()

    print(f"\n✅ 发现 {len(available_tools)} 个可用工具:")
    for tool_name in available_tools:
        server = multi_mcp.get_tool_server(tool_name)
        print(f"  - {tool_name} (来自 {server})")

    # 生成测试用 UUID
    test_user_id = str(uuid.uuid4())
    test_contact_id = str(uuid.uuid4())
    test_schedule_id = str(uuid.uuid4())

    print(f"\n🔑 测试用 UUID:")
    print(f"  - user_id: {test_user_id}")
    print(f"  - contact_id: {test_contact_id}")
    print(f"  - schedule_id: {test_schedule_id}")

    # 测试联系人相关工具
    print("\n" + "-" * 70)
    print("测试 1: 联系人管理工具")
    print("-" * 70)

    # 1.1 创建联系人
    if "contacts_create" in available_tools:
        print("\n1.1 创建联系人")
        result = await multi_mcp.call_tool("contacts_create", {
            "user_id": test_user_id,
            "name": "张三",
            "company": "测试公司",
            "position": "工程师",
            "phone": "13800138001",
            "email": "zhangsan@example.com",
            "relationship_type": "colleague"
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if result.get("success"):
            contact_id = result.get("result", {}).get("data", {}).get("id")
            if contact_id:
                test_contact_id = contact_id

    # 1.2 搜索联系人
    if "contacts_search" in available_tools:
        print("\n1.2 搜索联系人")
        result = await multi_mcp.call_tool("contacts_search", {
            "user_id": test_user_id,
            "name": "张三"
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 1.3 更新联系人
    if "contacts_update" in available_tools:
        print("\n1.3 更新联系人")
        result = await multi_mcp.call_tool("contacts_update", {
            "user_id": test_user_id,
            "id": test_contact_id,
            "name": "张三丰",
            "company": "新公司",
            "position": "高级工程师"
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 测试日程相关工具
    print("\n" + "-" * 70)
    print("测试 2: 日程管理工具")
    print("-" * 70)

    # 2.1 创建日程
    if "schedules_create" in available_tools:
        print("\n2.1 创建日程")
        result = await multi_mcp.call_tool("schedules_create", {
            "user_id": test_user_id,
            "title": "团队会议",
            "description": "讨论项目进展",
            "start_time": "2025-01-01T10:00:00",
            "end_time": "2025-01-01T11:00:00",
            "location": "会议室 A",
            "category": "meeting"
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if result.get("success"):
            schedule_id = result.get("result", {}).get("data", {}).get("id")
            if schedule_id:
                test_schedule_id = schedule_id

    # 2.2 搜索日程
    if "schedules_search" in available_tools:
        print("\n2.2 搜索日程")
        result = await multi_mcp.call_tool("schedules_search", {
            "user_id": test_user_id,
            "title": "团队会议"
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 2.3 更新日程
    if "schedules_update" in available_tools:
        print("\n2.3 更新日程")
        result = await multi_mcp.call_tool("schedules_update", {
            "user_id": test_user_id,
            "id": test_schedule_id,
            "title": "重要团队会议",
            "description": "讨论项目进展和下阶段计划",
            "location": "会议室 B"
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 测试聊天消息搜索
    print("\n" + "-" * 70)
    print("测试 3: 聊天消息搜索")
    print("-" * 70)

    if "chat_messages_search" in available_tools:
        print("\n3.1 搜索聊天消息")
        result = await multi_mcp.call_tool("chat_messages_search", {
            "user_id": test_user_id,
            "query": "测试消息"
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 清理测试数据
    print("\n" + "-" * 70)
    print("测试 4: 清理测试数据")
    print("-" * 70)

    # 4.1 删除日程
    if "schedules_delete" in available_tools:
        print("\n4.1 删除日程")
        result = await multi_mcp.call_tool("schedules_delete", {
            "id": test_schedule_id
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 4.2 删除联系人
    if "contacts_delete" in available_tools:
        print("\n4.2 删除联系人")
        result = await multi_mcp.call_tool("contacts_delete", {
            "id": test_contact_id
        })
        print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)

async def test_tool_info():
    """测试工具信息获取"""
    print("\n" + "=" * 70)
    print("工具信息获取测试")
    print("=" * 70)

    multi_mcp = MultiMCPClient()
    await multi_mcp.list_all_tools()

    # 获取特定工具的详细信息
    tool_names = ["contacts_create", "schedules_search", "chat_messages_search"]

    for tool_name in tool_names:
        if tool_name in multi_mcp.get_available_tools():
            print(f"\n📋 工具信息: {tool_name}")
            tool_info = multi_mcp.get_tool_info(tool_name)
            if tool_info:
                print(f"  名称: {tool_info.get('name')}")
                print(f"  描述: {tool_info.get('description')}")
                print(f"  服务器: {tool_info.get('server')}")
                schema = tool_info.get('schema')
                if schema and isinstance(schema, dict):
                    properties = schema.get('properties', {})
                    required = schema.get('required', [])
                    print(f"  必需参数: {required}")
                    print(f"  可选参数: {[k for k in properties.keys() if k not in required]}")

    print("\n" + "=" * 70)

async def main():
    """主函数"""
    await test_tool_calls()
    await test_tool_info()

if __name__ == "__main__":
    asyncio.run(main())
