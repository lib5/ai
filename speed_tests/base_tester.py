#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试基类模块
定义了所有模型测试器的基本接口和通用功能
"""

import json
import time
import asyncio
import aiohttp
import statistics
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging


@dataclass
class TestResult:
    """测试结果数据类"""

    model_name: str
    prompt_id: int
    prompt_type: str
    response_time_ms: float
    input_tokens: int
    output_tokens: int
    tokens_per_second: float
    success: bool
    error_message: Optional[str] = None
    timestamp: str = None
    raw_response: Optional[Dict] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class BaseTester(ABC):
    """
    测试器抽象基类

    定义了所有模型测试器必须实现的接口和通用功能
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
        self.timeout = kwargs.get('timeout', 30)
        self.results: List[TestResult] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def chat_completion(self, messages: List[Dict]) -> Dict:
        """
        发送聊天请求并返回结果

        Args:
            messages: 消息列表

        Returns:
            解析后的响应字典
        """
        pass

    @abstractmethod
    def extract_content(self, response: Dict) -> str:
        """
        从API响应中提取文本内容

        Args:
            response: API返回的原始响应

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

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量

        Args:
            text: 输入文本

        Returns:
            估算的token数量
        """
        if not text:
            return 0

        # 简单估算：中文字符约2字符/Token，英文字符约4字符/Token
        chinese_chars = sum(1 for c in text if ord(c) > 127)
        english_chars = len(text) - chinese_chars

        return int(chinese_chars / 2 + english_chars / 4)

    def parse_complete_prompt(self, complete_prompt_str: str) -> List[Dict]:
        """
        解析complete_prompt字符串为消息列表

        Args:
            complete_prompt_str: JSON字符串格式的prompt

        Returns:
            解析后的消息列表
        """
        try:
            messages = json.loads(complete_prompt_str)

            # 提取最后一条用户消息
            user_messages = [msg for msg in messages if msg.get('role') == 'user']
            if user_messages:
                last_message = user_messages[-1]

                # 处理复合内容（文本+图片）
                if isinstance(last_message.get('content'), list):
                    text_content = ""
                    for item in last_message['content']:
                        if item.get('type') == 'input_text':
                            text_content += item.get('text', '')
                    final_message = {"role": "user", "content": text_content}
                else:
                    final_message = last_message

                # 构造简化的对话（只保留系统提示和最后用户消息）
                simplified_messages = []
                for msg in messages:
                    if msg.get('role') == 'system':
                        simplified_messages.append(msg)
                simplified_messages.append(final_message)
                return simplified_messages

            return [{"role": "user", "content": "Hello"}]
        except Exception as e:
            self.logger.warning(f"解析prompt失败: {e}，使用默认消息")
            return [{"role": "user", "content": complete_prompt_str[:100]}]

    async def test_single_prompt(self, prompt: Dict) -> TestResult:
        """
        测试单个prompt

        Args:
            prompt: prompt数据

        Returns:
            测试结果
        """
        prompt_id = prompt.get('id', 0)
        prompt_type = prompt.get('type', 'text')

        # 解析消息并计算输入token数
        try:
            messages = self.parse_complete_prompt(prompt['complete_prompt'])
            input_text = json.dumps(messages, ensure_ascii=False)
            input_tokens = self.estimate_tokens(input_text)
        except Exception as e:
            self.logger.error(f"解析prompt失败 (ID: {prompt_id}): {e}")
            input_tokens = self.estimate_tokens(str(prompt))

        start_time = time.time()

        try:
            # 发送请求
            response = await self.chat_completion(messages)

            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            # 提取响应文本
            content = self.extract_content(response)

            # 计算输出token数
            output_tokens = self.estimate_tokens(content)

            # 计算token生成速度
            if response_time_ms > 0:
                tokens_per_second = (output_tokens / response_time_ms) * 1000
            else:
                tokens_per_second = 0

            return TestResult(
                model_name=self.model_name,
                prompt_id=prompt_id,
                prompt_type=prompt_type,
                response_time_ms=response_time_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                tokens_per_second=tokens_per_second,
                success=True,
                raw_response=response
            )

        except Exception as e:
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            self.logger.error(f"测试失败 (ID: {prompt_id}): {e}")

            return TestResult(
                model_name=self.model_name,
                prompt_id=prompt_id,
                prompt_type=prompt_type,
                response_time_ms=response_time_ms,
                input_tokens=input_tokens,
                output_tokens=0,
                tokens_per_second=0,
                success=False,
                error_message=str(e)
            )

    async def run_test(self,
                       prompts: List[Dict],
                       delay_between_requests: float = 2.0) -> List[TestResult]:
        """
        运行模型测试

        Args:
            prompts: prompt列表
            delay_between_requests: 请求间隔（秒）

        Returns:
            测试结果列表
        """
        self.logger.info(f"🚀 开始测试模型: {self.model_name}")
        self.logger.info(f"📊 测试prompts数量: {len(prompts)}")

        # 为每个prompt添加时间戳
        for prompt in prompts:
            prompt['timestamp'] = datetime.now().isoformat()

        results = []
        for i, prompt in enumerate(prompts, 1):
            prompt_start_time = datetime.now()
            self.logger.info(f"[{prompt_start_time.strftime('%Y-%m-%d %H:%M:%S')}] [{i}/{len(prompts)}] 测试prompt ID: {prompt['id']}")

            result = await self.test_single_prompt(prompt)
            results.append(result)
            self.results.append(result)

            # 延迟避免API限制
            if delay_between_requests > 0:
                await asyncio.sleep(delay_between_requests)

            # 显示结果
            if result.success:
                self.logger.info(
                    f"    ✅ {result.response_time_ms:.0f}ms | "
                    f"{result.output_tokens}tokens | "
                    f"{result.tokens_per_second:.1f} tokens/s | "
                    f"时间戳: {result.timestamp}"
                )
            else:
                error_msg = result.error_message[:50] + "..." if len(result.error_message) > 50 else result.error_message
                self.logger.error(f"    ❌ 错误: {error_msg} | 时间戳: {result.timestamp}")

        return results

    def calculate_statistics(self) -> Dict[str, Any]:
        """
        计算统计指标

        Returns:
            统计结果字典
        """
        model_results = [r for r in self.results if r.success]

        if not model_results:
            return {"error": f"模型 {self.model_name} 没有成功的测试结果"}

        # 整体统计
        response_times = [r.response_time_ms for r in model_results]
        output_tokens = [r.output_tokens for r in model_results]
        tokens_per_second = [r.tokens_per_second for r in model_results]

        # 按类型分类统计
        text_results = [r for r in model_results if r.prompt_type == 'text']
        image_results = [r for r in model_results if r.prompt_type == 'image']

        stats = {
            "model_name": self.model_name,
            "total_tests": len(self.results),
            "successful_tests": len(model_results),
            "failed_tests": len(self.results) - len(model_results),

            "response_time_ms": {
                "mean": round(statistics.mean(response_times), 2),
                "median": round(statistics.median(response_times), 2),
                "min": round(min(response_times), 2),
                "max": round(max(response_times), 2),
                "p80": round(np.percentile(response_times, 80), 2),
                "p90": round(np.percentile(response_times, 90), 2),
                "p99": round(np.percentile(response_times, 99), 2),
            },

            "output_tokens": {
                "mean": round(statistics.mean(output_tokens), 2),
                "median": round(statistics.median(output_tokens), 2),
                "min": min(output_tokens),
                "max": max(output_tokens),
            },

            "tokens_per_second": {
                "mean": round(statistics.mean(tokens_per_second), 2),
                "median": round(statistics.median(tokens_per_second), 2),
                "min": round(min(tokens_per_second), 2),
                "max": round(max(tokens_per_second), 2),
                "p80": round(np.percentile(tokens_per_second, 80), 2),
                "p90": round(np.percentile(tokens_per_second, 90), 2),
                "p99": round(np.percentile(tokens_per_second, 99), 2),
            }
        }

        # 添加文本类型统计
        if text_results:
            text_response_times = [r.response_time_ms for r in text_results]
            text_output_tokens = [r.output_tokens for r in text_results]
            text_tokens_per_second = [r.tokens_per_second for r in text_results]

            stats["text_type"] = {
                "count": len(text_results),
                "response_time_ms": {
                    "mean": round(statistics.mean(text_response_times), 2),
                    "median": round(statistics.median(text_response_times), 2),
                    "min": round(min(text_response_times), 2),
                    "max": round(max(text_response_times), 2),
                    "p80": round(np.percentile(text_response_times, 80), 2),
                    "p90": round(np.percentile(text_response_times, 90), 2),
                    "p99": round(np.percentile(text_response_times, 99), 2),
                },
                "output_tokens": {
                    "mean": round(statistics.mean(text_output_tokens), 2),
                    "median": round(statistics.median(text_output_tokens), 2),
                    "min": min(text_output_tokens),
                    "max": max(text_output_tokens),
                },
                "tokens_per_second": {
                    "mean": round(statistics.mean(text_tokens_per_second), 2),
                    "median": round(statistics.median(text_tokens_per_second), 2),
                    "min": round(min(text_tokens_per_second), 2),
                    "max": round(max(text_tokens_per_second), 2),
                    "p80": round(np.percentile(text_tokens_per_second, 80), 2),
                    "p90": round(np.percentile(text_tokens_per_second, 90), 2),
                    "p99": round(np.percentile(text_tokens_per_second, 99), 2),
                }
            }

        # 添加图片类型统计
        if image_results:
            image_response_times = [r.response_time_ms for r in image_results]
            image_output_tokens = [r.output_tokens for r in image_results]
            image_tokens_per_second = [r.tokens_per_second for r in image_results]

            stats["image_type"] = {
                "count": len(image_results),
                "response_time_ms": {
                    "mean": round(statistics.mean(image_response_times), 2),
                    "median": round(statistics.median(image_response_times), 2),
                    "min": round(min(image_response_times), 2),
                    "max": round(max(image_response_times), 2),
                    "p80": round(np.percentile(image_response_times, 80), 2),
                    "p90": round(np.percentile(image_response_times, 90), 2),
                    "p99": round(np.percentile(image_response_times, 99), 2),
                },
                "output_tokens": {
                    "mean": round(statistics.mean(image_output_tokens), 2),
                    "median": round(statistics.median(image_output_tokens), 2),
                    "min": min(image_output_tokens),
                    "max": max(image_output_tokens),
                },
                "tokens_per_second": {
                    "mean": round(statistics.mean(image_tokens_per_second), 2),
                    "median": round(statistics.median(image_tokens_per_second), 2),
                    "min": round(min(image_tokens_per_second), 2),
                    "max": round(max(image_tokens_per_second), 2),
                    "p80": round(np.percentile(image_tokens_per_second, 80), 2),
                    "p90": round(np.percentile(image_tokens_per_second, 90), 2),
                    "p99": round(np.percentile(image_tokens_per_second, 99), 2),
                }
            }

        # 添加图片 vs 文本对比
        if text_results and image_results:
            text_avg_time = statistics.mean([r.response_time_ms for r in text_results])
            image_avg_time = statistics.mean([r.response_time_ms for r in image_results])
            text_avg_speed = statistics.mean([r.tokens_per_second for r in text_results])
            image_avg_speed = statistics.mean([r.tokens_per_second for r in image_results])

            time_diff_pct = ((image_avg_time - text_avg_time) / text_avg_time) * 100 if text_avg_time > 0 else 0
            speed_diff_pct = ((text_avg_speed - image_avg_speed) / image_avg_speed) * 100 if image_avg_speed > 0 else 0

            stats["image_vs_text_comparison"] = {
                "response_time": {
                    "text_mean_ms": round(text_avg_time, 2),
                    "image_mean_ms": round(image_avg_time, 2),
                    "image_vs_text_diff_pct": round(time_diff_pct, 2),
                    "analysis": "图片比文本慢" if time_diff_pct > 0 else "图片比文本快" if time_diff_pct < 0 else "图片和文本速度相同"
                },
                "tokens_per_second": {
                    "text_mean": round(text_avg_speed, 2),
                    "image_mean": round(image_avg_speed, 2),
                    "text_vs_image_diff_pct": round(speed_diff_pct, 2),
                    "analysis": "文本比图片快" if speed_diff_pct > 0 else "文本比图片慢" if speed_diff_pct < 0 else "文本和图片速度相同"
                }
            }

        return stats

    def print_statistics(self):
        """
        打印统计结果
        """
        stats = self.calculate_statistics()

        if "error" in stats:
            print(f"\n❌ {stats['error']}")
            return

        print(f"\n📊 {stats['model_name']} 测试统计结果:")
        print(f"  总测试: {stats['total_tests']} | 成功: {stats['successful_tests']} | 失败: {stats['failed_tests']}")

        rt = stats['response_time_ms']
        print(f"\n⏱️ 响应时间 (ms):")
        print(f"  均值: {rt['mean']} | 中位数: {rt['median']} | 最小: {rt['min']} | 最大: {rt['max']}")
        print(f"  P80: {rt['p80']} | P90: {rt['p90']} | P99: {rt['p99']}")

        tps = stats['tokens_per_second']
        print(f"\n🚀 Token生成速度 (tokens/s):")
        print(f"  均值: {tps['mean']} | 中位数: {tps['median']} | 最小: {tps['min']} | 最大: {tps['max']}")
        print(f"  P80: {tps['p80']} | P90: {tps['p90']} | P99: {tps['p99']}")

        tokens = stats['output_tokens']
        print(f"\n📝 输出Token数量:")
        print(f"  均值: {tokens['mean']} | 中位数: {tokens['median']} | 最小: {tokens['min']} | 最大: {tokens['max']}")

        # 打印文本类型统计
        if "text_type" in stats:
            text_stats = stats["text_type"]
            print(f"\n📝 文本类型 (无图片) - {text_stats['count']}个测试:")
            rt = text_stats['response_time_ms']
            print(f"  响应时间: 均值{rt['mean']}ms | 中位数{rt['median']}ms | 最小{rt['min']}ms | 最大{rt['max']}ms")
            tps = text_stats['tokens_per_second']
            print(f"  Token速度: 均值{tps['mean']} tok/s | 中位数{tps['median']} tok/s | 最小{tps['min']} tok/s | 最大{tps['max']} tok/s")
            tok = text_stats['output_tokens']
            print(f"  输出Token: 均值{tok['mean']} | 中位数{tok['median']} | 最小{tok['min']} | 最大{tok['max']}")

        # 打印图片类型统计
        if "image_type" in stats:
            image_stats = stats["image_type"]
            print(f"\n📸 图片类型 (有图片) - {image_stats['count']}个测试:")
            rt = image_stats['response_time_ms']
            print(f"  响应时间: 均值{rt['mean']}ms | 中位数{rt['median']}ms | 最小{rt['min']}ms | 最大{rt['max']}ms")
            tps = image_stats['tokens_per_second']
            print(f"  Token速度: 均值{tps['mean']} tok/s | 中位数{tps['median']} tok/s | 最小{tps['min']} tok/s | 最大{tps['max']} tok/s")
            tok = image_stats['output_tokens']
            print(f"  输出Token: 均值{tok['mean']} | 中位数{tok['median']} | 最小{tok['min']} | 最大{tok['max']}")

        # 打印图片 vs 文本对比
        if "image_vs_text_comparison" in stats:
            comp = stats["image_vs_text_comparison"]
            print(f"\n📊 图片 vs 文本速度对比:")
            print(f"  响应时间: 文本{comp['response_time']['text_mean_ms']}ms vs 图片{comp['response_time']['image_mean_ms']}ms")
            print(f"    {comp['response_time']['analysis']} {abs(comp['response_time']['image_vs_text_diff_pct']):.1f}%")
            print(f"  Token速度: 文本{comp['tokens_per_second']['text_mean']} tok/s vs 图片{comp['tokens_per_second']['image_mean']} tok/s")
            print(f"    {comp['tokens_per_second']['analysis']} {abs(comp['tokens_per_second']['text_vs_image_diff_pct']):.1f}%")

    def save_results(self, filename: str):
        """
        保存测试结果到文件

        Args:
            filename: 输出文件名
        """
        # 保存详细结果
        detailed_results = [asdict(r) for r in self.results]

        output = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "model_name": self.model_name,
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

        print(f"\n💾 测试结果已保存:")
        print(f"  • 详细结果: {filename}")
        print(f"  • 统计结果: {stats_filename}")

        # 打印统计结果
        self.print_statistics()