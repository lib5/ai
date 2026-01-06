#!/usr/bin/env python3
"""
快速检查MCP服务器状态和可用工具
"""

import asyncio
from services.mcp_client import ModelscopeMCPClient
from config import settings


async def check_mcp_status():
    """检查MCP服务器状态"""
    print("=" * 70)
    print("MCP服务器状态检查")
    print("=" * 70)

    # 显示配置信息
    print(f"\n📋 配置信息:")
    print(f"  MCP服务器URL: {settings.mcp_server_url}")

    # 尝试连接MCP服务器
    try:
        mcp_client = ModelscopeMCPClient(settings.mcp_server_url)
        async with mcp_client:
            print(f"\n✅ MCP服务器连接成功")

            # 获取工具列表
            print(f"\n🔧 获取可用工具...")
            tools = await mcp_client.list_tools()

            if tools:
                print(f"\n✅ 找到 {len(tools)} 个可用工具:")
                print("-" * 70)

                # 按类型分类显示工具
                vision_tools = []
                modelscope_tools = []
                other_tools = []

                for tool in tools:
                    tool_name = tool.get('name', 'unknown')
                    tool_desc = tool.get('description', '无描述')

                    if any(keyword in tool_name.lower() for keyword in ['vision', 'visual', 'image', 'clip']):
                        vision_tools.append((tool_name, tool_desc))
                    elif 'modelscope' in tool_name.lower():
                        modelscope_tools.append((tool_name, tool_desc))
                    else:
                        other_tools.append((tool_name, tool_desc))

                # 显示视觉工具
                if vision_tools:
                    print("\n  🎨 视觉分析工具:")
                    for name, desc in vision_tools:
                        print(f"    - {name}")
                        print(f"      └─ {desc}")

                # 显示ModelScope工具
                if modelscope_tools:
                    print("\n  📦 ModelScope工具:")
                    for name, desc in modelscope_tools:
                        print(f"    - {name}")
                        print(f"      └─ {desc}")

                # 显示其他工具
                if other_tools:
                    print("\n  🔨 其他工具:")
                    for name, desc in other_tools:
                        print(f"    - {name}")
                        print(f"      └─ {desc}")

                print("-" * 70)

                # 总结
                print(f"\n✅ MCP服务器状态: 正常")
                print(f"   总工具数: {len(tools)}")
                print(f"   视觉工具: {len(vision_tools)}")
                print(f"   ModelScope工具: {len(modelscope_tools)}")
                print(f"   其他工具: {len(other_tools)}")

                # 提示下一步
                if vision_tools:
                    print("\n💡 提示: 检测到视觉工具，可以进行图像分析测试")
                    print("   运行: python test_react_vision_complete.py")
                else:
                    print("\n⚠️  警告: 未检测到视觉工具，图像分析将使用Azure OpenAI作为回退")

            else:
                print("\n⚠️  警告: MCP服务器返回空工具列表")

    except Exception as e:
        print(f"\n❌ MCP服务器连接失败")
        print(f"   错误: {str(e)}")
        print(f"\n💡 可能的原因:")
        print(f"   1. MCP服务器未启动")
        print(f"   2. 端口 {settings.mcp_server_url} 无法访问")
        print(f"   3. 网络连接问题")
        print(f"\n💡 解决方案:")
        print(f"   1. 启动MCP服务器: npx -y vision-mcp-server")
        print(f"   2. 检查端口配置: {settings.mcp_server_url}")
        print(f"   3. 查看防火墙设置")
        print(f"\n✅ 系统仍可使用Azure OpenAI Vision作为回退方案")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(check_mcp_status())
