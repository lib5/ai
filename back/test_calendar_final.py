#!/usr/bin/env python3
"""
测试最终修复的日历功能
"""

import asyncio
from services.true_react_agent import TrueReActAgent

async def test_final_calendar():
    print("="*80)
    print("[测试] 最终修复的日历格式")
    print("="*80)

    agent = TrueReActAgent()
    calendar_info = agent._get_calendar_info()

    print("\n[日历信息]:")
    print("-" * 80)
    print(calendar_info)
    print("-" * 80)

    # 验证2025年11月的格式
    print("\n[验证2025年11月]:")
    lines = calendar_info.split('\n')
    for i, line in enumerate(lines):
        if "上个月(11)" in line:
            print(f"月标题: {line}")
            # 接下来是星期表头
            if i+1 < len(lines):
                print(f"星期表头: {lines[i+1]}")
            # 接下来几行是日期
            for j in range(2, min(7, len(lines) - i)):
                if i+j < len(lines):
                    print(f"日期行{j-1}: {lines[i+j]}")

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_final_calendar())
