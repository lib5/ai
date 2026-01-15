#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流式测试基类模块
专门用于测试模型流式返回的首token速度 (TTFT)
"""

import json
import time
import asyncio
import aiohttp
import statistics
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
import logging


@dataclass
class StreamTestResult:
    """流式测试结果数据类"""

    model_name: str
    prompt_id: int
    prompt_type: str

    # 核心性能指标
    ttft_ms: float  # 首token时间 (Time To First Token)
    total_response_time_ms: float  # 总响应时间
    total_tokens: int  # 总token数
    tokens_per_second: float  # token生成速度

    # 详细时间统计
    request_sent_time: str  # 请求发送时间
    first_token_time: str  # 首token接收时间
    last_token_time: str  # 最后一个token接收时间

    success: bool
    error_message: Optional[str] = None

    # 流式数据
    stream_chunks: Optional[List[Dict]] = None  # 流式数据块
    raw_response: Optional[Dict] = None


class BaseStreamTester(ABC):
    """
    流式测试器抽象基类

    专门用于测试模型的流式响应性能，特别是首token速度
    """

    def __init__(self, model_name: str, api_key: str, **kwargs):
        """
        初始化测试器

        Args:
            model_name: 模型名称
            api_key: API密钥
            **kwargs: 其他配置参数
        """
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = kwargs.get('base_url', '')
        self.headers = kwargs.get('headers', {})
        self.model = kwargs.get('model', model_name)
        self.timeout = kwargs.get('timeout', 60)
        self.results: List[StreamTestResult] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def chat_completion_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """
        发送流式聊天请求并返回数据流

        Args:
            messages: 消息列表

        Yields:
            流式数据块 (SSE格式或JSON格式)
        """
        pass

    @abstractmethod
    def extract_content_from_chunk(self, chunk: str) -> str:
        """
        从流式数据块中提取文本内容

        Args:
            chunk: 流式数据块

        Returns:
            提取的文本内容
        """
        pass

    def get_api_url(self) -> str:
        """
        获取API端点URL

        子类必须重写此方法

        Returns:
            API端点URL
        """
        raise NotImplementedError("子类必须实现 get_api_url 方法")

    def parse_complete_prompt(self, complete_prompt_str: str) -> List[Dict]:
        """
        解析complete_prompt字符串为消息列表

        Args:
            complete_prompt_str: JSON字符串格式的prompt

        Returns:
            解析后的消息列表
        """
        try:
            # 如果已经是list，直接返回
            if isinstance(complete_prompt_str, list):
                return complete_prompt_str
            # 如果是字符串，解析JSON
            messages = json.loads(complete_prompt_str)
            return messages
        except Exception as e:
            self.logger.warning(f"解析prompt失败: {e}，使用默认消息")
            return [{"role": "user", "content": str(complete_prompt_str)[:100]}]

    async def test_single_prompt_stream(self, prompt: Dict) -> StreamTestResult:
        """
        测试单个prompt的流式响应

        Args:
            prompt: prompt数据

        Returns:
            流式测试结果
        """
        prompt_id = prompt.get('id', 0)
        prompt_type = prompt.get('type', 'text')

        try:
            # 解析消息
            messages = self.parse_complete_prompt(prompt['complete_prompt'])

            # 记录请求发送时间
            request_sent_time = datetime.now()
            request_sent_iso = request_sent_time.isoformat()

            first_token_received = False
            first_token_time = None
            last_token_time = None
            total_content = ""
            stream_chunks = []

            # 开始流式请求
            async for chunk in self.chat_completion_stream(messages):
                chunk_time = datetime.now()

                # 提取内容
                content = self.extract_content_from_chunk(chunk)
                if content:
                    # 记录首token时间（只有当content不为空且不是第一次记录时）
                    if not first_token_received:
                        first_token_time = chunk_time
                        first_token_received = True

                    # 如果content很长，可能不是真正的"首字符"
                    # 尝试进一步细分为更小的块
                    if len(content) > 100 and not hasattr(self, '_detailed_timing'):
                        self.logger.info(f"检测到大内容chunk: {len(content)} 字符")
                        self.logger.info(f"内容预览: {content[:200]}...")

                    total_content += content
                    last_token_time = chunk_time

                # 保存流式块信息
                stream_chunks.append({
                    "timestamp": chunk_time.isoformat(),
                    "content": content,
                    "chunk": chunk
                })

            # 计算性能指标
            if first_token_time and request_sent_time:
                ttft_ms = (first_token_time - request_sent_time).total_seconds() * 1000
            else:
                ttft_ms = 0

            if last_token_time and request_sent_time:
                total_response_time_ms = (last_token_time - request_sent_time).total_seconds() * 1000
            else:
                total_response_time_ms = 0

            total_tokens = len(total_content.split())
            tokens_per_second = (total_tokens / total_response_time_ms * 1000) if total_response_time_ms > 0 else 0

            return StreamTestResult(
                model_name=self.model_name,
                prompt_id=prompt_id,
                prompt_type=prompt_type,
                ttft_ms=ttft_ms,
                total_response_time_ms=total_response_time_ms,
                total_tokens=total_tokens,
                tokens_per_second=tokens_per_second,
                request_sent_time=request_sent_iso,
                first_token_time=first_token_time.isoformat() if first_token_time else None,
                last_token_time=last_token_time.isoformat() if last_token_time else None,
                success=True,
                stream_chunks=stream_chunks
            )

        except Exception as e:
            self.logger.error(f"流式测试失败 (ID: {prompt_id}): {e}")

            return StreamTestResult(
                model_name=self.model_name,
                prompt_id=prompt_id,
                prompt_type=prompt_type,
                ttft_ms=0,
                total_response_time_ms=0,
                total_tokens=0,
                tokens_per_second=0,
                request_sent_time=datetime.now().isoformat(),
                first_token_time=None,
                last_token_time=None,
                success=False,
                error_message=str(e)
            )

    async def run_stream_test(self,
                              prompts: List[Dict],
                              delay_between_requests: float = 2.0) -> List[StreamTestResult]:
        """
        运行流式模型测试

        Args:
            prompts: prompt列表
            delay_between_requests: 请求间隔（秒）

        Returns:
            流式测试结果列表
        """
        self.logger.info(f"🚀 开始流式测试模型: {self.model_name}")
        self.logger.info(f"📊 测试prompts数量: {len(prompts)}")

        # 为每个prompt添加时间戳
        for prompt in prompts:
            prompt['timestamp'] = datetime.now().isoformat()

        results = []
        for i, prompt in enumerate(prompts, 1):
            prompt_start_time = datetime.now()
            self.logger.info(f"[{prompt_start_time.strftime('%Y-%m-%d %H:%M:%S')}] [{i}/{len(prompts)}] 测试prompt ID: {prompt['id']}")

            result = await self.test_single_prompt_stream(prompt)
            results.append(result)
            self.results.append(result)

            # 延迟避免API限制
            if delay_between_requests > 0:
                await asyncio.sleep(delay_between_requests)

            # 显示结果
            if result.success:
                self.logger.info(
                    f"    ✅ TTFT: {result.ttft_ms:.0f}ms | "
                    f"总时间: {result.total_response_time_ms:.0f}ms | "
                    f"Token: {result.total_tokens} | "
                    f"速度: {result.tokens_per_second:.1f} tok/s"
                )
            else:
                error_msg = result.error_message[:50] + "..." if result.error_message and len(result.error_message) > 50 else result.error_message
                self.logger.error(f"    ❌ 错误: {error_msg}")

        return results

    def calculate_statistics(self) -> Dict[str, Any]:
        """
        计算流式测试统计指标

        Returns:
            统计结果字典
        """
        successful_results = [r for r in self.results if r.success]

        if not successful_results:
            return {"error": f"模型 {self.model_name} 没有成功的测试结果"}

        # 整体统计
        ttft_times = [r.ttft_ms for r in successful_results]
        response_times = [r.total_response_time_ms for r in successful_results]
        tokens_per_second = [r.tokens_per_second for r in successful_results]
        total_tokens = [r.total_tokens for r in successful_results]

        # 按类型分类统计
        text_results = [r for r in successful_results if r.prompt_type == 'text']
        image_results = [r for r in successful_results if r.prompt_type == 'image']

        stats = {
            "model_name": self.model_name,
            "total_tests": len(self.results),
            "successful_tests": len(successful_results),
            "failed_tests": len(self.results) - len(successful_results),

            # TTFT统计
            "ttft_ms": {
                "mean": round(statistics.mean(ttft_times), 2),
                "median": round(statistics.median(ttft_times), 2),
                "min": round(min(ttft_times), 2),
                "max": round(max(ttft_times), 2),
                "p80": round(np.percentile(ttft_times, 80), 2),
                "p90": round(np.percentile(ttft_times, 90), 2),
                "p99": round(np.percentile(ttft_times, 99), 2),
            },

            # 总响应时间统计
            "total_response_time_ms": {
                "mean": round(statistics.mean(response_times), 2),
                "median": round(statistics.median(response_times), 2),
                "min": round(min(response_times), 2),
                "max": round(max(response_times), 2),
                "p80": round(np.percentile(response_times, 80), 2),
                "p90": round(np.percentile(response_times, 90), 2),
                "p99": round(np.percentile(response_times, 99), 2),
            },

            # Token生成速度统计
            "tokens_per_second": {
                "mean": round(statistics.mean(tokens_per_second), 2),
                "median": round(statistics.median(tokens_per_second), 2),
                "min": round(min(tokens_per_second), 2),
                "max": round(max(tokens_per_second), 2),
                "p80": round(np.percentile(tokens_per_second, 80), 2),
                "p90": round(np.percentile(tokens_per_second, 90), 2),
                "p99": round(np.percentile(tokens_per_second, 99), 2),
            },

            # 总token数统计
            "total_tokens": {
                "mean": round(statistics.mean(total_tokens), 2),
                "median": round(statistics.median(total_tokens), 2),
                "min": min(total_tokens),
                "max": max(total_tokens),
            }
        }

        # 添加文本类型统计
        if text_results:
            text_ttft = [r.ttft_ms for r in text_results]
            text_response_time = [r.total_response_time_ms for r in text_results]
            text_tokens_per_second = [r.tokens_per_second for r in text_results]
            text_total_tokens = [r.total_tokens for r in text_results]

            stats["text_type"] = {
                "count": len(text_results),
                "ttft_ms": {
                    "mean": round(statistics.mean(text_ttft), 2),
                    "median": round(statistics.median(text_ttft), 2),
                    "min": round(min(text_ttft), 2),
                    "max": round(max(text_ttft), 2),
                },
                "total_response_time_ms": {
                    "mean": round(statistics.mean(text_response_time), 2),
                    "median": round(statistics.median(text_response_time), 2),
                    "min": round(min(text_response_time), 2),
                    "max": round(max(text_response_time), 2),
                },
                "tokens_per_second": {
                    "mean": round(statistics.mean(text_tokens_per_second), 2),
                    "median": round(statistics.median(text_tokens_per_second), 2),
                    "min": round(min(text_tokens_per_second), 2),
                    "max": round(max(text_tokens_per_second), 2),
                },
                "total_tokens": {
                    "mean": round(statistics.mean(text_total_tokens), 2),
                    "median": round(statistics.median(text_total_tokens), 2),
                    "min": min(text_total_tokens),
                    "max": max(text_total_tokens),
                }
            }

        # 添加图片类型统计
        if image_results:
            image_ttft = [r.ttft_ms for r in image_results]
            image_response_time = [r.total_response_time_ms for r in image_results]
            image_tokens_per_second = [r.tokens_per_second for r in image_results]
            image_total_tokens = [r.total_tokens for r in image_results]

            stats["image_type"] = {
                "count": len(image_results),
                "ttft_ms": {
                    "mean": round(statistics.mean(image_ttft), 2),
                    "median": round(statistics.median(image_ttft), 2),
                    "min": round(min(image_ttft), 2),
                    "max": round(max(image_ttft), 2),
                },
                "total_response_time_ms": {
                    "mean": round(statistics.mean(image_response_time), 2),
                    "median": round(statistics.median(image_response_time), 2),
                    "min": round(min(image_response_time), 2),
                    "max": round(max(image_response_time), 2),
                },
                "tokens_per_second": {
                    "mean": round(statistics.mean(image_tokens_per_second), 2),
                    "median": round(statistics.median(image_tokens_per_second), 2),
                    "min": round(min(image_tokens_per_second), 2),
                    "max": round(max(image_tokens_per_second), 2),
                },
                "total_tokens": {
                    "mean": round(statistics.mean(image_total_tokens), 2),
                    "median": round(statistics.median(image_total_tokens), 2),
                    "min": min(image_total_tokens),
                    "max": max(image_total_tokens),
                }
            }

        return stats

    def print_statistics(self):
        """
        打印流式测试统计结果
        """
        stats = self.calculate_statistics()

        if "error" in stats:
            print(f"\n❌ {stats['error']}")
            return

        print(f"\n📊 {stats['model_name']} 流式测试统计结果:")
        print(f"  总测试: {stats['total_tests']} | 成功: {stats['successful_tests']} | 失败: {stats['failed_tests']}")

        # TTFT统计
        ttft = stats['ttft_ms']
        print(f"\n⚡ 首Token时间 (TTFT) (ms):")
        print(f"  均值: {ttft['mean']} | 中位数: {ttft['median']} | 最小: {ttft['min']} | 最大: {ttft['max']}")
        print(f"  P80: {ttft['p80']} | P90: {ttft['p90']} | P99: {ttft['p99']}")

        # 总响应时间统计
        total_rt = stats['total_response_time_ms']
        print(f"\n⏱️ 总响应时间 (ms):")
        print(f"  均值: {total_rt['mean']} | 中位数: {total_rt['median']} | 最小: {total_rt['min']} | 最大: {total_rt['max']}")
        print(f"  P80: {total_rt['p80']} | P90: {total_rt['p90']} | P99: {total_rt['p99']}")

        # Token生成速度统计
        tps = stats['tokens_per_second']
        print(f"\n🚀 Token生成速度 (tokens/s):")
        print(f"  均值: {tps['mean']} | 中位数: {tps['median']} | 最小: {tps['min']} | 最大: {tps['max']}")
        print(f"  P80: {tps['p80']} | P90: {tps['p90']} | P99: {tps['p99']}")

        # 总token数统计
        tokens = stats['total_tokens']
        print(f"\n📝 输出Token数量:")
        print(f"  均值: {tokens['mean']} | 中位数: {tokens['median']} | 最小: {tokens['min']} | 最大: {tokens['max']}")

        # 文本类型统计
        if "text_type" in stats:
            text_stats = stats["text_type"]
            print(f"\n📝 文本类型 (无图片) - {text_stats['count']}个测试:")
            ttft = text_stats['ttft_ms']
            print(f"  TTFT: 均值{ttft['mean']}ms | 中位数{ttft['median']}ms | 最小{ttft['min']}ms | 最大{ttft['max']}ms")
            rt = text_stats['total_response_time_ms']
            print(f"  响应时间: 均值{rt['mean']}ms | 中位数{rt['median']}ms | 最小{rt['min']}ms | 最大{rt['max']}ms")
            tps = text_stats['tokens_per_second']
            print(f"  Token速度: 均值{tps['mean']} tok/s | 中位数{tps['median']} tok/s | 最小{tps['min']} tok/s | 最大{tps['max']} tok/s")

        # 图片类型统计
        if "image_type" in stats:
            image_stats = stats["image_type"]
            print(f"\n📸 图片类型 (有图片) - {image_stats['count']}个测试:")
            ttft = image_stats['ttft_ms']
            print(f"  TTFT: 均值{ttft['mean']}ms | 中位数{ttft['median']}ms | 最小{ttft['min']}ms | 最大{ttft['max']}ms")
            rt = image_stats['total_response_time_ms']
            print(f"  响应时间: 均值{rt['mean']}ms | 中位数{rt['median']}ms | 最小{rt['min']}ms | 最大{rt['max']}ms")
            tps = image_stats['tokens_per_second']
            print(f"  Token速度: 均值{tps['mean']} tok/s | 中位数{tps['median']} tok/s | 最小{tps['min']} tok/s | 最大{tps['max']} tok/s")

    def save_results(self, filename: str):
        """
        保存流式测试结果到文件

        Args:
            filename: 输出文件名
        """
        # 保存详细结果
        detailed_results = [asdict(r) for r in self.results]

        output = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "model_name": self.model_name,
                "test_type": "stream_ttft_test",
                "total_results": len(self.results),
                "successful_results": len([r for r in self.results if r.success]),
                "failed_results": len([r for r in self.results if not r.success]),
            },
            "detailed_results": detailed_results
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        # 计算统计结果
        statistics = self.calculate_statistics()

        # 保存统计结果
        stats_output = {
            "test_info": output["test_info"],
            "statistics": statistics
        }

        stats_filename = filename.replace('.json', '_stats.json')
        with open(stats_filename, 'w', encoding='utf-8') as f:
            json.dump(stats_output, f, ensure_ascii=False, indent=2)

        print(f"\n💾 流式测试结果已保存:")
        print(f"  • 详细结果: {filename}")
        print(f"  • 统计结果: {stats_filename}")

        # 打印统计结果
        self.print_statistics()
