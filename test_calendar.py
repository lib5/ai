#!/usr/bin/env python3
"""
测试日历功能
验证系统提示词中的日历信息是否正确显示
"""

import asyncio
from services.true_react_agent import TrueReActAgent

async def test_calendar_info():
    """测试日历信息生成"""
    print("="*80)
    print("[测试] 日历功能测试")
    print("="*80)

    # 创建 ReAct Agent 实例
    agent = TrueReActAgent()

    # 获取日历信息
    calendar_info = agent._get_calendar_info()

    print("\n[日历信息内容]:")
    print("-" * 80)
    print(calendar_info)
    print("-" * 80)

    # 验证日历信息的关键元素
    checks = [
        ("当前时间", "当前时间：" in calendar_info),
        ("星期信息", "今天是星期" in calendar_info),
        ("当前日期", "当前日期：" in calendar_info),
        ("月历信息", "## 月历信息" in calendar_info),
        ("上个月", "上个月(" in calendar_info),
        ("当前月", "当前月(" in calendar_info),
        ("下个月", "下个月(" in calendar_info),
        ("使用说明", "## 使用说明" in calendar_info),
    ]

    print("\n[验证结果]:")
    all_passed = True
    for name, result in checks:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False

    print("\n" + "="*80)
    if all_passed:
        print("[成功] 所有测试通过！日历功能正常工作。")
    else:
        print("[警告] 部分测试失败，请检查日历功能。")
    print("="*80)

    return all_passed

async def test_system_prompt_with_calendar():
    """测试包含日历信息的系统提示词"""
    print("\n" + "="*80)
    print("[测试] 系统提示词中的日历信息")
    print("="*80)

    # 创建 ReAct Agent 实例
    agent = TrueReActAgent()

    # 构建系统提示词（不包含图像和用户元数据）
    system_prompt = agent._build_system_prompt()

    print("\n[系统提示词片段]:")
    print("-" * 80)
    # 只显示前2000个字符
    print(system_prompt[:2000])
    if len(system_prompt) > 2000:
        print("\n... (内容过长，已截断) ...")
    print("-" * 80)

    # 验证系统提示词是否包含日历信息
    calendar_in_prompt = "当前时间：" in system_prompt and "月历信息" in system_prompt

    print(f"\n[验证结果]: {'✓ 系统提示词包含日历信息' if calendar_in_prompt else '✗ 系统提示词缺少日历信息'}")

    print("="*80)
    return calendar_in_prompt

async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("日历功能测试套件")
    print("="*80)

    # 测试1: 基础日历信息生成
    test1_result = await test_calendar_info()

    # 测试2: 系统提示词集成
    test2_result = await test_system_prompt_with_calendar()

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    print(f"  基础日历信息: {'✓ 通过' if test1_result else '✗ 失败'}")
    print(f"  系统提示词集成: {'✓ 通过' if test2_result else '✗ 失败'}")

    if test1_result and test2_result:
        print("\n[✓ 所有测试通过！日历功能已成功集成到系统中。]")
    else:
        print("\n[✗ 部分测试失败，请检查实现。]")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
