"""
Chat 接口测试脚本
测试 POST /api/v1/chat 接口（流式响应）
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 测试配置
API_BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
# API_BASE_URL = os.getenv("TEST_BASE_URL", "http://192.168.106.108:8000")

print(f"API_BASE_URL: {API_BASE_URL}")


async def get_test_session():
    """获取测试用的 session_id"""
    try:
        from app.services.verification_code_service import \
            verification_code_service

        # 生成测试手机号
        test_phone = "13800138013"#f"138{''.join([str(uuid4().int % 10) for _ in range(8)])}"
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
        print(f"   请手动提供 session_id")
        return None, None


async def test_chat_text_only(session_id: str):
    """测试纯文本消息"""
    print("\n" + "=" * 60)
    print("💬 测试 Chat 接口 - 纯文本消息")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 准备请求数据
            request_data = {
                "content": "你好，请介绍一下你自己"
            }
            
            print(f"\n📤 发送请求:")
            print(f"   URL: {API_BASE_URL}/api/v1/chat")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            # 发送 POST 请求（流式响应）
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
                    "X-OS-Type": "iOS",
                    "X-OS-Version": "17.0",
                }
            ) as response:
                print(f"\n📥 响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"\n📨 流式响应内容:")
                    print("-" * 60)
                    
                    chunk_count = 0
                    all_responses = []  # 保存所有响应
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        # 解析 SSE 格式：data: {...}
                        if line.startswith("data: "):
                            data_str = line[6:]  # 去掉 "data: " 前缀
                            try:
                                data = json.loads(data_str)
                                chunk_count += 1
                                all_responses.append(data)  # 保存完整响应
                                
                                # 显示响应内容
                                response_type = data.get("type", "unknown")
                                content = data.get("content", "")
                                message_id = data.get("message_id", "")
                                timestamp = data.get("timestamp", "")
                                
                                print(f"\n[Chunk {chunk_count}]")
                                print(f"   Type: {response_type}")
                                print(f"   Message ID: {message_id}")
                                if timestamp:
                                    print(f"   Timestamp: {timestamp}")
                                
                                # 显示完整 JSON 数据
                                print(f"   完整数据:")
                                print(json.dumps(data, indent=4, ensure_ascii=False))
                                
                            except json.JSONDecodeError as e:
                                print(f"   ⚠️  JSON 解析失败: {data_str}")
                                print(f"   原始数据: {line[:200]}")
                        else:
                            print(f"   ⚠️  非标准 SSE 格式: {line}")
                    
                    # 显示所有响应的摘要
                    print("\n" + "=" * 60)
                    print("📊 响应摘要")
                    print("=" * 60)
                    print(f"总响应数: {chunk_count}")
                    print(f"\n所有响应类型统计:")
                    type_counts = {}
                    for resp in all_responses:
                        resp_type = resp.get("type", "unknown")
                        type_counts[resp_type] = type_counts.get(resp_type, 0) + 1
                    for resp_type, count in type_counts.items():
                        print(f"   {resp_type}: {count}")
                    
                    print(f"\n完整响应列表:")
                    print(json.dumps(all_responses, indent=2, ensure_ascii=False))
                    
                    print("-" * 60)
                    print(f"\n✅ 测试完成，共收到 {chunk_count} 个响应块")
                else:
                    print(f"❌ 请求失败，状态码: {response.status_code}")
                    error_text = await response.aread()
                    print(f"   错误内容: {error_text.decode('utf-8', errors='ignore')}")
                    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_chat_with_shortcut(session_id: str):
    """测试带快捷指令的消息"""
    print("\n" + "=" * 60)
    print("💬 测试 Chat 接口 - 文本 + 快捷指令")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 准备请求数据
            request_data = {
                "content": [
                    {
                        "type": "text",
                        "text": "请帮我创建一个人脉,标题为:嘉华集团,描述为:这是一个测试人脉,公司为:嘉华集团,职位为:董事长,电话为:13800138013,邮箱为:zhangsan@gmail.com,微信为:zhangsan,地址为:北京市海淀区"
                    },
                    {
                        "type": "shortcut",
                        "shortcut": {
                            "shortcut": "新建人脉"
                        }
                    }
                ]
            }
            
            print(f"\n📤 发送请求:")
            print(f"   URL: {API_BASE_URL}/api/v1/chat")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            # 发送 POST 请求（流式响应）
            async with client.stream(
                "POST",
                f"{API_BASE_URL}/api/v1/chat",
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-Id": session_id,
                    "X-App-Id": "test-app",
                    "X-App-Version": "1.0.0",
                    "X-Device-Id": "test-device-002",
                    "X-OS-Type": "Android",
                    "X-OS-Version": "14.0",
                }
            ) as response:
                print(f"\n📥 响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"\n📨 流式响应内容:")
                    print("-" * 60)
                    
                    chunk_count = 0
                    all_responses = []  # 保存所有响应
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                chunk_count += 1
                                all_responses.append(data)  # 保存完整响应
                                
                                response_type = data.get("type", "unknown")
                                print(f"\n[Chunk {chunk_count}]")
                                print(f"   完整数据:")
                                print(json.dumps(data, indent=4, ensure_ascii=False))
                                
                            except json.JSONDecodeError as e:
                                print(f"   ⚠️  JSON 解析失败: {data_str}")
                                print(f"   原始数据: {line[:200]}")
                    
                    # 显示所有响应的摘要
                    print("\n" + "=" * 60)
                    print("📊 响应摘要")
                    print("=" * 60)
                    print(f"总响应数: {chunk_count}")
                    print(f"\n完整响应列表:")
                    print(json.dumps(all_responses, indent=2, ensure_ascii=False))
                    
                    print("-" * 60)
                    print(f"\n✅ 测试完成，共收到 {chunk_count} 个响应块")
                else:
                    print(f"❌ 请求失败，状态码: {response.status_code}")
                    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_chat_with_image_url(session_id: str):
    """测试带图片URL的消息（使用HTTP URL）"""
    print("\n" + "=" * 60)
    print("💬 测试 Chat 接口 - 文本 + 图片URL")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 准备请求数据（使用示例图片URL）
            request_data = {
                "content": [
                    {
                        "type": "text",
                        "text": "请分析这张图片"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://via.placeholder.com/300x200.jpg"
                        }
                    }
                ]
            }
            
            print(f"\n📤 发送请求:")
            print(f"   URL: {API_BASE_URL}/api/v1/chat")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
            
            # 发送 POST 请求（流式响应）
            async with client.stream(
                "POST",
                f"{API_BASE_URL}/api/v1/chat",
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-Id": session_id,
                    "X-App-Id": "test-app",
                    "X-App-Version": "1.0.0",
                }
            ) as response:
                print(f"\n📥 响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"\n📨 流式响应内容:")
                    print("-" * 60)
                    
                    chunk_count = 0
                    all_responses = []  # 保存所有响应
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                chunk_count += 1
                                all_responses.append(data)  # 保存完整响应
                                
                                print(f"\n[Chunk {chunk_count}]")
                                print(f"   完整数据:")
                                print(json.dumps(data, indent=4, ensure_ascii=False))
                                
                            except json.JSONDecodeError as e:
                                print(f"   ⚠️  JSON 解析失败: {data_str}")
                                print(f"   原始数据: {line[:200]}")
                    
                    # 显示所有响应的摘要
                    print("\n" + "=" * 60)
                    print("📊 响应摘要")
                    print("=" * 60)
                    print(f"总响应数: {chunk_count}")
                    print(f"\n完整响应列表:")
                    print(json.dumps(all_responses, indent=2, ensure_ascii=False))
                    
                    print("-" * 60)
                    print(f"\n✅ 测试完成，共收到 {chunk_count} 个响应块")
                else:
                    print(f"❌ 请求失败，状态码: {response.status_code}")
                    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_chat_with_parent_message(session_id: str):
    """测试引用消息的对话"""
    print("\n" + "=" * 60)
    print("💬 测试 Chat 接口 - 引用消息")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # 先发送第一条消息
            print("\n📤 发送第一条消息...")
            first_request = {
                "content": "明天下午3点开会"
            }
            
            first_message_id = None
            async with client.stream(
                "POST",
                f"{API_BASE_URL}/api/v1/chat",
                json=first_request,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-Id": session_id,
                }
            ) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                msg_id = data.get("message_id")
                                if msg_id and not first_message_id:
                                    first_message_id = msg_id
                                    print(f"   第一条消息 ID: {first_message_id}")
                                    break
                            except json.JSONDecodeError:
                                pass
            
            if first_message_id:
                # 等待一下，确保第一条消息处理完成
                await asyncio.sleep(2)
                
                # 发送引用第一条消息的第二条消息
                print(f"\n📤 发送引用消息（parent_message_id: {first_message_id})...")
                second_request = {
                    "content": "请修改时间到下午4点",
                    "parent_message_id": first_message_id
                }
                
                async with client.stream(
                    "POST",
                    f"{API_BASE_URL}/api/v1/chat",
                    json=second_request,
                    headers={
                        "Content-Type": "application/json",
                        "X-Session-Id": session_id,
                    }
                ) as response:
                    print(f"\n📥 响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        chunk_count = 0
                        all_responses = []  # 保存所有响应
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                try:
                                    data = json.loads(data_str)
                                    chunk_count += 1
                                    all_responses.append(data)  # 保存完整响应
                                    
                                    print(f"\n[Chunk {chunk_count}]")
                                    print(f"   完整数据:")
                                    print(json.dumps(data, indent=4, ensure_ascii=False))
                                    
                                except json.JSONDecodeError as e:
                                    print(f"   ⚠️  JSON 解析失败: {data_str}")
                                    print(f"   原始数据: {line[:200]}")
                        
                        # 显示所有响应的摘要
                        print("\n" + "=" * 60)
                        print("📊 响应摘要")
                        print("=" * 60)
                        print(f"总响应数: {chunk_count}")
                        print(f"\n完整响应列表:")
                        print(json.dumps(all_responses, indent=2, ensure_ascii=False))
                        
                        print(f"\n✅ 测试完成，共收到 {chunk_count} 个响应块")
                    else:
                        print(f"❌ 请求失败，状态码: {response.status_code}")
            else:
                print("⚠️  无法获取第一条消息 ID，跳过引用消息测试")
                
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🚀 Chat API 接口测试")
    print("=" * 60)
    
    # 获取测试 session
    session_id, user_id = await get_test_session()
    
    if not session_id:
        print("\n⚠️  无法获取测试 session，请手动提供")
        session_id = input("请输入 session_id (或按 Enter 跳过): ").strip()
        if not session_id:
            print("❌ 未提供 session_id，退出测试")
            return
    
    # 运行测试
    # await test_chat_text_only(session_id)
    # await asyncio.sleep(1)
    
    await test_chat_with_shortcut(session_id)
    await asyncio.sleep(1)
    
    # await test_chat_with_image_url(session_id)
    # await asyncio.sleep(1)
    
    # await test_chat_with_parent_message(session_id)
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
