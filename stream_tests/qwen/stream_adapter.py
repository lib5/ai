#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen模型流式适配器
实现Qwen模型的流式API调用和TTFT测试
"""

import aiohttp
import json
from typing import Dict, List, AsyncGenerator
from stream_tests.base_stream_tester import BaseStreamTester


class QwenStreamTester(BaseStreamTester):
    """阿里巴巴Qwen模型流式测试器"""

    def __init__(self, api_key: str, model: str = "qwen3-vl-plus", **kwargs):
        base_url = kwargs.pop('base_url', "https://dashscope.aliyuncs.com/compatible-mode/v1")
        headers = kwargs.pop('headers', {})
        headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

        super().__init__(
            model_name=f"Alibaba-Qwen-{model}",
            api_key=api_key,
            base_url=base_url,
            headers=headers,
            model=model,
            **kwargs
        )

    def get_api_url(self) -> str:
        """返回Qwen API端点"""
        return f"{self.base_url}/chat/completions"

    async def chat_completion_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """发送流式聊天请求"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
            "stream": True,  # 启用流式输出
            "top_p": 0.8,
            "repetition_penalty": 1.1
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
                    self.logger.error(f"Qwen API错误 {resp.status}: {error_text}")
                    raise Exception(f"Qwen API错误 {resp.status}: {error_text}")

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

    def parse_complete_prompt(self, complete_prompt_str: str) -> List[Dict]:
        """解析complete_prompt为消息列表"""
        if isinstance(complete_prompt_str, list):
            messages = complete_prompt_str
        else:
            messages = json.loads(complete_prompt_str)

        # 转换消息格式为Qwen API兼容格式
        converted_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if isinstance(content, list):
                new_content = []
                for item in content:
                    item_type = item.get('type', '')
                    if item_type == 'input_text' or item_type == 'text':
                        new_content.append({
                            "type": "text",  # Qwen期望'text'而不是'input_text'
                            "text": item.get('text', '')
                        })
                    elif item_type == 'input_image' or item_type == 'image_url':
                        # Qwen API图片格式
                        image_url = item.get('image_url', '')
                        if isinstance(image_url, dict):
                            image_url = image_url.get('url', '')
                        new_content.append({
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        })

                if new_content:
                    converted_messages.append({"role": role, "content": new_content})
            else:
                converted_messages.append({"role": role, "content": content})

        return converted_messages
