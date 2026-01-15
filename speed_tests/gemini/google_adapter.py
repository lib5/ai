#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google官方Gemini模型适配器
专门用于测试Google官方Gemini API的非流式输出速度

配置:
- API端点: generativelanguage.googleapis.com
- API密钥: AQ.Ab8RN6J9GWr-zLevwtQ-kjFdSlZRy2wIabqdn4sNbszpacBJ0A
- 模型: gemini-3-flash-preview
"""

import aiohttp
import json
from typing import Dict, List
from speed_tests.base_tester import BaseTester


class GoogleGeminiTester(BaseTester):
    """Google官方Gemini模型测试器"""

    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview", **kwargs):
        base_url = kwargs.pop('base_url', "https://generativelanguage.googleapis.com")
        headers = kwargs.pop('headers', {})
        headers.update({
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
        """返回Google官方Gemini API端点"""
        return f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    async def chat_completion(self, messages: List[Dict]) -> Dict:
        """发送非流式聊天请求"""
        # 解析消息，提取文本和图片内容
        user_content = []

        for message in messages:
            if message.get('role') == 'user' and isinstance(message.get('content'), list):
                for part in message['content']:
                    if part.get('type') == 'input_text' or part.get('type') == 'text':
                        user_content.append({
                            "type": "text",
                            "text": part.get('text', '')
                        })
                    elif part.get('type') == 'input_image' or part.get('type') == 'image_url':
                        # 处理图片
                        image_url = part.get('image_url', {})
                        if isinstance(image_url, dict):
                            url = image_url.get('url', '')
                        else:
                            url = image_url

                        if url.startswith('data:image/'):
                            # 提取base64数据和MIME类型
                            header, data = url.split(',', 1)
                            mime_type = header.split(':')[1].split(';')[0]
                            user_content.append({
                                "inline_data": {
                                    "mimeType": mime_type,
                                    "data": data
                                }
                            })
            elif message.get('role') == 'user' and isinstance(message.get('content'), str):
                user_content.append({
                    "type": "text",
                    "text": message.get('content', '')
                })

        # 构建payload（使用非流式配置）
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
                    self.logger.error(f"Google Gemini API错误 {resp.status}: {error_text}")
                    raise Exception(f"Google Gemini API错误 {resp.status}: {error_text}")

                return await resp.json()

    def extract_content(self, response: Dict) -> str:
        """从Google Gemini响应中提取内容"""
        try:
            if 'candidates' in response and response['candidates']:
                candidate = response['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts = candidate['content']['parts']
                    content = ''
                    for part in parts:
                        if 'text' in part:
                            content += part['text']
                    return content
            else:
                self.logger.warning(f"Google Gemini响应格式异常: {response}")
                return str(response)
        except (KeyError, IndexError) as e:
            raise ValueError(f"无法从Google Gemini响应中提取内容: {e}")

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

        # 转换消息格式为Google Gemini API兼容格式
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
                        image_url = item.get('image_url', {})
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
