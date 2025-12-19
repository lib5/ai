#!/usr/bin/env python3
"""
简单的 ReAct 模式测试
测试修改后的 ReAct Agent 是否能正确使用具体工具
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, '/home/libo/chatapi')

from services.true_react_agent import true_react_agent


async def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("🚀 测试 ReAct Agent (使用具体工具)")
    print("=" * 80 + "\n")

    # 测试问题
    test_queries = [
        "搜索关于 Python 编程的信息",
        "搜索人工智能最新发展",
        "搜索机器学习入门指南"
    ]

    for query in test_queries:
        print("\n" + "=" * 80)
        print(f"🔍 测试查询: {query}")
        print("=" * 80)

        try:
            result = await true_react_agent.run(query)

            print(f"\n✅ 查询完成")
            print(f"📝 问题: {result.get('query')}")
            print(f"💡 答案: {result.get('answer', 'N/A')[:200]}...")
            print(f"🔄 迭代次数: {result.get('iterations', 0)}")
            print(f"📊 步骤数: {len(result.get('steps', []))}")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
