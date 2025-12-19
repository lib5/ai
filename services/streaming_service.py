import json
import uuid
from typing import Dict, Any, AsyncGenerator
import asyncio
from datetime import datetime

class StreamingService:
    """流式输出服务"""

    def __init__(self, request_id: str):
        self.request_id = request_id

    async def generate_stream(self, response_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        生成流式 JSON 响应

        Args:
            response_data: 响应数据

        Yields:
            JSON 字符串片段
        """
        # 将响应数据转换为 JSON 字符串
        response_json = json.dumps(response_data, ensure_ascii=False, separators=(',', ':'))

        # 模拟流式输出，每次发送一部分数据
        chunk_size = 100  # 每次发送 100 个字符

        # 发送开始标记
        start_marker = {
            "event": "start",
            "requestId": self.request_id,
            "timestamp": response_data.get("timestamp", "")
        }
        yield f"data: {json.dumps(start_marker, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.01)  # 短暂延迟

        # 分块发送数据
        for i in range(0, len(response_json), chunk_size):
            chunk = response_json[i:i + chunk_size]

            chunk_event = {
                "event": "chunk",
                "requestId": self.request_id,
                "data": chunk,
                "sequence": i // chunk_size
            }
            yield f"data: {json.dumps(chunk_event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)  # 短暂延迟

        # 发送结束标记
        end_marker = {
            "event": "end",
            "requestId": self.request_id,
            "totalLength": len(response_json)
        }
        yield f"data: {json.dumps(end_marker, ensure_ascii=False)}\n\n"

    async def generate_stream_with_steps(self, steps_data: list) -> AsyncGenerator[str, None]:
        """
        按步骤生成流式输出

        Args:
            steps_data: 步骤数据列表

        Yields:
            JSON 字符串片段
        """
        for i, step in enumerate(steps_data):
            # 发送每个步骤
            step_event = {
                "event": "step",
                "requestId": self.request_id,
                "stepIndex": i,
                "stepData": step
            }
            yield f"data: {json.dumps(step_event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)  # 步骤间延迟

        # 发送完成事件
        completion_event = {
            "event": "complete",
            "requestId": self.request_id,
            "totalSteps": len(steps_data)
        }
        yield f"data: {json.dumps(completion_event, ensure_ascii=False)}\n\n"

    async def generate_step_by_step_stream(self, steps_data: list, code: int = 200, message: str = "成功") -> AsyncGenerator[str, None]:
        """
        逐个输出步骤，每次输出一个完整的响应格式，包含递增的steps

        Args:
            steps_data: 步骤数据列表
            code: 响应代码
            message: 响应消息

        Yields:
            完整的 JSON 响应字符串，每次包含累积的steps
        """
        accumulated_steps = []  # 累积所有步骤

        for i, step in enumerate(steps_data):
            # 将当前步骤添加到累积列表中
            if isinstance(step, list):
                accumulated_steps.extend(step)
            else:
                accumulated_steps.append(step)

            # 创建完整的响应格式，包含所有累积的步骤
            response_data = {
                "code": code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat() + "Z" if i == 0 else None,
                "requestId": self.request_id,
                "data": {
                    "steps": accumulated_steps
                }
            }

            # 移除空值
            response_data = {k: v for k, v in response_data.items() if v is not None}

            # 输出完整的响应
            yield json.dumps(response_data, ensure_ascii=False, separators=(',', ':')) + '\n'
            await asyncio.sleep(0.1)  # 步骤间延迟