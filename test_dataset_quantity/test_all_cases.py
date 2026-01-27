#!/usr/bin/env python3
"""
测试全部44个测试用例（包括17个单轮和27个多轮）
多轮对话按turn顺序执行，每个turn都调用API

版本 v4 修改内容:
- 修复数据隔离问题：使用final_cast.json中的user_id而非登录返回的user_id
- 创建会话时只获取session_id，忽略登录返回的user_id
- 确保每个测试用例使用final_cast.json中定义的唯一user_id
- 这样可以避免搜索到其他测试的历史数据，实现真正的数据隔离

版本 v3 修改内容:
- 每个测试用例获取新的session_id
- 使用final_cast.json中的user_id进行数据隔离
- 每次测试前调用delete-all-data接口清理数据
- 确保每条测试在空白环境中进行
"""
import asyncio
import json
import os
import sys
import time
import base64
import argparse
import uuid
from pathlib import Path
from datetime import datetime

import httpx

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 获取当前脚本所在目录作为基础路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR



# API配置

## 环境地址 开发环境28000  测试环境8000 
API_BASE_URL = os.getenv("TEST_BASE_URL", "http://192.168.106.108:8000")
print(f"API_BASE_URL: {API_BASE_URL}")


def load_image_as_base64(image_path):
    """将图片转换为base64格式"""
    try:
        # 提取文件名，不管输入路径是什么，都重定向到正确路径
        filename = os.path.basename(image_path)

        # 🔧 修复：处理错误的路径格式（images四点开会.png → 四点开会.png）
        if filename.startswith('images'):
            # 如果文件名以'images'开头，说明路径格式错误，需要移除'images'前缀
            filename = filename[6:]  # 移除'images'这6个字符
            # 如果移除后还以分隔符开头，再次移除
            if filename.startswith('/') or filename.startswith('\\'):
                filename = filename[1:]

        correct_path = PROJECT_ROOT / "images" / filename

        print(f"   原始路径: {image_path}")
        print(f"   尝试加载图片: {correct_path}")

        if not os.path.isfile(correct_path):
            print(f"❌ 图片文件不存在: {correct_path}")
            return None

        with open(correct_path, 'rb') as f:
            image_data = f.read()

        # 根据文件扩展名确定content_type
        path_str = str(correct_path).lower()
        if path_str.endswith('.png'):
            content_type = 'image/png'
        elif path_str.endswith('.jpg') or path_str.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif path_str.endswith('.gif'):
            content_type = 'image/gif'
        else:
            content_type = 'image/jpeg'

        # 转换为base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        return f"data:{content_type};base64,{image_base64}"

    except Exception as e:
        print(f"❌ 图片读取失败: {e}")
        return None


async def create_test_session():
    """创建测试会话 - 只获取session_id，忽略返回的user_id"""
    try:
        # 使用固定手机号进行登录
        test_phone = "13800138123"
        test_code = "123456"

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 先尝试登录接口
            try:
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
                    login_user_id = data.get("user_id")
                    print(f"✅ 创建会话成功")
                    print(f"   Phone: {test_phone}")
                    print(f"   Session ID: {session_id}")
                    print(f"   忽略登录返回的user_id: {login_user_id}")
                    print(f"   将使用final_cast.json中定义的user_id")

                    # 🔧 只返回session_id，不返回user_id
                    return session_id
                else:
                    print(f"⚠️ 登录接口不存在或失败: {response.status_code}")
                    return None
            except Exception as e:
                print(f"⚠️ 登录接口不存在: {str(e)}")
                return None
    except Exception as e:
        print(f"⚠️ 无法创建会话: {str(e)}")
        return None


async def delete_all_user_data(session_id):
    """清理用户数据 - 调用delete-all-data接口"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"\n🗑️ 清理用户数据")
            print(f"   URL: {API_BASE_URL}/api/v1/user/delete-all-data")

            response = await client.delete(
                f"{API_BASE_URL}/api/v1/user/delete-all-data",
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                }
            )

            print(f"   响应状态码: {response.status_code}")

            if response.status_code == 200:
                response_data = response.json()
                print(f"   ✅ 数据清理成功")
                data = response_data.get("data", {})
                deleted_counts = data.get("deleted_counts", {})
                total_deleted = data.get("total_deleted", 0)
                print(f"      - 聊天记录: {deleted_counts.get('chat_messages', 0)} 条")
                print(f"      - 日程: {deleted_counts.get('schedules', 0)} 条")
                print(f"      - 人脉: {deleted_counts.get('contacts', 0)} 条")
                print(f"      - 总计: {total_deleted} 条")
                return True
            else:
                print(f"   ⚠️ 数据清理失败: {response.status_code}")
                print(f"      响应: {response.text}")
                return False

    except Exception as e:
        print(f"   ⚠️ 数据清理异常: {str(e)}")
        return False


async def verify_data_exists(session_id, contact_id=None, schedule_id=None):
    """验证数据存在"""
    print(f"\n🔍 验证数据存在...")

    results = {
        "contacts": 0,
        "schedules": 0,
        "chat_messages": 0
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 验证联系人
            if contact_id:
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/contacts/{contact_id}",
                    headers={
                        "X-Session-Id": session_id,
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 200:
                    results["contacts"] = 1
                    print(f"   ✅ 联系人存在: {contact_id}")
                else:
                    print(f"   ⚠️ 联系人不存在: {contact_id}")

            # 验证日程
            if schedule_id:
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/schedules/{schedule_id}",
                    headers={
                        "X-Session-Id": session_id,
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 200:
                    results["schedules"] = 1
                    print(f"   ✅ 日程存在: {schedule_id}")
                else:
                    print(f"   ⚠️ 日程不存在: {schedule_id}")

            # 获取聊天历史（验证聊天消息）
            response = await client.get(
                f"{API_BASE_URL}/api/v1/chat/history_4_agent",
                params={"page": 1, "page_size": 10},
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                }
            )
            if response.status_code == 200:
                response_data = response.json()
                messages = response_data.get("data", {}).get("messages", [])
                results["chat_messages"] = len(messages)
                print(f"   ✅ 聊天消息数量: {len(messages)}")
            else:
                print(f"   ⚠️ 无法获取聊天历史")

        return results

    except Exception as e:
        print(f"   ❌ 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return results


async def verify_data_deleted(session_id, contact_id=None, schedule_id=None):
    """验证数据已被删除"""
    print(f"\n🔍 验证数据已被删除...")

    results = {
        "contacts": 0,
        "schedules": 0,
        "chat_messages": 0
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 验证联系人
            if contact_id:
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/contacts/{contact_id}",
                    headers={
                        "X-Session-Id": session_id,
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 404:
                    print(f"   ✅ 联系人已删除: {contact_id}")
                else:
                    results["contacts"] = 1
                    print(f"   ❌ 联系人仍然存在: {contact_id}")

            # 验证日程
            if schedule_id:
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/schedules/{schedule_id}",
                    headers={
                        "X-Session-Id": session_id,
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code == 404:
                    print(f"   ✅ 日程已删除: {schedule_id}")
                else:
                    results["schedules"] = 1
                    print(f"   ❌ 日程仍然存在: {schedule_id}")

            # 获取聊天历史（验证聊天消息）
            response = await client.get(
                f"{API_BASE_URL}/api/v1/chat/history",
                params={"page": 1, "page_size": 10},
                headers={
                    "X-Session-Id": session_id,
                    "Content-Type": "application/json"
                }
            )
            if response.status_code == 200:
                response_data = response.json()
                messages = response_data.get("data", {}).get("messages", [])
                results["chat_messages"] = len(messages)
                if len(messages) == 0:
                    print(f"   ✅ 聊天消息已全部删除")
                else:
                    print(f"   ⚠️ 仍有 {len(messages)} 条聊天消息")
            else:
                print(f"   ⚠️ 无法获取聊天历史")

        return results

    except Exception as e:
        print(f"   ❌ 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return results


async def verify_data_cleared(session_id, user_id, max_retries=3):
    """验证数据是否真正被清空 - 不创建测试数据，只检查现有数据"""
    print(f"\n🔍 验证数据清空效果...")

    for attempt in range(max_retries):
        try:
            # 等待清空操作完成
            await asyncio.sleep(2)

            print(f"   验证轮次: {attempt + 1}/{max_retries}")

            # 直接检查环境是否为空，不创建测试数据

            # 1. 验证环境是否为空
            print(f"\n   检查环境是否为空...")
            is_empty = True

            async with httpx.AsyncClient(timeout=30.0) as client:
                # 检查联系人列表
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/contacts",
                    params={"page": 1, "page_size": 10},
                    headers={
                        "X-Session-Id": session_id,
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code == 200:
                    contact_data = response.json().get("data", {})
                    contacts = contact_data.get("contacts", [])
                    if len(contacts) > 0:
                        print(f"   ⚠️ 发现 {len(contacts)} 条联系人记录")
                        is_empty = False
                    else:
                        print(f"   ✅ 联系人列表为空")

                # 检查日程列表
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/schedules",
                    params={"page": 1, "page_size": 10},
                    headers={
                        "X-Session-Id": session_id,
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code == 200:
                    schedule_data = response.json().get("data", {})
                    schedules = schedule_data.get("schedules", [])
                    if len(schedules) > 0:
                        print(f"   ⚠️ 发现 {len(schedules)} 条日程记录")
                        is_empty = False
                    else:
                        print(f"   ✅ 日程列表为空")

                # 检查聊天历史
                print(f"   正在检查聊天历史...")
                try:
                    response = await client.get(
                        f"{API_BASE_URL}/api/v1/chat/history",
                        params={"page": 1, "page_size": 10},
                        headers={
                            "X-Session-Id": session_id,
                            "Content-Type": "application/json"
                        }
                    )

                    print(f"     聊天历史API状态码: {response.status_code}")

                    if response.status_code == 200:
                        response_data = response.json()
                        messages = response_data.get("data", {}).get("messages", [])
                        if len(messages) > 0:
                            print(f"   ⚠️ 发现 {len(messages)} 条聊天消息")
                            is_empty = False
                        else:
                            print(f"   ✅ 聊天历史为空")
                    else:
                        print(f"   ⚠️ 获取聊天历史失败: {response.status_code}")
                        print(f"     响应: {response.text[:200]}")
                except Exception as e:
                    print(f"   ❌ 检查聊天历史异常: {str(e)}")
                    is_empty = False  # 如果检查失败，认为环境不干净

            # 判断环境是否为空
            print(f"\n   清空效果验证:")
            if is_empty:
                print(f"   ✅ 验证通过：环境干净，无数据残留")
                return True
            else:
                print(f"   ❌ 验证失败：环境中有数据残留")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                else:
                    return False

        except Exception as e:
            print(f"   ⚠️ 验证过程异常: {str(e)}")
            import traceback
            traceback.print_exc()

        if attempt < max_retries - 1:
            print(f"   ⏳ 验证失败，{attempt + 1}/{max_retries}，等待3秒后重试...")
            await asyncio.sleep(3)

    print(f"   ❌ 验证失败: 数据可能未被完全清空")
    return False


async def delete_all_user_data_with_verification(session_id, user_id):
    """带验证的用户数据清理"""
    print(f"\n🗑️ 开始清理用户数据（带验证）...")

    # 步骤1: 调用清空接口
    delete_success = await delete_all_user_data(session_id)

    if not delete_success:
        print(f"   ❌ 清空接口调用失败")
        return False

    # 步骤2: 验证清空效果
    verify_success = await verify_data_cleared(session_id, user_id)

    if verify_success:
        print(f"   ✅ 数据清理并验证成功")
        return True
    else:
        print(f"   ⚠️ 数据清理完成但验证失败")
        print(f"   💡 建议：检查清空接口是否正常工作")
        return False


def convert_turn_to_api_request(turn, test_user_id, turn_index):
    """将单个turn转换为API请求格式"""
    user_input = turn['user_input']
    query_type = user_input['type']
    content = user_input['content']

    print(f"   Turn {turn_index}: {query_type}")
    print(f"   内容: {content[:80]}...")

    # 构建请求数据
    if query_type == 'text':
        # 纯文本 - 使用final_cast.json中定义的user_id
        request_data = {
            "user_id": test_user_id,  # ✅ 来自final_cast.json，确保数据隔离
            "content": content
        }
        print(f"   ✅ 转换为纯文本请求（使用final_cast.json中的user_id）")

    elif query_type == 'image':
        # 图片处理 - 使用final_cast.json中定义的user_id
        image_base64 = load_image_as_base64(content)
        if image_base64:
            request_data = {
                "user_id": test_user_id,  # ✅ 来自final_cast.json，确保数据隔离
                "content": [
                    {
                        "type": "text",
                        "text": "请分析这张图片并执行相应操作"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_base64
                        }
                    }
                ]
            }
            print(f"   ✅ 转换为图片请求（使用final_cast.json中的user_id）")
        else:
            return None
    else:
        print(f"   ❌ 不支持的查询类型: {query_type}")
        return None

    return request_data


async def execute_api_test(session_id, request_data, test_case, turn_index):
    """执行API测试"""
    print(f"\n{'='*80}")
    print(f"🚀 执行测试: {test_case['id']} - Turn {turn_index}")
    print(f"{'='*80}")

    # 生成唯一的trace_id
    trace_id = str(uuid.uuid4())
    print(f"\n🔍 生成Trace ID: {trace_id}")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"\n📤 发送API请求")
            print(f"   URL: {API_BASE_URL}/api/v1/chat")
            print(f"   使用final_cast.json中的user_id: {request_data.get('user_id')}")
            print(f"   Session ID: {session_id[:20] + '...' if session_id and len(session_id) > 20 else session_id}")
            print(f"   Trace ID: {trace_id}")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)[:500]}...")

            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "X-App-Id": "test-app",
                "X-App-Version": "1.0.0",
                "X-Moly-Trace-Id": trace_id,  # 添加trace_id到请求头
            }
            if session_id:
                headers["X-Session-Id"] = session_id

            async with client.stream(
                "POST",
                f"{API_BASE_URL}/api/v1/chat",
                json=request_data,
                headers=headers
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

                                # 只显示前3个chunk的详细信息，避免输出过多
                                if chunk_count <= 3:
                                    print(f"\n[Chunk {chunk_count}]")
                                    print(f"   Type: {data.get('type', 'unknown')}")

                                    if 'content' in data:
                                        content = data['content']
                                        if isinstance(content, str):
                                            print(f"   Content: {content[:100]}...")
                                        else:
                                            print(f"   Content: {str(content)[:100]}...")

                                if 'data' in data and chunk_count == 1:
                                    data_info = data['data']
                                    if isinstance(data_info, dict):
                                        print(f"   Data Keys: {list(data_info.keys())}")

                            except json.JSONDecodeError:
                                if chunk_count <= 3:
                                    print(f"   ⚠️ JSON解析失败: {data_str[:100]}")

                    # 检查响应完整性
                    response_types = [resp.get('type') for resp in all_responses]
                    has_tool_call = any(t in ['tool', 'tool_call'] for t in response_types)
                    has_finish = any('完成' in str(resp.get('content', '')) or 'complete' in str(resp.get('content', '')).lower() for resp in all_responses)

                    # 判断状态
                    if chunk_count < 5 or not has_tool_call:
                        status = "incomplete"  # 响应不完整
                        print(f"\n⚠️  警告：响应可能不完整")
                        print(f"   响应块数: {chunk_count} (预期: >=5)")
                        print(f"   包含工具调用: {has_tool_call}")
                    else:
                        status = "success"

                    # 解码所有响应中的arguments字段
                    for resp in all_responses:
                        if resp.get('type') == 'tool' and 'content' in resp:
                            content = resp['content']
                            if 'arguments' in content and isinstance(content['arguments'], str):
                                args_str = content['arguments']
                                try:
                                    # 解码Unicode转义序列
                                    decoded_args = args_str.encode().decode('unicode_escape')
                                    content['arguments'] = decoded_args
                                except Exception:
                                    pass  # 如果解码失败，保持原值

                    print("\n" + "="*80)
                    print(f"✅ 测试完成，共收到 {chunk_count} 个响应块")
                    print(f"   状态: {status}")
                    print(f"   Trace ID: {trace_id}")
                    print("="*80)

                    return {
                        "status": status,
                        "chunks_count": chunk_count,
                        "raw_data": all_responses,
                        "trace_id": trace_id,  # 记录trace_id到结果中
                        "response_analysis": {
                            "has_tool_call": has_tool_call,
                            "has_finish": has_finish,
                            "response_types": response_types
                        }
                    }
                else:
                    error_text = await response.aread()
                    print(f"❌ 请求失败: {response.status_code}")
                    print(f"   错误: {error_text.decode('utf-8', errors='ignore')}")
                    print(f"   Trace ID: {trace_id}")
                    return {
                        "status": "failed",
                        "error": f"HTTP {response.status_code}",
                        "error_text": error_text.decode('utf-8', errors='ignore'),
                        "trace_id": trace_id  # 记录trace_id到结果中
                    }

    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        print(f"   Trace ID: {trace_id}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "trace_id": trace_id  # 记录trace_id到结果中
        }


async def main():
    """主函数"""
    # 记录开始时间
    start_time = time.time()
    start_datetime = datetime.now()

    parser = argparse.ArgumentParser(description='测试全部44个测试用例')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径 (可选，将自动生成)')
    parser.add_argument('--input', '-i', type=str, default='raw_data/final_cast_v3-101.json', help='输入测试用例文件路径 (默认: raw_data/final_cast_v2.json)')
    parser.add_argument('--limit', '-l', type=int, help='限制测试用例数量 (默认: 全部)')
    parser.add_argument('--timestamp', '-t', type=str, help='时间戳 (可选，用于生成文件名)')
    args = parser.parse_args()

    # 创建专用输出目录
    output_dir = PROJECT_ROOT / "test_results_single"
    output_dir.mkdir(exist_ok=True)
    print(f"\n📁 输出目录: {output_dir}")

    print("\n" + "="*80)
    print("🧪 测试全部44个测试用例（包括多轮对话）")
    print("="*80)

    # 加载测试用例
    print("\n📖 加载测试数据...")
    input_file = args.input if args.input.startswith('/') else PROJECT_ROOT / args.input
    with open(input_file, 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    # 限制测试用例数量
    if args.limit:
        test_cases = test_cases[:args.limit]
        print(f"   加载了 {len(test_cases)} 个测试用例（限制数量）")
    else:
        print(f"   加载了 {len(test_cases)} 个测试用例（全部）")

    # 分类统计
    single_turn = [t for t in test_cases if t.get('mode', 'single_turn') == 'single_turn']
    multi_turn = [t for t in test_cases if t.get('mode', 'single_turn') == 'multi_turn']

    print(f"   单轮测试: {len(single_turn)} 个")
    print(f"   多轮测试: {len(multi_turn)} 个")

    # 执行测试
    results = []

    for i, test_case in enumerate(test_cases):
        print(f"\n\n{'#'*80}")
        print(f"测试用例 {i+1}/{len(test_cases)}: {test_case['id']}")
        print(f"{'#'*80}")

        # 🔐 为每个测试用例创建新的session
        print(f"\n🔐 创建测试会话...")
        session_id = await create_test_session()

        if not session_id:
            print(f"❌ 无法获取session_id，跳过测试用例 {test_case['id']}")
            continue

        # ✅ 使用final_cast.json中定义的user_id进行数据隔离
        test_user_id = test_case.get('user_id')
        print(f"\n✅ 使用final_cast.json中的user_id: {test_user_id}")
        print(f"   这样做确保每个测试使用不同的user_id，实现数据隔离")

        # 获取所有turns
        turns = test_case['conversation']['turns']
        test_mode = test_case.get('mode', 'single_turn')

        print(f"\n📝 测试模式: {test_mode}")
        print(f"   总轮数: {len(turns)}")

        # 🗑️ 每次测试前清理数据，确保空白环境（带验证和重试）
        print(f"\n🧹 清理测试环境...")
        max_cleanup_retries = 3
        cleanup_success = False
        skip_test = False  # 添加跳过标志

        for retry_count in range(max_cleanup_retries):
            if retry_count > 0:
                print(f"\n   🔄 第 {retry_count} 次重试清理...")

            cleanup_success = await delete_all_user_data_with_verification(session_id, test_user_id)

            if cleanup_success:
                print(f"   ✅ 环境清理并验证成功，开始测试")
                break
            else:
                if retry_count < max_cleanup_retries - 1:
                    print(f"   ⚠️ 环境清理失败或验证失败，{max_cleanup_retries - retry_count - 1} 次重试机会剩余")
                    await asyncio.sleep(3)  # 等待3秒后重试
                else:
                    print(f"   ❌ 环境清理失败，已重试 {max_cleanup_retries} 次")
                    print(f"   💡 跳过测试用例 {test_case['id']}，避免污染环境")

                    # 保存失败结果并跳过此测试用例
                    results.append({
                        "test_case_id": test_case['id'],
                        "test_mode": test_mode,
                        "total_turns": len(turns),
                        "original_user_id": test_case['user_id'],
                        "execution_user_id": test_user_id,
                        "session_id": session_id,
                        "cleanup_status": "failed",
                        "turn_results": [],
                        "timestamp": datetime.now().isoformat(),
                        "error": "环境清理失败，跳过测试"
                    })
                    skip_test = True  # 设置跳过标志

        # 如果需要跳过此测试，进入下一个
        if skip_test:
            continue

        # 执行每个turn
        all_turn_results = []
        for turn_idx, turn in enumerate(turns):
            print(f"\n{'-'*80}")
            print(f"   Turn {turn_idx + 1}/{len(turns)}")
            print(f"{'-'*80}")

            # 转换turn为API请求
            request_data = convert_turn_to_api_request(turn, test_user_id, turn_idx + 1)
            if not request_data:
                print(f"❌ Turn {turn_idx + 1} 转换失败，跳过")
                all_turn_results.append({
                    "turn_id": turn_idx + 1,
                    "status": "conversion_failed"
                })
                continue

            # 执行API测试
            execution_result = await execute_api_test(session_id, request_data, test_case, turn_idx + 1)

            # 保存turn结果
            turn_result = {
                "turn_id": turn_idx + 1,
                "user_input": turn.get('user_input', {}),
                "execution_result": execution_result,
                "expected_behavior": turn.get('expected_behavior', {}),
            }
            all_turn_results.append(turn_result)

            # 如果不是最后一个turn，等待一段时间再执行下一个turn
            if turn_idx < len(turns) - 1:
                print(f"\n⏳ 等待2秒后执行下一个turn...")
                await asyncio.sleep(2)

        # 保存整个测试用例的结果
        result_data = {
            "test_case_id": test_case['id'],
            "test_mode": test_mode,
            "total_turns": len(turns),
            "original_user_id": test_case['user_id'],  # 来自final_cast.json
            "execution_user_id": test_user_id,        # 实际使用的user_id
            "session_id": session_id,
            "turn_results": all_turn_results,
            "timestamp": datetime.now().isoformat(),
            "note": "使用final_cast.json中的user_id确保数据隔离"
        }

        results.append(result_data)

        print(f"\n📝 测试用例 {test_case['id']} 完成")

        # 每执行完20个测试，保存一次中间结果
        if (i + 1) % 20 == 0:
            timestamp = args.timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
            intermediate_output_file = output_dir / f"test_results_intermediate_{timestamp}.json"
            with open(intermediate_output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 中间结果已保存到: {intermediate_output_file}")

    # 保存最终结果到文件
    timestamp = args.timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.output:
        output_file = args.output
    else:
        output_file = output_dir / f"test_results_all_44_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n\n" + "="*80)
    print("📊 所有44个测试完成")
    print("="*80)
    print(f"总测试数: {len(results)}")

    # 统计整体状态
    total_turns = sum(len(r['turn_results']) for r in results if 'cleanup_status' not in r or r['cleanup_status'] != 'failed')
    cleanup_failed = sum(1 for r in results if r.get('cleanup_status') == 'failed')

    successful_turns = sum(1 for r in results for t in r['turn_results'] if 'execution_result' in t and t['execution_result'].get('status') == 'success')
    incomplete_turns = sum(1 for r in results for t in r['turn_results'] if 'execution_result' in t and t['execution_result'].get('status') == 'incomplete')
    failed_turns = sum(1 for r in results for t in r['turn_results'] if 'execution_result' in t and t['execution_result'].get('status') not in ['success', 'incomplete'])

    print(f"✅ 成功执行测试: {len(results) - cleanup_failed} 个")
    print(f"❌ 清理失败跳过: {cleanup_failed} 个")
    print(f"总轮数: {total_turns}")
    print(f"成功轮数: {successful_turns}")
    print(f"不完整轮数: {incomplete_turns}")
    print(f"失败轮数: {failed_turns}")

    print(f"\n使用的user_id和session_id列表:")
    for i, result in enumerate(results):
        mode = result['test_mode']
        original_user_id = result.get('original_user_id', 'N/A')
        execution_user_id = result.get('execution_user_id', 'N/A')
        session_id = result.get('session_id', 'N/A')
        session_display = session_id[:20] + '...' if session_id and len(session_id) > 20 else session_id

        # 检查是否跳过
        if result.get('cleanup_status') == 'failed':
            print(f"  {i+1}. {result['test_case_id']} [{mode}] - ❌ 跳过")
            print(f"     跳过原因: {result.get('error', 'N/A')}")
        else:
            print(f"  {i+1}. {result['test_case_id']} [{mode}]")
            print(f"     Final-Cast User ID: {original_user_id}")
            print(f"     Execution User ID: {execution_user_id}")
            print(f"     Session ID: {session_display}")
            if original_user_id == execution_user_id:
                print(f"     ✅ 使用final_cast.json中的user_id，确保数据隔离")
            else:
                print(f"     ⚠️ user_id不匹配！")

    print(f"\n结果已保存到: {output_file}")

    # 分类统计
    print("\n" + "="*80)
    print("📊 分类统计")
    print("="*80)

    # 过滤掉清理失败的测试
    executed_results = [r for r in results if r.get('cleanup_status') != 'failed']
    single_turn_results = [r for r in executed_results if r['test_mode'] == 'single_turn']
    multi_turn_results = [r for r in executed_results if r['test_mode'] == 'multi_turn']

    # 显示跳过测试
    skipped_results = [r for r in results if r.get('cleanup_status') == 'failed']
    if skipped_results:
        print(f"\n❌ 跳过测试 ({len(skipped_results)} 个):")
        for result in skipped_results:
            print(f"  {result['test_case_id']}: {result.get('error', 'N/A')}")

    print(f"\n✅ 单轮测试 ({len(single_turn_results)} 个):")
    for result in single_turn_results:
        if result['turn_results'] and 'execution_result' in result['turn_results'][0]:
            status = result['turn_results'][0]['execution_result']['status']
        else:
            status = 'conversion_failed'
        print(f"  {result['test_case_id']}: {status}")

    print(f"\n✅ 多轮测试 ({len(multi_turn_results)} 个):")
    for result in multi_turn_results:
        turn_statuses = []
        for t in result['turn_results']:
            if 'execution_result' in t:
                turn_statuses.append(t['execution_result']['status'])
            else:
                turn_statuses.append('conversion_failed')
        print(f"  {result['test_case_id']}: {turn_statuses}")

    # 计算并显示执行时间
    end_time = time.time()
    end_datetime = datetime.now()
    execution_time = end_time - start_time

    print("\n" + "="*80)
    print("⏱️  执行时间统计")
    print("="*80)
    print(f"开始时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结束时间: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总执行时间: {execution_time:.2f}秒 ({execution_time/60:.2f}分钟)")

    executed_count = len(results) - cleanup_failed
    if executed_count > 0:
        print(f"平均每个测试: {execution_time/executed_count:.2f}秒 (基于{executed_count}个实际执行测试)")
    else:
        print(f"平均每个测试: N/A (没有测试被执行)")
    print("="*80)

    # 删除中间文件
    print("\n🧹 清理中间文件...")
    try:
        intermediate_files = list(output_dir.glob("test_results_intermediate_*.json"))
        for intermediate_file in intermediate_files:
            intermediate_file.unlink()
            print(f"  已删除: {intermediate_file.name}")
        print(f"✅ 共清理了 {len(intermediate_files)} 个中间文件")
    except Exception as e:
        print(f"⚠️ 清理中间文件时出错: {e}")

    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())