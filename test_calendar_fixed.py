#!/usr/bin/env python3
"""
测试修复后的日历功能
验证日历格式是否正确对齐
"""

import asyncio
from services.true_react_agent import TrueReActAgent

async def test_calendar_format():
    """测试日历格式是否正确对齐"""
    print("="*80)
    print("[测试] 修复后的日历格式")
    print("="*80)

    # 创建 ReAct Agent 实例
    agent = TrueReActAgent()

    # 获取日历信息
    calendar_info = agent._get_calendar_info()

    print("\n[修复后的日历信息]:")
    print("-" * 80)
    print(calendar_info)
    print("-" * 80)

    # 验证关键点
    print("\n[格式验证]:")
    lines = calendar_info.split('\n')

    # 查找月历部分
    in_calendar_section = False
    for i, line in enumerate(lines):
        if "上个月(" in line or "当前月(" in line or "下个月(" in line:
            in_calendar_section = True
            print(f"\n月历开始: {line}")

        if in_calendar_section:
            print(f"  行 {i}: {line}")

            # 检查星期表头
            if "日  一  二  三  四  五  六" in line:
                print(f"    ✓ 星期表头格式正确")

            # 如果是日期行，检查格式
            if line.strip() and not line.startswith(" ") and not "月历信息" in line and not "日期对应的星期" in line:
                # 计算每行的字符数
                print(f"    行长度: {len(line)} 字符")

        # 如果遇到日期对应的星期，说明月历部分结束
        if "日期对应的星期" in line:
            in_calendar_section = False
            print(f"月历结束: {line}\n")

    print("\n" + "="*80)
    print("[测试完成] 请检查日历格式是否对齐正确")
    print("="*80)

async def main():
    await test_calendar_format()

if __name__ == "__main__":
    asyncio.run(main())
