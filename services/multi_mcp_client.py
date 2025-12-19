#!/usr/bin/env python3
"""
多 MCP 服务器管理服务
支持同时连接多个 MCP 服务器并调用它们的工具
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from config import settings

# 尝试导入 fastmcp
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


class MultiMCPClient:
    """
    多 MCP 服务器客户端

    可以同时管理多个 MCP 服务器，并根据工具类型选择合适的服务器
    """

    def __init__(self):
        """初始化多 MCP 客户端"""
        self.servers = {}
        self.tools_index = {}  # 工具名称到服务器 URL 的映射
        self.tools_info = {}  # 工具名称到完整工具信息的映射（包含参数模式）

        # 初始化 MCP 服务器
        self._init_servers()

    def _init_servers(self):
        """初始化 MCP 服务器"""
        # 服务器 1: 中文必应搜索 MCP 服务器
        search_url = settings.mcp_server_url
        if search_url:
            self.servers["bing-cn-search"] = {
                "url": search_url,
                "service_token": None,
                "description": "中文必应搜索 MCP 服务器"
            }

        # 服务器 2: 本地测试 MCP 服务器（联系人、文件、日程管理）
        test_mcp_url = settings.test_mcp_base_url
        if test_mcp_url:
            self.servers["test_mcp"] = {
                "url": test_mcp_url,
                "service_token": settings.mcp_service_token,
                "description": "测试 MCP 服务器（联系人、文件、日程管理）"
            }

        print(f"[MultiMCP] 初始化了 {len(self.servers)} 个 MCP 服务器:")
        for name, server in self.servers.items():
            print(f"  - {name}: {server['url']}")
            if server['service_token']:
                print(f"    令牌: {server['service_token'][:10]}...")

    def _build_url(self, server_url: str, service_token: Optional[str] = None) -> str:
        """构建带认证的 URL"""
        if service_token and "key=" not in server_url:
            return f"{server_url}?key={service_token}"
        return server_url

    async def list_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        列出所有 MCP 服务器上的所有工具

        Returns:
            字典，键为服务器名，值为工具列表
        """
        all_tools = {}

        for server_name, server_info in self.servers.items():
            print(f"\n📋 列出 {server_name} ({server_info['description']}) 的工具...")
            try:
                url = self._build_url(server_info['url'], server_info['service_token'])
                tools = await self._list_tools_from_server(url)
                all_tools[server_name] = tools

                # 打印工具列表并保存完整工具信息
                for tool in tools:
                    tool_name = "unknown"
                    tool_desc = ""
                    tool_schema = None

                    # 提取工具名称
                    if isinstance(tool, dict):
                        tool_name = tool.get('name', 'unknown')
                        tool_desc = tool.get('description', '')
                        tool_schema = tool.get('inputSchema') or tool.get('input_schema') or tool.get('schema')
                    elif hasattr(tool, 'name'):
                        name_attr = tool.name
                        tool_name = name_attr() if callable(name_attr) else str(name_attr)
                        tool_desc = getattr(tool, 'description', '')
                        # 尝试获取参数模式
                        for attr_name in ['inputSchema', 'input_schema', 'schema', 'parameters']:
                            tool_schema = getattr(tool, attr_name, None)
                            if tool_schema is not None:
                                break
                    elif hasattr(tool, '__name__'):
                        tool_name = str(tool.__name__)

                    print(f"  - {tool_name}")
                    # 建立工具索引
                    if tool_name != "unknown":
                        self.tools_index[tool_name] = server_name
                        # 保存完整的工具信息（包含参数模式）
                        self.tools_info[tool_name] = {
                            'name': tool_name,
                            'description': tool_desc,
                            'schema': tool_schema,
                            'server': server_name
                        }

            except Exception as e:
                print(f"⚠️  列出 {server_name} 工具失败: {str(e)}")
                import traceback
                traceback.print_exc()
                all_tools[server_name] = []

        return all_tools

    async def _list_tools_from_server(self, url: str) -> List[Dict[str, Any]]:
        """从单个服务器列出工具"""
        # 使用 FastMCPClient 包装器以确保一致性
        try:
            from .mcp_client import FastMCPClient
        except ImportError:
            # 直接运行时的备选方案
            from mcp_client import FastMCPClient

        async with FastMCPClient(url) as client:
            return await client.list_tools()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用指定工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        # 查找工具所属的服务器
        server_name = self.tools_index.get(tool_name)
        if not server_name:
            return {
                "success": False,
                "error": f"未找到工具 '{tool_name}'",
                "tool_name": tool_name,
                "arguments": arguments
            }

        server_info = self.servers[server_name]
        print(f"\n🧪 在 {server_name} ({server_info['description']}) 调用工具: {tool_name}")
        print(f"   参数: {json.dumps(arguments, ensure_ascii=False)}")

        try:
            url = self._build_url(server_info['url'], server_info['service_token'])

            if USE_NEW_API:
                async with streamable_http_client(url) as client:
                    result = await client.call_tool(tool_name, arguments)
                    # 格式化结果
                    try:
                        from .mcp_client import FastMCPClient
                    except ImportError:
                        from mcp_client import FastMCPClient
                    client_instance = FastMCPClient(url)
                    formatted_result = client_instance._format_result(result)
                    extracted_data = client_instance.extract_response_data(formatted_result)

                    return {
                        "success": True,
                        "result": extracted_data,
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "server": server_name,
                        "raw_result": formatted_result
                    }
            else:
                transport = StreamableHttpTransport(url=url)
                async with Client(transport) as client:
                    result = await client.call_tool(tool_name, arguments)
                    # 格式化结果
                    try:
                        from .mcp_client import FastMCPClient
                    except ImportError:
                        from mcp_client import FastMCPClient
                    client_instance = FastMCPClient(url)
                    formatted_result = client_instance._format_result(result)
                    extracted_data = client_instance.extract_response_data(formatted_result)

                    return {
                        "success": True,
                        "result": extracted_data,
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "server": server_name,
                        "raw_result": formatted_result
                    }

        except Exception as e:
            error_msg = f"在 {server_name} 调用工具 '{tool_name}' 失败: {str(e)}"
            print(f"[MultiMCP ERROR] {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "tool_name": tool_name,
                "arguments": arguments,
                "server": server_name
            }

    def get_available_tools(self) -> List[str]:
        """获取所有可用工具的名称列表"""
        return list(self.tools_index.keys())

    def get_tool_server(self, tool_name: str) -> Optional[str]:
        """获取工具所属的服务器名称"""
        return self.tools_index.get(tool_name)

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具的完整信息（包含参数模式）"""
        return self.tools_info.get(tool_name)


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


def main():
    """主函数"""
    asyncio.run(test_multi_mcp_client())


if __name__ == "__main__":
    main()
