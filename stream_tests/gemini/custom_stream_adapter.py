#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义Gemini模型流式适配器
使用指定的API端点和模型进行测试

配置:
- API端点: wsa.147ai.cn
- API密钥: sk-i1OxltYB6g1sc4WFeLeqg088af7tDhiWFBrqbyvlDB30hmKF
- 模型: gemini-3-flash-preview-low
"""

import aiohttp
import json
import asyncio
from typing import Dict, List, AsyncGenerator
from stream_tests.base_stream_tester import BaseStreamTester


class CustomGeminiStreamTester(BaseStreamTester):
    """自定义Gemini模型流式测试器"""

    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview-low", **kwargs):
        base_url = kwargs.pop('base_url', "https://wsa.147ai.cn")
        headers = kwargs.pop('headers', {})
        headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

        super().__init__(
            model_name=f"Custom-Gemini-{model}",
            api_key=api_key,
            base_url=base_url,
            headers=headers,
            model=model,
            **kwargs
        )

    def get_api_url(self) -> str:
        """返回Gemini API端点"""
        return f"{self.base_url}/v1beta/models/{self.model}:generateContent"

    async def chat_completion_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """发送流式聊天请求"""

        # 解析消息，提取文本和图片内容
        user_content = []
        has_image = False

        for message in messages:
            if message.get('role') == 'user' and isinstance(message.get('content'), list):
                for part in message['content']:
                    if part.get('type') == 'input_text':
                        user_content.append({
                            "type": "text",
                            "text": part.get('text', '')
                        })
                    elif part.get('type') == 'input_image':
                        # 处理图片
                        image_url = part.get('image_url', '')
                        if image_url.startswith('data:image/'):
                            # 提取base64数据和MIME类型
                            header, data = image_url.split(',', 1)
                            mime_type = header.split(':')[1].split(';')[0]
                            user_content.append({
                                "type": "text",
                                "text": part.get('text', '')
                            })
                            user_content.append({
                                "inline_data": {
                                    "mimeType": mime_type,
                                    "data": data
                                }
                            })
                            has_image = True
                        else:
                            # 如果不是base64格式，假设是文本
                            user_content.append({
                                "type": "text",
                                "text": part.get('text', '')
                            })
            elif message.get('role') == 'user' and isinstance(message.get('content'), str):
                user_content.append({
                    "type": "text",
                    "text": message.get('content', '')
                })

        # 构建payload
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": user_content
                }
            ],
            "generationConfig": {
                "thinkingConfig": {
                    "thinkingBudget": 1
                },
                "stream": "true"
            }
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self.get_api_url(),
                json=payload,
                headers=self.headers
            ) as resp:

                if resp.status != 200:
                    error_text = await resp.text()
                    self.logger.error(f"Gemini API错误 {resp.status}: {error_text}")
                    raise Exception(f"Gemini API错误 {resp.status}: {error_text}")

                # 检查Content-Type判断是否是流式响应
                content_type = resp.headers.get('Content-Type', '')

                if 'text/event-stream' in content_type or 'stream' in content_type.lower():
                    # 处理SSE流
                    async for line in resp.content:
                        if line:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    break
                                yield data
                else:
                    # 接收完整JSON响应并模拟流式输出
                    response_data = await resp.json()
                    response_text = self.extract_content_from_chunk(json.dumps(response_data))

                    # 模拟流式输出：将响应文本按字符分块输出
                    if response_text:
                        # 将文本分割成小块，每块约10个字符
                        chunk_size = 10
                        for i in range(0, len(response_text), chunk_size):
                            chunk = response_text[i:i + chunk_size]
                            # 包装成SSE格式
                            sse_data = {
                                "candidates": [{
                                    "content": {
                                        "role": "model",
                                        "parts": [{"text": chunk}]
                                    }
                                }]
                            }
                            yield json.dumps(sse_data)
                            # 添加小延迟模拟流式输出
                            await asyncio.sleep(0.01)

                    # 发送结束标志
                    yield "data: [DONE]"

    def extract_content_from_chunk(self, chunk: str) -> str:
        """从流式数据块中提取内容"""
        try:
            # 解析SSE JSON数据
            data = json.loads(chunk)
            if 'candidates' in data and data['candidates']:
                candidate = data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    content = ''
                    for part in parts:
                        if 'text' in part:
                            content += part['text']
                    return content
            return ''
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            self.logger.warning(f"解析流式块失败: {e}, chunk: {chunk[:100]}")
            return ''
