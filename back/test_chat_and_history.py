"""
Chat 和 History 接口测试脚本
测试 POST /api/v1/chat 和 POST /api/v1/chat/history 接口
"""
import asyncio
import json
import os
import sys
import httpx
from uuid import uuid4
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 测试配置
API_BASE_URL = os.getenv("TEST_BASE_URL", "http://192.168.106.108:8000")
# API_BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")

print(f"API_BASE_URL: {API_BASE_URL}")


async def get_test_session():
    """获取测试用的 session_id"""
    try:
        from app.services.verification_code_service import verification_code_service
        
        # 生成测试手机号
        test_phone = f"138{''.join([str(uuid4().int % 10) for _ in range(8)])}"
        test_code = "123456"
        
        # 设置验证码
        await verification_code_service.set_verification_code(test_phone, test_code)
        
        # 登录获取 session_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json={
                    "phone": test_phone,
                    "verification_code": test_code
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                session_id = data.get("session_id")
                user_id = data.get("user_id")
                print(f"✅ 获取测试 session 成功")
                print(f"   Session ID: {session_id}")
                print(f"   User ID: {user_id}")
                return session_id, user_id
            else:
                print(f"❌ 登录失败: {response.status_code} - {response.text}")
                return None, None
    except Exception as e:
        print(f"⚠️  无法自动获取 session（可能不在测试环境）: {str(e)}")
        print(f"   请手动提供 session_id 和 user_id")
        return None, None


async def test_chat_text_only(session_id: str):
    """测试 Chat 接口 - 纯文本消息"""
    print("\n" + "=" * 60)
    print("💬 测试 Chat 接口 - 纯文本消息")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            request_data = {
                "content": "你好，请介绍一下你自己"
            }
            
            print(f"\n📤 发送请求:")
            print(f"   URL: {API_BASE_URL}/api/v1/chat")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            async with client.stream(
                "POST",
                f"{API_BASE_URL}/api/v1/chat",
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-Id": session_id,
                    "X-App-Id": "test-app",
                    "X-App-Version": "1.0.0",
                    "X-Device-Id": "test-device-001",
                }
            ) as response:
                print(f"\n📥 响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"\n📨 流式响应内容:")
                    print("-" * 60)
                    
                    chunk_count = 0
                    all_responses = []
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                chunk_count += 1
                                all_responses.append(data)
                                
                                print(f"\n[Chunk {chunk_count}]")
                                print(f"   完整数据:")
                                print(json.dumps(data, indent=4, ensure_ascii=False))
                                
                            except json.JSONDecodeError as e:
                                print(f"   ⚠️  JSON 解析失败: {data_str[:100]}")
                    
                    print("-" * 60)
                    print(f"\n✅ 测试完成，共收到 {chunk_count} 个响应块")
                    return all_responses
                else:
                    print(f"❌ 请求失败，状态码: {response.status_code}")
                    error_text = await response.aread()
                    print(f"   错误内容: {error_text.decode('utf-8', errors='ignore')}")
                    return []
                    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


async def test_chat_with_shortcut(session_id: str):
    """测试 Chat 接口 - 文本 + 快捷指令"""
    print("\n" + "=" * 60)
    print("💬 测试 Chat 接口 - 文本 + 快捷指令")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            request_data = {
                "content": [
                    {
                        "type": "text",
                        "text": "请帮我创建一个日程"
                    },
                    {
                        "type": "shortcut",
                        "shortcut": {
                            "shortcut": "创建日程"
                        }
                    }
                ]
            }
            
            print(f"\n📤 发送请求:")
            print(f"   URL: {API_BASE_URL}/api/v1/chat")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            async with client.stream(
                "POST",
                f"{API_BASE_URL}/api/v1/chat",
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-Id": session_id,
                }
            ) as response:
                print(f"\n📥 响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    chunk_count = 0
                    all_responses = []
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                chunk_count += 1
                                all_responses.append(data)
                                print(f"\n[Chunk {chunk_count}] Type: {data.get('type', 'unknown')}")
                            except json.JSONDecodeError:
                                pass
                    
                    print(f"\n✅ 测试完成，共收到 {chunk_count} 个响应块")
                    return all_responses
                else:
                    print(f"❌ 请求失败，状态码: {response.status_code}")
                    return []
                    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


async def test_chat_history(user_id: str):
    """测试 History 接口 - 获取聊天历史"""
    print("\n" + "=" * 60)
    print("📜 测试 Chat History 接口")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 测试1: 基本查询
            print("\n📤 测试1: 基本查询（默认分页）")
            request_data = {
                "user_id": user_id,
            }
            
            print(f"   URL: {API_BASE_URL}/api/v1/chat/history")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            response = await client.post(
                f"{API_BASE_URL}/api/v1/chat/history",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n📥 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ 请求成功")
                print(f"\n   响应数据:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
                
                # 解析消息
                if "data" in response_data and "messages" in response_data["data"]:
                    messages = response_data["data"]["messages"]
                    print(f"\n   消息数量: {len(messages)}")
                    
                    for i, msg in enumerate(messages, 1):
                        role = msg.get("role", "unknown")
                        print(f"\n   消息 {i}:")
                        print(f"      Role: {role}")
                        
                        if role == "user":
                            data = msg.get("data", [])
                            print(f"      Data 项数: {len(data)}")
                            for j, item in enumerate(data, 1):
                                item_type = item.get("type", "unknown")
                                print(f"        项 {j}: type={item_type}")
                                if item_type == "shortcut":
                                    print(f"          Shortcut: {item.get('shortcut', {}).get('shortcut', 'N/A')}")
                                elif item_type == "input_text":
                                    text = item.get("text", "")
                                    print(f"          Text: {text[:50]}..." if len(text) > 50 else f"          Text: {text}")
                        
                        elif role == "assistant":
                            message_id = msg.get("message_id", "N/A")
                            data = msg.get("data", [])
                            print(f"      Message ID: {message_id}")
                            print(f"      Data 项数: {len(data)}")
                            
                            for j, item in enumerate(data, 1):
                                item_type = item.get("type", "unknown")
                                print(f"        项 {j}: type={item_type}")
                                
                                if item_type == "tool":
                                    content = item.get("content", {})
                                    print(f"          Tool: {content.get('name', 'N/A')} ({content.get('name_cn', 'N/A')})")
                                    print(f"          Status: {content.get('status', 'N/A')}")
                                
                                elif item_type == "markdown":
                                    content = item.get("content", "")
                                    print(f"          Content: {content[:50]}..." if len(content) > 50 else f"          Content: {content}")
                                
                                elif item_type == "card":
                                    content = item.get("content", {})
                                    print(f"          Card Type: {content.get('card_type', 'N/A')}")
                                    print(f"          Card ID: {content.get('card_id', 'N/A')}")
                
                return response_data
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                print(f"   错误内容: {response.text}")
                return None
                
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_chat_history_with_pagination(user_id: str):
    """测试 History 接口 - 带分页参数"""
    print("\n" + "=" * 60)
    print("📜 测试 Chat History 接口 - 分页查询")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            request_data = {
                "user_id": user_id,
                "page": 1,
                "page_size": 10
            }
            
            print(f"\n📤 发送请求:")
            print(f"   URL: {API_BASE_URL}/api/v1/chat/history")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            response = await client.post(
                f"{API_BASE_URL}/api/v1/chat/history",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"\n📥 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ 请求成功")
                
                if "data" in response_data and "messages" in response_data["data"]:
                    messages = response_data["data"]["messages"]
                    print(f"\n   返回消息数量: {len(messages)}")
                    print(f"   分页参数: page=1, page_size=10")
                
                return response_data
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def test_chat_and_history_flow(session_id: str, user_id: str):
    """测试完整的流程：发送消息 -> 获取历史"""
    print("\n" + "=" * 60)
    print("🔄 测试完整流程：发送消息 -> 获取历史")
    print("=" * 60)
    
    # 1. 先发送一条消息
    print("\n步骤1: 发送消息")
    chat_responses = await test_chat_text_only(session_id)
    
    if not chat_responses:
        print("⚠️  消息发送失败，跳过历史查询测试")
        return
    
    # 等待一下，确保消息已保存
    await asyncio.sleep(2)
    
    # 2. 获取聊天历史
    print("\n步骤2: 获取聊天历史")
    history_data = await test_chat_history(user_id)
    
    if history_data:
        print("\n✅ 完整流程测试成功")
    else:
        print("\n⚠️  历史查询失败")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 Chat 和 History API 接口测试")
    print("=" * 60)
    
    # 获取测试 session
    session_id, user_id = await get_test_session()
    
    if not session_id or not user_id:
        print("\n⚠️  无法获取测试 session，请手动提供")
        session_id = input("请输入 session_id (或按 Enter 跳过): ").strip()
        if not session_id:
            print("❌ 未提供 session_id，退出测试")
            return
        
        user_id = input("请输入 user_id (或按 Enter 跳过): ").strip()
        if not user_id:
            print("⚠️  未提供 user_id，将跳过需要 user_id 的测试")
            user_id = None
    
    # 运行测试
    if session_id:
        await test_chat_text_only(session_id)
        await asyncio.sleep(1)
        
        await test_chat_with_shortcut(session_id)
        await asyncio.sleep(1)
    
    if user_id:
        await test_chat_history(user_id)
        await asyncio.sleep(1)
        
        await test_chat_history_with_pagination(user_id)
        await asyncio.sleep(1)
    
    if session_id and user_id:
        await test_chat_and_history_flow(session_id, user_id)
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
