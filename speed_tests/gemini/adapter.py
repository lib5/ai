#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini模型适配器
实现基于Gemini-3-Flash的API调用
"""

import aiohttp
import json
from typing import Dict, List
from speed_tests.base_tester import BaseTester


class GeminiTester(BaseTester):
    """Gemini-3-Flash模型测试器"""

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

    async def chat_completion(self, messages: List[Dict]) -> Dict:
        """发送聊天请求"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
            "extra_body": {
                "reasoning": {
                    "max_tokens": 1
                }
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

                return await resp.json()

    def extract_content(self, response: Dict) -> str:
        """从Gemini响应中提取内容"""
        try:
            if 'choices' in response and response['choices']:
                return response['choices'][0]['message']['content']
            else:
                self.logger.warning(f"Gemini响应格式异常: {response}")
                return str(response)
        except (KeyError, IndexError) as e:
            raise ValueError(f"无法从Gemini响应中提取内容: {e}")

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

        # 转换消息格式为Gemini API兼容格式
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
                        # Gemini API图片格式
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
