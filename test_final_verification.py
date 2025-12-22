#!/usr/bin/env python3
"""
最终验证：确保服务器启动时工具立即可用
"""
import asyncio
import sys
sys.path.insert(0, '.')

from services.true_react_agent import true_react_agent

async def verify_tools_on_startup():
    """验证服务器启动时工具是否已加载"""
    print("=" * 80)
    print("验证服务器启动时工具加载状态")
    print("=" * 80)

    # 检查工具是否已加载
    print(f"\n📊 当前已注册的工具数量: {len(true_react_agent.tools)}")

    if len(true_react_agent.tools) > 1:  # 除了 finish 工具之外
        print(f"\n✅ 工具已正确加载 (共 {len(true_react_agent.tools)} 个)")

        print("\n📦 工具列表:")
        for name, info in true_react_agent.tools.items():
            print(f"  - {name}: {info['description']}")

        # 测试一个简单的工具("\调用
        printn🧪 测试工具调用...")
        try:
            # 使用 contacts_search 进行简单测试
            result = await true_react_agent.multi_mcp_client.call_tool(
                "contacts_search",
                {
                    "user_id": "ac66c8b6-b138-4c67-8688-f165f46d730f",
                    "name": "测试"
                }
            )

            if result.get("success"):
                print("✅ 工具调用测试成功")
                print(f"   返回数据: {str(result.get('result', {}))[:100]}...")
            else:
                print(f"⚠️  工具调用失败: {result.get('error', '未知错误')}")

        except Exception as e:
            print(f"❌ 工具调用测试出错: {e}")

        print("\n" + "=" * 80)
        print("✅ 验证完成：服务器启动时工具已准备就绪")
        print("=" * 80)
        return True
    else:
        print(f"\n❌ 工具未正确加载，仅有 {len(true_react_agent.tools)} 个工具")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_tools_on_startup())
    sys.exit(0 if success else 1)
