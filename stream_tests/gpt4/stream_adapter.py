#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT-4模型流式适配器
实现GPT-4模型的流式API调用和TTFT测试
"""

import aiohttp
import json
from typing import Dict, List, AsyncGenerator
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from stream_tests.base_stream_tester import BaseStreamTester
from services.azure_openai_service import AzureOpenAIService


class GPT4StreamTester(BaseStreamTester):
    """Azure GPT-4模型流式测试器"""

    def __init__(self, api_key: str, deployment_name: str = "gpt-4.1", **kwargs):
        endpoint = kwargs.pop('endpoint', "")
        api_version = kwargs.pop('api_version', "2024-02-15-preview")
        timeout = kwargs.pop('timeout', 30)

        super().__init__(
            model_name=f"Azure-GPT-{deployment_name}",
            api_key=api_key,
            endpoint=endpoint,
            api_version=api_version,
            deployment_name=deployment_name,
            timeout=timeout,
            **kwargs
        )

        # 初始化AzureOpenAI服务
        self.azure_service = AzureOpenAIService(
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            deployment_name=deployment_name
        )

    def get_api_url(self) -> str:
        """返回GPT-4 API端点"""
        return f"{self.azure_service.base_url}/chat/completions?api-version={self.azure_service.api_version}"

    async def chat_completion_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """发送流式聊天请求"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        payload = {
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
            "stream": True  # 启用流式输出
        }

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }

        url = f"{self.azure_service.base_url}/chat/completions?api-version={self.azure_service.api_version}"

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    self.logger.error(f"GPT-4 API错误 {resp.status}: {error_text}")
                    raise Exception(f"GPT-4 API错误 {resp.status}: {error_text}")

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

        # 转换消息格式为GPT-4 API兼容格式
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
                            "type": "text",  # GPT-4期望'text'而不是'input_text'
                            "text": item.get('text', '')
                        })
                    elif item_type == 'input_image' or item_type == 'image_url':
                        # GPT-4 API图片格式
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
