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
            "stream": stream,
            "extra_body": {
                "reasoning": {
                    "max_tokens": 1
                }
            }
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
            "stream": True,
            "extra_body": {
                "reasoning": {
                    "max_tokens": 1
                }
            }
        }

        async with aiohttp.ClientSession() as session:
            try:
                # 记录请求开始时间
                request_start_time = asyncio.get_event_loop().time()
                first_chunk_time = None
                chunk_count = 0

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

                                    # 记录第一个chunk的时间
                                    if first_chunk_time is None:
                                        first_chunk_time = asyncio.get_event_loop().time()
                                        time_to_first_output = (first_chunk_time - request_start_time) * 1000
                                        print(f"\n{'='*80}")
                                        print(f"⏱️  Gemini API 时间统计")
                                        print(f"📥 请求 Gemini → 📤 首个输出: {time_to_first_output:.2f}ms")
                                        print(f"{'='*80}\n")

                                    chunk_count += 1
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


class DoubaoService:
    """豆包服务类 - 字节跳动 AI 助手"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://ark.cn-beijing.volces.com",
        model: str = "doubao-lite-4k",
        timeout: int = 30
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        调用豆包 Chat Completion API

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
            "stream": stream,
            "reasoning_effort": "minimal"
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"豆包 API 错误: {response.status} - {error_text}")

            except aiohttp.ClientError as e:
                raise Exception(f"请求豆包 API 时发生网络错误: {str(e)}")

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用豆包 Chat Completion API

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
            "stream": True,
            "reasoning_effort": "minimal"
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                # 记录请求开始时间
                request_start_time = asyncio.get_event_loop().time()
                first_chunk_time = None
                chunk_count = 0

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

                                    # 记录第一个chunk的时间
                                    if first_chunk_time is None:
                                        first_chunk_time = asyncio.get_event_loop().time()
                                        time_to_first_output = (first_chunk_time - request_start_time) * 1000
                                        print(f"\n{'='*80}")
                                        print(f"⏱️ 豆包 API 时间统计")
                                        print(f"📥 请求豆包 → 📤 首个输出: {time_to_first_output:.2f}ms")
                                        print(f"{'='*80}\n")

                                    chunk_count += 1
                                    yield chunk
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"豆包 API 错误: {response.status} - {error_text}")

            except aiohttp.ClientError as e:
                raise Exception(f"请求豆包 API 时发生网络错误: {str(e)}")