# -*- coding: utf-8 -*-
"""
模型速度测试模块

本模块提供了统一的模型速度测试框架，支持多个AI模型供应商的测试。

主要组件:
- BaseTester: 抽象基类，定义测试器的基本接口
- 测试模块: doubao/, qwen/, deepseek/, gemini/
"""

from .base_tester import BaseTester, TestResult

__all__ = [
    'BaseTester',
    'TestResult'
]