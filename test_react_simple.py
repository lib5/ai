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

    # 初始化agent
    print("📋 正在初始化 ReAct Agent...")
    try:
        await true_react_agent.initialize()
        print("✅ ReAct Agent 初始化成功\n")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return

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
            # run 方法返回 AsyncGenerator，需要用 async for
            final_result = None
            async for output in true_react_agent.run(query):
                output_type = output.get('type')
                if output_type == 'final_answer':
                    final_result = output
                    break

            if final_result:
                print(f"\n✅ 查询完成")
                print(f"💡 答案: {final_result.get('answer', 'N/A')[:200]}...")

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
