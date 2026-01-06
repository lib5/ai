#!/usr/bin/env python3
"""
测试 bing-cn-search MCP 服务器的工具
测试工具: bing_search 和 fetch_webpage
"""
import asyncio
import json
import sys
from typing import Dict, Any

# 添加 services 目录到路径
sys.path.insert(0, '/home/libo/chatapi')

from services.multi_mcp_client import MultiMCPClient


async def test_bing_search_tools():
    """测试 bing-cn-search MCP 服务器的工具"""
    print("\n" + "=" * 80)
    print("🧪 测试 bing-cn-search MCP 服务器工具")
    print("=" * 80)

    # 创建多 MCP 客户端
    multi_mcp = MultiMCPClient()

    # 列出所有工具
    print("\n📋 列出所有 MCP 服务器的工具...")
    all_tools = await multi_mcp.list_all_tools()

    print(f"\n✅ 总共找到 {len(multi_mcp.get_available_tools())} 个工具:")
    for tool_name in multi_mcp.get_available_tools():
        server = multi_mcp.get_tool_server(tool_name)
        print(f"  - {tool_name} (来自 {server})")

    # 测试 bing_search 工具
    print("\n" + "=" * 80)
    print("🔍 测试 bing_search 工具")
    print("=" * 80)

    if "bing_search" in multi_mcp.get_available_tools():
        print("\n📝 执行搜索: 'Python 编程教程'")
        result = await multi_mcp.call_tool("bing_search", {
            "query": "Python 编程教程",
            "count": 5
        })

        print(f"\n📊 搜索结果:")
        if result.get("success"):
            print(f"  ✅ 工具调用成功")
            print(f"  🖥️  服务器: {result.get('server')}")
            print(f"  📦 结果数据:")
            print(json.dumps(result.get("result"), indent=2, ensure_ascii=False))
        else:
            print(f"  ❌ 工具调用失败")
            print(f"  错误: {result.get('error')}")

    else:
        print("\n⚠️  未找到 'bing_search' 工具")

    # 测试 fetch_webpage 工具
    print("\n" + "=" * 80)
    print("🌐 测试 fetch_webpage 工具")
    print("=" * 80)

    if "fetch_webpage" in multi_mcp.get_available_tools():
        print("\n📝 步骤 1: 先进行搜索获取 result_id")
        search_result = await multi_mcp.call_tool("bing_search", {
            "query": "Python 教程",
            "count": 1
        })

        if search_result.get("success") and search_result.get("result"):
            # 从搜索结果中提取 result_id
            search_data = search_result.get("result", [])
            if isinstance(search_data, list) and len(search_data) > 0:
                first_result = search_data[0]
                result_id = first_result.get("id")
                link = first_result.get("link")
                title = first_result.get("title")

                print(f"\n📋 获取到搜索结果:")
                print(f"  标题: {title}")
                print(f"  链接: {link}")
                print(f"  ID: {result_id}")

                print("\n📝 步骤 2: 使用 result_id 获取网页内容")
                fetch_result = await multi_mcp.call_tool("fetch_webpage", {
                    "result_id": result_id
                })

                print(f"\n📊 网页获取结果:")
                if fetch_result.get("success"):
                    print(f"  ✅ 工具调用成功")
                    print(f"  🖥️  服务器: {fetch_result.get('server')}")

                    # 提取结果数据
                    result_data = fetch_result.get("result", {})
                    if isinstance(result_data, dict):
                        print(f"  📄 标题: {result_data.get('title', 'N/A')}")
                        print(f"  📏 内容长度: {len(result_data.get('content', ''))} 字符")
                        print(f"  📝 内容预览:")
                        content = result_data.get('content', '')
                        if content:
                            preview = content[:500] + "..." if len(content) > 500 else content
                            print(f"     {preview}")
                        print(f"\n  📦 完整结果:")
                        print(json.dumps(result_data, indent=2, ensure_ascii=False))
                    else:
                        print(f"  📦 结果数据:")
                        print(json.dumps(result_data, indent=2, ensure_ascii=False))
                else:
                    print(f"  ❌ 工具调用失败")
                    print(f"  错误: {fetch_result.get('error')}")
            else:
                print("  ❌ 搜索结果为空")
        else:
            print(f"  ❌ 搜索失败: {search_result.get('error')}")

    else:
        print("\n⚠️  未找到 'fetch_webpage' 工具")

    # 额外测试：使用 bing_search 搜索更多关键词
    print("\n" + "=" * 80)
    print("🔍 额外测试: 搜索不同关键词")
    print("=" * 80)

    if "bing_search" in multi_mcp.get_available_tools():
        test_queries = [
            "人工智能最新发展",
            "机器学习入门指南",
            "Python Web 开发框架"
        ]

        for query in test_queries:
            print(f"\n🔎 搜索: '{query}'")
            result = await multi_mcp.call_tool("bing_search", {
                "query": query,
                "count": 3
            })

            if result.get("success"):
                print(f"  ✅ 搜索成功")
                # 尝试提取搜索结果数量
                search_results = result.get("result", {})
                if isinstance(search_results, dict):
                    items = search_results.get("items", search_results.get("results", []))
                    print(f"  📊 返回结果数: {len(items) if isinstance(items, list) else 'N/A'}")
                else:
                    print(f"  📊 结果: {str(search_results)[:100]}...")
            else:
                print(f"  ❌ 搜索失败: {result.get('error')}")

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)


def main():
    """主函数"""
    try:
        asyncio.run(test_bing_search_tools())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
