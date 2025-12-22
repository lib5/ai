#!/usr/bin/env python3
"""
测试系统提示词是否包含工具
"""
import asyncio
from services.true_react_agent import true_react_agent

async def test_system_prompt():
    print("=" * 80)
    print("测试系统提示词")
    print("=" * 80)

    # 初始化
    await true_react_agent.initialize()

    # 构建系统提示词
    prompt = true_react_agent._build_system_prompt()

    # 查找工具部分
    print("\n🔍 查找系统提示词中的工具部分...")
    lines = prompt.split('\n')

    # 打印整个系统提示词的前50行和工具部分
    print("\n📝 系统提示词前50行:")
    print("-" * 80)
    for i, line in enumerate(lines[:50]):
        print(f"{i+1:3d}: {line}")

    # 查找并打印工具部分
    print("\n" + "=" * 80)
    print("🔧 工具部分详情:")
    print("=" * 80)
    in_tools_section = False
    for i, line in enumerate(lines):
        if '可用工具' in line:
            in_tools_section = True
            print(f"\n✅ 找到工具部分在第{i+1}行")
            print(f"   内容: {line}")
            print("\n📋 工具列表:")
            print("-" * 80)
            # 打印接下来的30行或直到下一个章节
            for j in range(i+1, min(i+31, len(lines))):
                if lines[j].strip() and not lines[j].startswith('#') and '输出格式' in lines[j]:
                    print(f"\n[工具部分结束于第{j+1}行]")
                    break
                print(lines[j])
            break

    if not in_tools_section:
        print("\n❌ 未找到工具部分！")

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_system_prompt())
