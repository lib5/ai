#!/usr/bin/env python3
"""
测试简化后的日历格式
"""

import asyncio
from services.true_react_agent import TrueReActAgent

async def test_simplified_calendar():
    print("="*80)
    print("[测试] 简化后的日历格式")
    print("="*80)

    agent = TrueReActAgent()
    calendar_info = agent._get_calendar_info()

    print("\n[简化日历信息]:")
    print("-" * 80)
    print(calendar_info)
    print("-" * 80)

    print("\n[格式验证]:")
    lines = calendar_info.split('\n')

    # 检查关键元素
    checks = {
        "当前时间信息": any("## 当前时间信息" in line for line in lines),
        "日期星期对照表": any("## 日期星期对照表" in line for line in lines),
        "2025年11月": any("2025年11月" in line for line in lines),
        "2025年12月": any("2025年12月" in line for line in lines),
        "2026年1月": any("2026年1月" in line for line in lines),
        "使用说明": any("## 使用说明" in line for line in lines),
    }

    for key, result in checks.items():
        print(f"  {key}: {'✓' if result else '✗'}")

    # 检查日期格式
    print("\n[日期格式示例]:")
    date_lines = [line for line in lines if "月" in line and "日" in line and "=" in line]
    for line in date_lines[:5]:  # 显示前5行
        print(f"  {line}")

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_simplified_calendar())
