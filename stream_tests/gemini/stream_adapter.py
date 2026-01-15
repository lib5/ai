#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini模型流式适配器
实现Gemini模型的流式API调用和TTFT测试
"""

import aiohttp
import json
import asyncio
from typing import Dict, List, AsyncGenerator
from stream_tests.base_stream_tester import BaseStreamTester


class GeminiStreamTester(BaseStreamTester):
    """Google Gemini模型流式测试器"""

    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview", **kwargs):
        base_url = kwargs.pop('base_url', "https://llm.onerouter.pro/v1")
        headers = kwargs.pop('headers', {})
        headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

        super().__init__(
            model_name=f"Google-Gemini-{model}",
            api_key=api_key,
            base_url=base_url,
            headers=headers,
            model=model,
            **kwargs
        )

    def get_api_url(self) -> str:
        """返回Gemini API端点"""
        return f"{self.base_url}/chat/completions"

    async def chat_completion_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """发送流式聊天请求"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
            "stream": True,  # 启用流式输出
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

                # 处理SSE流
                async for line in resp.content:
                    if line:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break
                            yield data

    def extract_content_from_chunk(self, chunk: str) -> str:
        """从流式数据块中提取内容"""
        try:
            # 解析SSE JSON数据
            data = json.loads(chunk)
            if 'choices' in data and data['choices']:
                delta = data['choices'][0].get('delta', {})
                return delta.get('content', '')
            return ''
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            self.logger.warning(f"解析流式块失败: {e}, chunk: {chunk[:100]}")
            return ''
