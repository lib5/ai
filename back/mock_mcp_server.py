"""
ModelScope MCP 模拟服务器
用于测试 MCP 客户端功能
"""

import asyncio
import json
from aiohttp import web, ClientSession
from typing import Dict, Any, List

class MockMCP:
    """MCP 模拟服务"""

    def __init__(self):
        self.models = [
            {
                "id": "AI-ModelScope/resnet50",
                "name": "ResNet-50",
                "description": "深度残差网络模型",
                "task": "image_classification"
            },
            {
                "id": "AI-ModelScope/bert-base",
                "name": "BERT Base",
                "description": "双向编码器表示模型",
                "task": "text_classification"
            },
            {
                "id": "AI-ModelScope/diffusion-v1-5",
                "name": "Stable Diffusion v1.5",
                "description": "文本到图像生成模型",
                "task": "text_to_image"
            }
        ]

    async def handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具列表请求"""
        return {
            "tools": [
                {
                    "name": "modelscope.search_model",
                    "description": "搜索 ModelScope 模型",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "default": 10}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "modelscope.get_model_info",
                    "description": "获取模型详细信息",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "model_id": {"type": "string"}
                        },
                        "required": ["model_id"]
                    }
                },
                {
                    "name": "modelscope.download_dataset",
                    "description": "下载数据集",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "dataset_id": {"type": "string"},
                            "subset": {"type": "string"}
                        },
                        "required": ["dataset_id"]
                    }
                },
                {
                    "name": "modelscope.test_streaming",
                    "description": "测试流式处理功能",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "object"}
                        },
                        "required": ["data"]
                    }
                }
            ]
        }

    async def handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name == "modelscope.search_model":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 10)

            # 简单的模糊搜索
            filtered_models = [
                model for model in self.models
                if query.lower() in model["name"].lower() or query.lower() in model["description"].lower()
            ][:limit]

            return {
                "models": filtered_models,
                "total": len(filtered_models)
            }

        elif name == "modelscope.get_model_info":
            model_id = arguments.get("model_id", "")
            model = next((m for m in self.models if m["id"] == model_id), None)

            if model:
                return {
                    **model,
                    "downloads": 100000,
                    "likes": 95,
                    "tags": ["pytorch", "computer_vision"],
                    "created_at": "2023-01-01T00:00:00Z"
                }
            else:
                return {"error": "模型未找到"}

        elif name == "modelscope.download_dataset":
            dataset_id = arguments.get("dataset_id", "")
            subset = arguments.get("subset")

            return {
                "dataset_id": dataset_id,
                "subset": subset,
                "status": "downloading",
                "progress": 0,
                "download_url": f"https://modelscope.cn/datasets/{dataset_id}"
            }

        elif name == "modelscope.test_streaming":
            data = arguments.get("data", {})

            # 模拟流式返回
            return {
                "status": "streaming",
                "data": data,
                "chunks": [
                    {"chunk_id": 1, "content": "第一部分数据"},
                    {"chunk_id": 2, "content": "第二部分数据"},
                    {"chunk_id": 3, "content": "第三部分数据"}
                ]
            }

        else:
            return {"error": f"未知工具: {name}"}

    async def handle_list_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理资源列表请求"""
        return {
            "resources": [
                {
                    "uri": "modelscope://models/resnet50",
                    "name": "ResNet-50 模型",
                    "description": "ImageNet 预训练的 ResNet-50 模型"
                },
                {
                    "uri": "modelscope://datasets/cifar10",
                    "name": "CIFAR-10 数据集",
                    "description": "CIFAR-10 图像分类数据集"
                }
            ]
        }

    async def handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理资源读取请求"""
        uri = params.get("uri", "")

        if uri == "modelscope://models/resnet50":
            return {
                "uri": uri,
                "name": "ResNet-50 模型",
                "content": "模型详细信息和下载链接..."
            }
        else:
            return {"error": "资源未找到"}

async def mcp_handler(request):
    """MCP 请求处理器"""
    try:
        data = await request.json()
        method = data.get("method")
        params = data.get("params", {})

        mock_mcp = MockMCP()

        if method == "tools/list":
            result = await mock_mcp.handle_list_tools(params)
        elif method == "tools/call":
            result = await mock_mcp.handle_call_tool(params)
        elif method == "resources/list":
            result = await mock_mcp.handle_list_resources(params)
        elif method == "resources/read":
            result = await mock_mcp.handle_read_resource(params)
        else:
            result = {"error": f"未知方法: {method}"}

        return web.json_response({
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": result
        })

    except Exception as e:
        return web.json_response({
            "jsonrpc": "2.0",
            "id": data.get("id") if 'data' in locals() else None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }, status=500)

async def init_app():
    """初始化应用"""
    app = web.Application()
    app.router.add_post("/mcp/rpc", mcp_handler)
    return app

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ModelScope MCP 模拟服务器")
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机")
    parser.add_argument("--port", type=int, default=3000, help="服务器端口")

    args = parser.parse_args()

    print(f"启动 ModelScope MCP 模拟服务器...")
    print(f"地址: http://{args.host}:{args.port}")
    print(f"MCP 端点: http://{args.host}:{args.port}/mcp/rpc")

    web.run_app(init_app(), host=args.host, port=args.port)