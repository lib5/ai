#!/usr/bin/env python3
"""
测试模型是否能读懂日历
"""

import asyncio
import json
from services.true_react_agent import TrueReActAgent
from config import settings

async def test_model_calendar_reading():
    """测试模型是否能读懂日历格式"""
    print("="*80)
    print("[测试] 模型读懂日历能力测试")
    print("="*80)

    # 创建一个简单的ReAct Agent
    agent = TrueReActAgent()

    # 测试问题：让模型根据日历计算"下周一"是哪一天
    test_queries = [
        {
            "query": "今天是2025年12月21日（星期日），下周一 是几月几号？",
            "expected_answer": "下周一应该是2025年12月22日"
        },
        {
            "query": "根据日历，2025年11月3日是星期几？",
            "expected_answer": "11月3日应该是星期一"
        },
        {
            "query": "请告诉我2026年1月的第一个星期一是什么时候？",
            "expected_answer": "2026年1月的第一个星期一是1月5日"
        }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\n[测试 {i}]: {test['query']}")
        print(f"预期答案: {test['expected_answer']}")
        print("-" * 80)

        try:
            # 获取系统提示词
            system_prompt = agent._build_system_prompt()
            print(f"[系统提示词片段 - 日历部分]:")
            # 只显示日历部分
            if "## 当前时间信息" in system_prompt:
                calendar_start = system_prompt.find("## 当前时间信息")
                calendar_end = system_prompt.find("## 用户信息", calendar_start)
                if calendar_end == -1:
                    calendar_end = system_prompt.find("## 可用工具", calendar_start)
                calendar_section = system_prompt[calendar_start:calendar_end]
                print(calendar_section[:500] + "..." if len(calendar_section) > 500 else calendar_section)
            print("-" * 80)

        except Exception as e:
            print(f"[错误] 测试 {i} 失败: {e}")

    print("\n" + "="*80)
    print("[说明]")
    print("模型需要能够：")
    print("1. 读取文本格式的日历")
    print("2. 通过位置对应确定某一天是星期几")
    print("3. 计算相对日期（下周一、下周末等）")
    print("4. 跨月计算（特别是年末年初）")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_model_calendar_reading())
