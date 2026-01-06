import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional, AsyncGenerator

class OpenAIService:
    """OpenAI 服务类"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://llm.onerouter.pro/v1",
        model: str = "gemini-3-flash-preview"
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        调用 OpenAI Chat Completion API

        Args:
            messages: 消息列表
            max_tokens: 最大令牌数
            temperature: 温度参数
            stream: 是否流式返回

        Returns:
            API 响应
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API 错误: {response.status} - {error_text}")

            except aiohttp.ClientError as e:
                raise Exception(f"请求 OpenAI API 时发生网络错误: {str(e)}")

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 OpenAI Chat Completion API

        Args:
            messages: 消息列表
            max_tokens: 最大令牌数
            temperature: 温度参数

        Yields:
            流式响应片段
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]  # 移除 'data: ' 前缀
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk = json.loads(data)
                                    yield chunk
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API 错误: {response.status} - {error_text}")

            except aiohttp.ClientError as e:
                raise Exception(f"请求 OpenAI API 时发生网络错误: {str(e)}")


class AzureOpenAIService:
    """Azure OpenAI 服务类"""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        api_version: str = "2024-02-15-preview",
        deployment_name: str = "gpt-4.1"
    ):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.api_version = api_version
        self.deployment_name = deployment_name
        self.base_url = f"{self.endpoint}/openai/deployments/{self.deployment_name}"

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        调用 Azure OpenAI Chat Completion API

        Args:
            messages: 消息列表
            max_tokens: 最大令牌数
            temperature: 温度参数
            stream: 是否流式返回

        Returns:
            API 响应
        """
        url = f"{self.base_url}/chat/completions?api-version={self.api_version}"

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"Azure OpenAI API 错误: {response.status} - {error_text}")

            except aiohttp.ClientError as e:
                raise Exception(f"请求 Azure OpenAI API 时发生网络错误: {str(e)}")

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 Azure OpenAI Chat Completion API

        Args:
            messages: 消息列表
            max_tokens: 最大令牌数
            temperature: 温度参数

        Yields:
            流式响应片段
        """
        url = f"{self.base_url}/chat/completions?api-version={self.api_version}"

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }

        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]  # 移除 'data: ' 前缀
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk = json.loads(data)
                                    yield chunk
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"Azure OpenAI API 错误: {response.status} - {error_text}")

            except aiohttp.ClientError as e:
                raise Exception(f"请求 Azure OpenAI API 时发生网络错误: {str(e)}")