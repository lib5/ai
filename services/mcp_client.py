import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# 尝试导入 fastmcp
try:
    from fastmcp import streamable_http_client
    HAS_FASTMCP = True
except ImportError:
    try:
        from fastmcp import Client
        from fastmcp.client.transports import StreamableHttpTransport
        HAS_FASTMCP = True
    except ImportError:
        HAS_FASTMCP = False

class MCPClient:
    """MCP (Model Context Protocol) 客户端"""

    def __init__(self, server_url: str = "http://localhost:3000"):
        self.server_url = server_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def send_request(
        self,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        发送 MCP 请求

        Args:
            method: MCP 方法名
            params: 请求参数

        Returns:
            响应数据
        """
        if not self.session:
            raise Exception("MCP 客户端未初始化")

        url = f"{self.server_url}/mcp/rpc"
        payload = {
            "jsonrpc": "2.0",
            "id": int(datetime.now().timestamp() * 1000),
            "method": method,
            "params": params
        }

        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"MCP 请求失败: {response.status} - {error_text}")

        except aiohttp.ClientError as e:
            raise Exception(f"MCP 客户端错误: {str(e)}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用的工具"""
        result = await self.send_request("tools/list", {})
        tools = result.get("result", {}).get("tools", [])

        # Print MCP tools
        print(f"\n=== MCP Server Tools ({len(tools)} total) ===")
        for tool in tools:
            print(f"  - {tool.get('name', 'unknown')}: {tool.get('description', 'no description')}")
        print("==================================\n")

        return tools

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用指定工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        # Print tool call
        print(f"\n[MCP] Calling tool: {name}")
        print(f"[MCP] Arguments: {arguments}")

        result = await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        # Print result
        print(f"[MCP] Tool '{name}' completed")

        return result.get("result", {})

    async def get_resources(self) -> List[Dict[str, Any]]:
        """获取可用资源"""
        result = await self.send_request("resources/list", {})
        return result.get("result", {}).get("resources", [])

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """读取指定资源"""
        result = await self.send_request("resources/read", {
            "uri": uri
        })
        return result.get("result", {})

class ModelscopeMCPClient(MCPClient):
    """ModelScope MCP 客户端特化版本"""

    async def search_model(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索 ModelScope 模型

        Args:
            query: 搜索查询
            limit: 返回结果数量限制

        Returns:
            模型列表
        """
        result = await self.call_tool("modelscope.search_model", {
            "query": query,
            "limit": limit
        })
        return result.get("models", [])

    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """
        获取模型详细信息

        Args:
            model_id: 模型 ID

        Returns:
            模型信息
        """
        result = await self.call_tool("modelscope.get_model_info", {
            "model_id": model_id
        })
        return result

    async def download_dataset(self, dataset_id: str, subset: Optional[str] = None) -> Dict[str, Any]:
        """
        下载 ModelScope 数据集

        Args:
            dataset_id: 数据集 ID
            subset: 数据子集

        Returns:
            下载结果
        """
        result = await self.call_tool("modelscope.download_dataset", {
            "dataset_id": dataset_id,
            "subset": subset
        })
        return result

    async def test_streaming(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        测试流式处理功能

        Args:
            data: 测试数据

        Returns:
            测试结果
        """
        result = await self.call_tool("modelscope.test_streaming", {
            "data": data
        })
        return result


class FastMCPClient:
    """
    通用 MCP 客户端 - 基于 fastmcp 库
    可以连接任何 MCP 服务器并调用工具
    """

    def __init__(self, server_url: str, service_token: Optional[str] = None):
        """
        初始化 FastMCP 客户端

        Args:
            server_url: MCP 服务器 URL
            service_token: 服务令牌（可选）
        """
        if not HAS_FASTMCP:
            raise ImportError(
                "fastmcp 库未安装。请运行: pip install fastmcp>=2.8.0,<2.12.0"
            )

        self.server_url = server_url
        self.service_token = service_token
        self._client = None
        # 强制使用旧 API，避免上下文管理器问题
        self.USE_NEW_API = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()

    async def connect(self):
        """连接到 MCP 服务器"""
        try:
            # 旧的 API：使用 Client + StreamableHttpTransport
            from fastmcp import Client
            from fastmcp.client.transports import StreamableHttpTransport

            if self.service_token and "key=" not in self.server_url:
                url = f"{self.server_url}?key={self.service_token}"
            else:
                url = self.server_url

            transport = StreamableHttpTransport(url=url)
            # 注意：Client 对象本身是上下文管理器
            self._client = Client(transport)
        except Exception as e:
            raise Exception(f"连接 MCP 服务器失败: {str(e)}")

    async def disconnect(self):
        """断开与 MCP 服务器的连接"""
        if hasattr(self, '_client') and self._client:
            await self._client.close()

    @property
    def client(self):
        """获取内部客户端（如果在上下文中）"""
        if self._client is None:
            raise RuntimeError("客户端未连接。请使用 'async with client:' 上下文管理器")
        return self._client

    def _format_result(self, result):
        """
        格式化结果，将 CallToolResult、TextContent 等对象转换为可序列化的格式

        Args:
            result: 原始结果

        Returns:
            格式化后的结果
        """
        # 处理 None
        if result is None:
            return None

        # 处理基本类型
        if isinstance(result, (str, int, float, bool)):
            return result

        # 处理列表
        if isinstance(result, list):
            return [self._format_result(item) for item in result]

        # 处理字典
        if isinstance(result, dict):
            return {key: self._format_result(value) for key, value in result.items()}

        # 处理 CallToolResult 对象
        if hasattr(result, 'content'):
            formatted_content = self._format_result(result.content)
            return {
                "content": formatted_content,
                "isError": getattr(result, 'isError', False),
            }

        # 处理 TextContent 对象
        if hasattr(result, 'text'):
            return {
                "type": "text",
                "text": getattr(result, 'text', str(result)),
            }

        # 处理其他有 __dict__ 的对象
        if hasattr(result, '__dict__'):
            return {key: self._format_result(value) for key, value in result.__dict__.items()}

        # 处理其他对象，尝试获取常见属性
        if hasattr(result, '__class__'):
            obj_dict = {}
            for attr in ['text', 'content', 'data', 'value', 'message', 'error']:
                if hasattr(result, attr):
                    obj_dict[attr] = self._format_result(getattr(result, attr))
            if obj_dict:
                return obj_dict

        # 最后尝试转换为字符串
        return str(result)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出 MCP 服务器上的所有可用工具

        Returns:
            工具列表
        """
        if self._client is None:
            raise Exception("MCP 客户端未连接。请使用 'async with client:' 上下文管理器")

        try:
            # 直接在客户端的上下文中调用
            async with self._client:
                tools = await self._client.list_tools()
                return tools
        except Exception as e:
            raise Exception(f"列出工具失败: {str(e)}")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if self._client is None:
            raise Exception("MCP 客户端未连接。请使用 'async with client:' 上下文管理器")

        try:
            # 直接在客户端的上下文中调用
            async with self._client:
                result = await self._client.call_tool(name, arguments)
                return self._format_result(result)
        except Exception as e:
            raise Exception(f"调用工具 '{name}' 失败: {str(e)}")

    @staticmethod
    def format_tools_for_llm(tool) -> str:
        """
        格式化工具信息用于 LLM

        Args:
            tool: 工具对象

        Returns:
            格式化的工具描述
        """
        args_desc = []

        # FastMCP 工具对象可能使用 inputSchema 或 input_schema
        schema = None
        for attr_name in ['inputSchema', 'input_schema', 'schema', 'parameters']:
            schema = getattr(tool, attr_name, None)
            if schema is not None:
                break

        # 如果 schema 是对象而非字典，尝试转换
        if schema is not None and hasattr(schema, '__dict__'):
            schema = vars(schema) if not isinstance(schema, dict) else schema

        # 如果 schema 有 model_dump 方法（Pydantic 模型）
        if schema is not None and hasattr(schema, 'model_dump'):
            schema = schema.model_dump()

        if isinstance(schema, dict) and "properties" in schema:
            properties = schema["properties"]
            required = schema.get("required", [])
            for param_name, param_info in properties.items():
                if isinstance(param_info, dict):
                    desc = param_info.get('description', 'No description')
                else:
                    desc = getattr(param_info, 'description', 'No description')
                arg_desc = f"- {param_name}: {desc}"
                if param_name in required:
                    arg_desc += " (required)"
                args_desc.append(arg_desc)

        tool_name = getattr(tool, 'name', 'unknown')
        tool_desc = getattr(tool, 'description', '')
        return f"Tool: {tool_name}\nDescription: {tool_desc}\nArguments:\n{chr(10).join(args_desc)}"

    @staticmethod
    def extract_response_data(formatted_result):
        """
        从 FastMCP 返回的格式化结果中提取实际的响应数据

        Args:
            formatted_result: 格式化结果

        Returns:
            提取的响应数据
        """
        if not isinstance(formatted_result, dict):
            return formatted_result

        # 如果直接包含 status，说明已经是解析后的数据
        if "status" in formatted_result:
            return formatted_result

        # 尝试从 content 中提取
        if "content" in formatted_result:
            content = formatted_result["content"]
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    text = first_item["text"]
                    # 尝试解析 JSON 字符串
                    try:
                        return json.loads(text)
                    except (json.JSONDecodeError, TypeError):
                        pass

        # 如果无法提取，返回原始格式
        return formatted_result