#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT4.1模型适配器
实现基于Azure OpenAI GPT-4.1的API调用
"""

import aiohttp
import json
from typing import Dict, List
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from speed_tests.base_tester import BaseTester
from services.azure_openai_service import AzureOpenAIService


class GPT4Tester(BaseTester):
    """GPT4.1模型测试器"""

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
        """返回GPT4.1 API端点"""
        return f"{self.azure_service.base_url}/chat/completions?api-version={self.azure_service.api_version}"

    async def chat_completion(self, messages: List[Dict]) -> Dict:
        """发送聊天请求"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        payload = {
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000
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
                    self.logger.error(f"GPT4.1 API错误 {resp.status}: {error_text}")
                    raise Exception(f"GPT4.1 API错误 {resp.status}: {error_text}")

                return await resp.json()

    def extract_content(self, response: Dict) -> str:
        """从GPT4.1响应中提取内容"""
        try:
            if 'choices' in response and response['choices']:
                return response['choices'][0]['message']['content']
            else:
                self.logger.warning(f"GPT4.1响应格式异常: {response}")
                return str(response)
        except (KeyError, IndexError) as e:
            raise ValueError(f"无法从GPT4.1响应中提取内容: {e}")

    def parse_complete_prompt(self, complete_prompt):
        """
        解析complete_prompt为消息列表
        处理两种格式：JSON字符串 或 直接的list
        """
        # 如果已经是list，直接使用
        if isinstance(complete_prompt, list):
            messages = complete_prompt
        else:
            # 如果是字符串，解析JSON
            messages = json.loads(complete_prompt)

        # 转换消息格式为GPT4.1 API兼容格式
        converted_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if isinstance(content, list):
                # 处理复合内容（文本+图片）
                new_content = []
                for item in content:
                    item_type = item.get('type', '')
                    if item_type == 'input_text' or item_type == 'text':
                        new_content.append({
                            "type": "text",
                            "text": item.get('text', '')
                        })
                    elif item_type == 'input_image' or item_type == 'image_url':
                        # GPT4.1 API图片格式
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
                # 普通文本内容
                converted_messages.append({"role": role, "content": content})

        return converted_messages
