#!/usr/bin/env python3
"""
测试修复后的日历格式
"""

import asyncio
from services.true_react_agent import TrueReActAgent

async def test_calendar():
    print("="*80)
    print("[测试] 修复后的日历格式")
    print("="*80)

    agent = TrueReActAgent()
    calendar_info = agent._get_calendar_info()

    print("\n[日历信息]:")
    print("-" * 80)
    print(calendar_info)
    print("-" * 80)

    # 特别验证11月1日的位置
    print("\n[特别验证2025年11月]:")
    lines = calendar_info.split('\n')
    for i, line in enumerate(lines):
        if "上个月(11)" in line:
            print(f"\n月标题: {line}")
            print(f"星期表头: {lines[i+1]}")

            # 检查11月1日所在的行
            for j in range(2, min(7, len(lines) - i)):
                if i+j < len(lines):
                    date_line = lines[i+j]
                    print(f"日期行{j-1}: {date_line}")

                    # 检查这一行是否有11月1日
                    if " 1 " in date_line or " 1" in date_line:
                        print(f"  -> 11月1日在这一行！")

                        # 计算位置
                        if " 1 " in date_line:
                            pos = date_line.index(" 1 ")
                        else:
                            pos = date_line.index(" 1")

                        print(f"  -> 位置索引: {pos}")
                        print(f"  -> 对应的星期: 根据表头，索引{pos//3}应该是：{['日', '一', '二', '三', '四', '五', '六'][pos//3]}")

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_calendar())
