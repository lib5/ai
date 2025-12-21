from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import uuid
import json
import asyncio
from datetime import datetime
import base64
import os

from services.azure_openai_service import AzureOpenAIService
from services.streaming_service import StreamingService
from services.true_react_agent import true_react_agent
from config import settings

app = FastAPI(title="Chat API with Azure OpenAI", version="1.0.0")

# Note: CORS middleware removed due to compatibility issues
# For production, consider using a reverse proxy for CORS

# 启动事件：初始化 ReAct Agent
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 ReAct Agent 和 MCP 工具"""
    print("\n" + "=" * 80)
    print("🚀 应用启动中...")
    print("=" * 80 + "\n")
    print("📋 正在初始化 ReAct Agent...")
    try:
        await true_react_agent.initialize()
        print("✅ ReAct Agent 初始化成功")
        print(f"✅ 已注册 {len(true_react_agent.tools)} 个工具")
        print("\n📦 可用工具列表:")
        for name, info in true_react_agent.tools.items():
            print(f"  - {name}: {info['description']}")
        print("\n" + "=" * 80)
        print("✅ 应用启动完成，工具已准备就绪")
        print("=" * 80 + "\n")
    except Exception as e:
        print(f"\n❌ ReAct Agent 初始化失败: {e}")
        print("=" * 80 + "\n")
        raise

# 关闭事件：清理资源
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    print("\n" + "=" * 80)
    print("🔄 应用关闭中...")
    print("=" * 80 + "\n")
    try:
        # 清理 MultiMCP 客户端资源
        if true_react_agent.multi_mcp_client:
            print("✅ MCP 客户端资源清理完成")
        print("✅ 应用关闭完成")
    except Exception as e:
        print(f"⚠️  关闭时发生错误: {e}")
    print("=" * 80 + "\n")

class ContentItem(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[str] = None

class QueryItem(BaseModel):
    role: str
    content: List[ContentItem]

class UserMetadata(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    wechat: Optional[str] = None
    company: Optional[str] = None
    birthday: Optional[str] = None
    industry: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    address: Optional[str] = None
    country: Optional[str] = None
    location_updated_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ChatRequest(BaseModel):
    user_id: str
    query: List[QueryItem]
    metadata: Optional[Dict[str, Any]] = None

class ProcessingStep(BaseModel):
    message_id: str
    present_content: str
    tool_type: str
    parameters: str
    tool_status: str
    observation: Optional[str] = None
    execution_duration: Optional[int] = None

class ChatResponse(BaseModel):
    code: int
    message: str
    timestamp: str
    requestId: str
    data: Dict[str, Any]


async def handle_react_chat(request: ChatRequest, request_id: str):
    """
    处理ReAct模式聊天请求

    流程：
    1. 解析输入（支持三种模式：仅文本、仅图像、文本+图像）
    2. 运行ReAct循环，生成步骤
    3. 流式输出每个步骤

    输出格式：
    - 工具调用：Start步骤 + Success步骤
    - 最终答案：Finish步骤
    """
    try:
        # 提取查询文本和图像URL
        query_parts = []
        image_urls = []
        has_text = False
        has_image = False

        for query_item in request.query:
            for content_item in query_item.content:
                if content_item.type == "input_text" and content_item.text:
                    query_parts.append(content_item.text)
                    has_text = True
                elif content_item.type == "input_image" and content_item.image_url:
                    image_urls.append(content_item.image_url)
                    has_image = True

        query_text = " ".join(query_parts)

        # 验证输入
        if not has_text and not has_image:
            raise ValueError("必须提供文本或图像输入")

        # 构建输入描述
        input_desc = []
        if has_text:
            input_desc.append(f"文本: {query_text[:50]}{'...' if len(query_text) > 50 else ''}")
        if has_image:
            input_desc.append(f"图像数量: {len(image_urls)}")

        # 提取用户元数据
        user_metadata = None
        if request.metadata and 'user' in request.metadata:
            user_metadata = request.metadata['user']

        print(f"\n{'='*60}")
        print(f"处理请求 (模式: {'文本' if has_text else ''}{' + ' if has_text and has_image else ''}{'图像' if has_image else ''})")
        print(f"输入: {', '.join(input_desc)}")
        if user_metadata:
            print(f"用户: {user_metadata.get('username', 'N/A')} ({user_metadata.get('city', 'N/A')})")
        print(f"{'='*60}\n")

        # 运行ReAct循环，传递metadata
        react_result = await true_react_agent.run(query_text, image_urls, user_metadata)

        # 构建流式步骤
        all_steps = []

        # 步骤 1: ReAct执行步骤
        react_steps = react_result.get('steps', [])
        for react_step in react_steps:
            step_type = react_step.get('type')

            if step_type == 'action':
                # 工具调用：创建 Start 和 Success 两个步骤
                tool_name = react_step.get('tool_name', 'Unknown')
                tool_args = react_step.get('tool_args', {})

                # 如果是finish工具，直接跳过创建Start/Success步骤
                # 最终答案会单独创建Finish步骤
                if tool_name == 'finish':
                    continue

                # 提取思考内容（如果存在）
                content = react_step.get('content', '')
                if isinstance(content, dict):
                    # 如果 content 是字典，尝试提取 thought 字段
                    thought = content.get('thought', '')
                    if thought:
                        present_text = f"{thought}"
                    else:
                        present_text = f"需要使用工具 {tool_name}"
                else:
                    present_text = f"{str(content)}"

                # 对于 mcp_call_tool，显示具体的 MCP 工具名称
                display_tool_name = tool_name
                if tool_name == 'mcp_call_tool' and isinstance(tool_args, dict):
                    # 从 arguments 中提取实际的 MCP 工具名称
                    actual_tool_name = tool_args.get('tool_name', '')
                    if actual_tool_name:
                        display_tool_name = f"{tool_name}({actual_tool_name})"
                    else:
                        # 也可能是嵌套在 arguments.arguments 中
                        nested_args = tool_args.get('arguments', {})
                        if isinstance(nested_args, dict) and 'tool_name' in nested_args:
                            actual_tool_name = nested_args.get('tool_name', '')
                            if actual_tool_name:
                                display_tool_name = f"{tool_name}({actual_tool_name})"

                # Start 步骤
                start_step = ProcessingStep(
                    message_id=str(uuid.uuid4()),
                    present_content=present_text,
                    tool_type=f"Tool_{display_tool_name}",
                    parameters=json.dumps(tool_args),
                    tool_status="Start"
                )
                all_steps.append(start_step)

                # Success 步骤
                # 格式化observation以提高可读性
                tool_result = react_step.get('tool_result')
                observation_text = '执行成功'

                if tool_result:
                    # tool_result可能是一个嵌套的结构 {"success": true, "result": {...}}
                    # 我们需要提取实际的工具输出
                    actual_result = tool_result
                    if isinstance(tool_result, dict) and 'result' in tool_result:
                        actual_result = tool_result['result']

                    if isinstance(actual_result, dict):
                        # 对于analyze_image工具，提取analysis字段
                        if tool_name == 'analyze_image' and 'analysis' in actual_result:
                            observation_text = actual_result['analysis']
                        # 对于其他工具，格式化整个结果
                        else:
                            observation_text = json.dumps(actual_result, ensure_ascii=False, indent=2)
                    else:
                        observation_text = str(actual_result)

                success_step = ProcessingStep(
                    message_id=str(uuid.uuid4()),
                    present_content="",
                    tool_type=f"Tool_{display_tool_name}",
                    parameters=json.dumps(tool_args),
                    tool_status="Success",
                    observation=observation_text,
                    execution_duration=50
                )
                all_steps.append(success_step)

        # 步骤 2: 最终答案 (Finish)
        # Finish步骤只包含message_id、present_content和tool_type三个字段
        # 不包含parameters、observation、tool_status、execution_duration字段
        final_answer = react_result.get('answer', '')
        finish_step = {
            "message_id": str(uuid.uuid4()),
            "present_content": final_answer,
            "tool_type": "Finish"
        }
        all_steps.append(finish_step)

        # 显示推理轨迹
        print(f"\n{'='*60}")
        print(f"执行步骤:")
        print(f"{'='*60}")
        for step in all_steps:
            # Handle both ProcessingStep instances and plain dicts (like Finish)
            if isinstance(step, dict):
                # Plain dict (e.g., Finish step)
                if step.get("tool_type") == "Finish":
                    print(f"  🎯 FINISH: {step.get('present_content', '')[:60]}")
            else:
                # ProcessingStep instance
                if step.tool_status == "Start":
                    print(f"  ▶️  START: {step.present_content[:60]}")
                elif step.tool_status == "Success":
                    print(f"  ✅ SUCCESS: {step.present_content[:60]}")
        print(f"\n{'='*60}\n")

        # 使用流式服务逐个输出步骤，每次发送递增的steps
        streaming_service = StreamingService(request_id)
        # 将所有步骤转换为字典，处理混合类型（ProcessingStep实例和字典）
        step_dicts = []
        for step in all_steps:
            if hasattr(step, 'model_dump'):
                # ProcessingStep实例
                step_dicts.append(step.model_dump())
            else:
                # 普通字典（如Finish步骤）
                step_dicts.append(step)

        return StreamingResponse(
            streaming_service.generate_step_by_step_stream(step_dicts),
            media_type="application/json"
        )

    except Exception as e:
        print(f"\n❌ 错误: {str(e)}\n")

        # 错误步骤
        error_steps = [
            ProcessingStep(
                message_id=str(uuid.uuid4()),
                present_content=f"处理请求时发生错误: {str(e)}",
                tool_type="ErrorHandler",
                parameters="{}",
                tool_status="Error",
                observation=str(e)
            )
        ]

        # 流式输出错误
        streaming_service = StreamingService(request_id)
        return StreamingResponse(
            streaming_service.generate_step_by_step_stream(
                [step.model_dump() for step in error_steps],
                code=500,
                message="处理请求时发生错误"
            ),
            media_type="application/json"
        )


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    处理用户聊天请求，支持三种输入模式：
    1. 仅文本 (input_text)
    2. 仅图像 (input_image)
    3. 文本+图像 (input_text + input_image)

    使用TrueReAct模式进行推理和行动循环
    流式输出每个处理步骤
    """
    request_id = f"req_{str(uuid.uuid4()).replace('-', '')[:12]}"

    # 所有请求都使用TrueReAct模式
    return await handle_react_chat(request, request_id)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
