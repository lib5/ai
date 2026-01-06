#!/usr/bin/env python3
"""
检查 MCP 服务器上可用的工具
"""
import asyncio
import os
from services.multi_mcp_client import MultiMCPClient
from config import settings

async def main():
    print("=" * 60)
    print("检查 MCP 服务器工具")
    print("=" * 60)

    # 创建多 MCP 客户端
    multi_mcp = MultiMCPClient()

    # 列出所有工具
    print("\n📋 列出所有 MCP 服务器的工具...")
    all_tools = await multi_mcp.list_all_tools()

    print(f"\n✅ 总共找到 {len(multi_mcp.get_available_tools())} 个工具:")
    for tool_name in multi_mcp.get_available_tools():
        server = multi_mcp.get_tool_server(tool_name)
        print(f"  - {tool_name} (来自 {server})")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
