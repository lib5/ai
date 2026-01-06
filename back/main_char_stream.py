#!/usr/bin/env python3
"""
真正的字符流式输出实现
修改 main.py 以支持真正的逐字符流式输出
"""
import asyncio
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# 模拟 ReAct 代理
class TrueReActAgent:
    async def run(self, query_text, image_urls, user_metadata):
        """模拟 ReAct 运行，返回流式输出"""
        # 第一步：开始查询
        yield {
            'type': 'start',
            'action': {
                'tool_name': 'schedules_search',
                'content': '正在为您查询...',
                'tool_args': {'query': query_text}
            }
        }
        await asyncio.sleep(0.5)

        # 第二步：工具结果
        yield {
            'type': 'result',
            'action': {
                'tool_name': 'schedules_search',
                'tool_result': {'data': '查询结果...'}
            }
        }
        await asyncio.sleep(0.3)

        # 第三步：最终答案（逐字符流式输出）
        final_answer = "亲爱的主人，这是您的查询结果。系统正在为您处理，请稍候。"
        yield {
            'type': 'final_answer',
            'answer': final_answer,
            'steps': [],
            'iterations': 1
        }

# 全局 ReAct 代理实例
true_react_agent = TrueReActAgent()

async def stream_with_character_output(request_id: str, query_text: str):
    """
    真正的逐字符流式输出
    """
    print(f"\n{'='*80}")
    print(f"开始处理请求: {request_id}")
    print(f"{'='*80}\n")

    # 1. 发送初始响应（JSON格式）
    initial_response = {
        "code": 200,
        "message": "成功",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "requestId": request_id,
        "data": {
            "steps": []
        }
    }
    yield json.dumps(initial_response, ensure_ascii=False, separators=(',', ':')) + '\n'
    print("✅ 发送初始响应\n")

    # 2. 运行 ReAct 并流式输出内容
    async for output in true_react_agent.run(query_text, None, None):
        output_type = output.get('type')

        if output_type == 'start':
            action = output.get('action', {})
            content = action.get('content', '')
            tool_name = action.get('tool_name', 'Unknown')

            print(f"🔄 步骤开始: {tool_name}")
            print(f"📝 内容: {content}\n")

            # 发送步骤开始事件
            step_response = {
                "code": 200,
                "message": "成功",
                "timestamp": None,
                "requestId": request_id,
                "data": {
                    "steps": [{
                        "message_id": str(uuid.uuid4()),
                        "present_content": content,
                        "tool_type": tool_name,
                        "tool_status": "Start"
                    }]
                }
            }
            yield json.dumps(step_response, ensure_ascii=False, separators=(',', ':')) + '\n'

            # 逐字符流式输出文本内容
            print(f"📤 流式输出文本: ", end='', flush=True)
            for char in content:
                yield char
                print(char, end='', flush=True)
                await asyncio.sleep(0.02)  # 20ms延迟
            print("\n✅ 文本输出完成\n")

        elif output_type == 'result':
            print(f"✅ 步骤完成\n")

            # 发送成功事件
            success_response = {
                "code": 200,
                "message": "成功",
                "timestamp": None,
                "requestId": request_id,
                "data": {
                    "steps": [{
                        "message_id": str(uuid.uuid4()),
                        "present_content": "",
                        "tool_type": "completed",
                        "tool_status": "Success"
                    }]
                }
            }
            yield json.dumps(success_response, ensure_ascii=False, separators=(',', ':')) + '\n'

        elif output_type == 'final_answer':
            answer = output.get('answer', '')
            print(f"🎯 最终答案 (长度: {len(answer)} 字符)")
            print(f"{'-'*80}")
            print(f"📤 开始流式输出最终答案:\n")

            # 发送最终答案开始事件
            final_start_response = {
                "code": 200,
                "message": "成功",
                "timestamp": None,
                "requestId": request_id,
                "data": {
                    "steps": [{
                        "message_id": str(uuid.uuid4()),
                        "present_content": "",
                        "tool_type": "Finish"
                    }]
                }
            }
            yield json.dumps(final_start_response, ensure_ascii=False, separators=(',', ':')) + '\n'

            # 逐字符流式输出最终答案
            for char in answer:
                yield char
                print(char, end='', flush=True)
                await asyncio.sleep(0.02)  # 20ms延迟
            print("\n")
            print(f"{'-'*80}")
            print(f"✅ 最终答案输出完成")
            print(f"{'='*80}\n")

            # 发送完成事件
            final_complete_response = {
                "code": 200,
                "message": "成功",
                "timestamp": None,
                "requestId": request_id,
                "data": {
                    "steps": [{
                        "message_id": str(uuid.uuid4()),
                        "present_content": answer,
                        "tool_type": "Finish"
                    }]
                }
            }
            yield json.dumps(final_complete_response, ensure_ascii=False, separators=(',', ':')) + '\n'

            break

# 测试端点
app = FastAPI()

@app.post("/api/chat/char-stream")
async def chat_char_stream_endpoint():
    """字符流式输出端点"""
    request_id = f"req_{str(uuid.uuid4())[:12]}"
    query_text = "你好，请介绍一下自己"

    return StreamingResponse(
        stream_with_character_output(request_id, query_text),
        media_type="application/json"
    )

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*80)
    print("🚀 启动字符流式输出测试服务器")
    print("端点: http://localhost:8000/api/chat/char-stream")
    print("="*80 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8001)