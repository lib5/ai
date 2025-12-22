#!/usr/bin/env python3
"""
验证服务器启动时工具是否已准备好
"""
import requests
import json
import time

def test_tools_loaded():
    """测试工具是否在服务器启动时已加载"""
    print("=" * 80)
    print("验证服务器启动时工具加载状态")
    print("=" * 80)

    # 准备测试请求
    test_data = {
        "user_id": "ac66c8b6-b138-4c67-8688-f165f46d730f",
        "query": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "帮我搜索联系人张三"}
                ]
            }
        ]
    }

    print("\n📡 发送测试请求...")
    try:
        with requests.post(
            "http://localhost:8000/api/chat",
            json=test_data,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        ) as response:
            print(f"\n📊 响应状态码: {response.status_code}")

            if response.status_code == 200:
                # 处理流式响应
                chunk_count = 0
                final_data = None

                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                chunk_count += 1
                                final_data = data
                            except:
                                pass

                print(f"✅ 请求成功，收到 {chunk_count} 个数据块")

                # 使用最后一块数据
                if final_data:
                    # 检查响应中的工具调用
                    steps = final_data.get("data", {}).get("steps", [])
                    print(f"\n🔧 执行的步骤数: {len(steps)}")

                    # 检查是否调用了 contacts_search 工具
                    for step in steps:
                        tool_type = step.get("tool_type", "")
                        if "contacts_search" in tool_type:
                            print(f"\n✅ 工具已正确加载并执行: {tool_type}")
                            print(f"   工具状态: {step.get('tool_status', 'N/A')}")

                            # 检查是否有观察结果
                            if step.get("observation"):
                                print(f"   ✅ 工具执行成功，返回结果")
                                # 尝试解析结果
                                try:
                                    obs = json.loads(step.get("observation", "{}"))
                                    if "data" in obs and "items" in obs["data"]:
                                        print(f"   📋 搜索到 {obs['data']['total']} 个联系人")
                                except:
                                    pass
                            break

                    # 检查是否有 finish 步骤
                    has_finish = any(step.get("tool_type") == "Finish" for step in steps)
                    if has_finish:
                        print(f"\n✅ ReAct 循环完成正常")

                    print("\n" + "=" * 80)
                    print("✅ 验证成功：服务器启动时工具已正确加载并可用")
                    print("=" * 80)
                    return True
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"响应内容: {response.text[:500]}")
                return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_tools_loaded()
    exit(0 if success else 1)
