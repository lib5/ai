#!/usr/bin/env python3
"""
并行测试版本 - 基于数据隔离的并行执行
保证缩短时间的同时，数据不会相互污染

核心思路：
1. 利用final_cast.json中的user_id进行天然数据隔离
2. 使用asyncio.Semaphore控制并发数量
3. 并行执行独立的测试用例，但每个测试用例内的多轮对话仍串行执行
4. 保留环境清理和验证机制
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
import threading

import httpx

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 获取当前脚本所在目录作为基础路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR

# API配置
API_BASE_URL = os.getenv("TEST_BASE_URL", "http://192.168.106.108:28000")
print(f"API_BASE_URL: {API_BASE_URL}")


class SemaphoreManager:
    """信号量管理器 - 控制并发数量"""
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent

    async def acquire(self):
        """获取执行权限"""
        await self.semaphore.acquire()

    def release(self):
        """释放执行权限"""
        self.semaphore.release()


class TestResultCollector:
    """测试结果收集器 - 线程安全的结果收集"""
    def __init__(self):
        self.results = []
        self.lock = threading.Lock()

    def add_result(self, result):
        """添加结果（线程安全）"""
        with self.lock:
            self.results.append(result)

    def get_results(self):
        """获取所有结果"""
        with self.lock:
            return self.results.copy()


def load_image_as_base64(image_path):
    """将图片转换为base64格式（保持原有逻辑）"""
    try:
        filename = os.path.basename(image_path)

        if filename.startswith('images'):
            filename = filename[6:]
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

        path_str = str(correct_path).lower()
        if path_str.endswith('.png'):
            content_type = 'image/png'
        elif path_str.endswith('.jpg') or path_str.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif path_str.endswith('.gif'):
            content_type = 'image/gif'
        else:
            content_type = 'image/jpeg'

        image_base64 = base64.b64encode(image_data).decode('utf-8')
        return f"data:{content_type};base64,{image_base64}"

    except Exception as e:
        print(f"❌ 图片读取失败: {e}")
        return None


async def create_test_session():
    """创建测试会话（保持原有逻辑）"""
    try:
        test_phone = "13800138123"
        test_code = "123456"

        async with httpx.AsyncClient(timeout=30.0) as client:
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
    """清理用户数据（保持原有逻辑）"""
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


async def verify_data_cleared(session_id, user_id, max_retries=3):
    """验证数据是否真正被清空（保持原有逻辑）"""
    print(f"\n🔍 验证数据清空效果...")

    for attempt in range(max_retries):
        try:
            await asyncio.sleep(2)
            print(f"   验证轮次: {attempt + 1}/{max_retries}")
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
                try:
                    response = await client.get(
                        f"{API_BASE_URL}/api/v1/chat/history",
                        params={"page": 1, "page_size": 10},
                        headers={
                            "X-Session-Id": session_id,
                            "Content-Type": "application/json"
                        }
                    )

                    if response.status_code == 200:
                        messages = response.json().get("data", {}).get("messages", [])
                        if len(messages) > 0:
                            print(f"   ⚠️ 发现 {len(messages)} 条聊天消息")
                            is_empty = False
                        else:
                            print(f"   ✅ 聊天历史为空")
                except Exception as e:
                    print(f"   ❌ 检查聊天历史异常: {str(e)}")
                    is_empty = False

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

        if attempt < max_retries - 1:
            print(f"   ⏳ 验证失败，{attempt + 1}/{max_retries}，等待3秒后重试...")
            await asyncio.sleep(3)

    print(f"   ❌ 验证失败: 数据可能未被完全清空")
    return False


async def delete_all_user_data_with_verification(session_id, user_id):
    """带验证的用户数据清理（保持原有逻辑）"""
    print(f"\n🗑️ 开始清理用户数据（带验证）...")

    delete_success = await delete_all_user_data(session_id)

    if not delete_success:
        print(f"   ❌ 清空接口调用失败")
        return False

    verify_success = await verify_data_cleared(session_id, user_id)

    if verify_success:
        print(f"   ✅ 数据清理并验证成功")
        return True
    else:
        print(f"   ⚠️ 数据清理完成但验证失败")
        print(f"   💡 建议：检查清空接口是否正常工作")
        return False


def convert_turn_to_api_request(turn, test_user_id, turn_index):
    """将单个turn转换为API请求格式（保持原有逻辑）"""
    user_input = turn['user_input']
    query_type = user_input['type']
    content = user_input['content']

    print(f"   Turn {turn_index}: {query_type}")
    print(f"   内容: {content[:80]}...")

    if query_type == 'text':
        request_data = {
            "user_id": test_user_id,
            "content": content
        }
        print(f"   ✅ 转换为纯文本请求（使用final_cast.json中的user_id）")

    elif query_type == 'image':
        image_base64 = load_image_as_base64(content)
        if image_base64:
            request_data = {
                "user_id": test_user_id,
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
        print(f"❌ 不支持的查询类型: {query_type}")
        return None

    return request_data


async def execute_api_test(session_id, request_data, test_case, turn_index, max_retries=3):
    """执行API测试（优化超时和重试机制）"""
    trace_id = str(uuid.uuid4())

    for attempt in range(max_retries):
        try:
            print(f"\n📤 发送API请求 (尝试 {attempt + 1}/{max_retries})")
            print(f"   URL: {API_BASE_URL}/api/v1/chat")
            print(f"   使用final_cast.json中的user_id: {request_data.get('user_id')}")
            print(f"   Session ID: {session_id[:20] + '...' if session_id and len(session_id) > 20 else session_id}")
            print(f"   Trace ID: {trace_id}")

            # 使用更宽松的超时设置
            timeout = httpx.Timeout(
                connect=30.0,  # 连接超时30秒
                read=180.0,    # 读取超时180秒（原120秒）
                write=30.0,    # 写入超时30秒
                pool=60.0      # 连接池超时60秒
            )

            async with httpx.AsyncClient(timeout=timeout) as client:
                headers = {
                    "Content-Type": "application/json",
                    "X-App-Id": "test-app",
                    "X-App-Version": "1.0.0",
                    "X-Moly-Trace-Id": trace_id,
                }
                if session_id:
                    headers["X-Session-Id"] = session_id

                try:
                    async with client.stream(
                        "POST",
                        f"{API_BASE_URL}/api/v1/chat",
                        json=request_data,
                        headers=headers
                    ) as response:
                        print(f"\n📥 响应状态码: {response.status_code}")

                        if response.status_code == 200:
                            chunk_count = 0
                            all_responses = []
                            buffer = []  # 临时缓冲区

                            try:
                                async for line in response.aiter_lines():
                                    if not line.strip():
                                        continue

                                    if line.startswith("data: "):
                                        data_str = line[6:]
                                        buffer.append(data_str)

                                        # 处理数据
                                        if len(buffer) >= 1:
                                            try:
                                                data = json.loads(buffer[-1])
                                                chunk_count += 1
                                                all_responses.append(data)

                                                # 减少输出，只显示关键信息
                                                if chunk_count <= 2:
                                                    print(f"\n[Chunk {chunk_count}]")
                                                    print(f"   Type: {data.get('type', 'unknown')}")
                                                    if 'content' in data:
                                                        content = str(data['content'])[:50]
                                                        print(f"   Content: {content}...")

                                            except json.JSONDecodeError as e:
                                                if chunk_count <= 2:
                                                    print(f"   ⚠️ JSON解析失败: {data_str[:100]}")

                                # 检查响应完整性
                                response_types = [resp.get('type') for resp in all_responses]
                                has_tool_call = any(t in ['tool', 'tool_call'] for t in response_types)
                                has_finish = any('完成' in str(resp.get('content', '')) or 'complete' in str(resp.get('content', '')).lower() for resp in all_responses)

                                # 判断状态
                                if chunk_count < 3:  # 降低最小响应块要求
                                    status = "incomplete"
                                    print(f"\n⚠️  警告：响应可能不完整")
                                    print(f"   响应块数: {chunk_count} (预期: >=3)")
                                elif not has_tool_call:
                                    status = "incomplete"
                                    print(f"\n⚠️  警告：响应缺少工具调用")
                                else:
                                    status = "success"

                                # 解码arguments字段
                                for resp in all_responses:
                                    if resp.get('type') == 'tool' and 'content' in resp:
                                        content = resp['content']
                                        if 'arguments' in content and isinstance(content['arguments'], str):
                                            args_str = content['arguments']
                                            try:
                                                decoded_args = args_str.encode().decode('unicode_escape')
                                                content['arguments'] = decoded_args
                                            except Exception:
                                                pass

                                print("\n" + "="*60)
                                print(f"✅ 测试完成，共收到 {chunk_count} 个响应块")
                                print(f"   状态: {status}")
                                print(f"   Trace ID: {trace_id}")
                                print("="*60)

                                return {
                                    "status": status,
                                    "chunks_count": chunk_count,
                                    "raw_data": all_responses,
                                    "trace_id": trace_id,
                                    "response_analysis": {
                                        "has_tool_call": has_tool_call,
                                        "has_finish": has_finish,
                                        "response_types": response_types
                                    },
                                    "attempts": attempt + 1
                                }

                            except httpx.ReadTimeout:
                                print(f"\n⏰ 读取超时 (尝试 {attempt + 1}/{max_retries})")
                                # 如果不是最后一次尝试，等待后重试
                                if attempt < max_retries - 1:
                                    print(f"   等待5秒后重试...")
                                    await asyncio.sleep(5)
                                    continue
                                else:
                                    # 最后一次尝试失败
                                    return {
                                        "status": "timeout",
                                        "error": "ReadTimeout after all retries",
                                        "chunks_received": chunk_count,
                                        "trace_id": trace_id,
                                        "attempts": attempt + 1,
                                        "partial_data": all_responses if chunk_count > 0 else None
                                    }

                        else:
                            error_text = await response.aread()
                            print(f"❌ 请求失败: {response.status_code}")
                            print(f"   错误: {error_text.decode('utf-8', errors='ignore')}")
                            return {
                                "status": "failed",
                                "error": f"HTTP {response.status_code}",
                                "error_text": error_text.decode('utf-8', errors='ignore'),
                                "trace_id": trace_id,
                                "attempts": attempt + 1
                            }

                except httpx.ReadTimeout as e:
                    print(f"\n⏰ HTTPX读取超时: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"   等待5秒后重试...")
                        await asyncio.sleep(5)
                        continue
                    else:
                        return {
                            "status": "timeout",
                            "error": f"ReadTimeout: {str(e)}",
                            "trace_id": trace_id,
                            "attempts": attempt + 1
                        }

                except Exception as e:
                    print(f"\n❌ 请求异常: {str(e)}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "trace_id": trace_id,
                        "attempts": attempt + 1
                    }

        except Exception as e:
            print(f"\n❌ 测试异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"   等待5秒后重试...")
                await asyncio.sleep(5)
                continue
            else:
                return {
                    "status": "error",
                    "error": str(e),
                    "trace_id": trace_id,
                    "attempts": attempt + 1
                }

    # 如果所有重试都失败
    return {
        "status": "failed",
        "error": "All retry attempts failed",
        "trace_id": trace_id,
        "attempts": max_retries
    }


async def execute_single_test_case(test_case, test_index, total_cases, semaphore_manager, result_collector):
    """执行单个测试用例（在并发环境中）"""
    test_case_id = test_case['id']
    print(f"\n{'#'*80}")
    print(f"🚀 并行测试用例 {test_index + 1}/{total_cases}: {test_case_id}")
    print(f"{'#'*80}")

    # 获取并发控制权限
    await semaphore_manager.acquire()

    try:
        # 创建测试会话
        print(f"\n🔐 创建测试会话...")
        session_id = await create_test_session()

        if not session_id:
            result = {
                "test_case_id": test_case['id'],
                "test_mode": test_case.get('mode', 'single_turn'),
                "total_turns": len(test_case['conversation']['turns']),
                "original_user_id": test_case.get('user_id'),
                "execution_user_id": test_case.get('user_id'),
                "session_id": None,
                "cleanup_status": "failed",
                "turn_results": [],
                "timestamp": datetime.now().isoformat(),
                "error": "无法获取session_id"
            }
            result_collector.add_result(result)
            return

        # 使用final_cast.json中定义的user_id
        test_user_id = test_case.get('user_id')
        print(f"\n✅ 使用final_cast.json中的user_id: {test_user_id}")

        # 清理环境
        print(f"\n🧹 清理测试环境...")
        cleanup_success = await delete_all_user_data_with_verification(session_id, test_user_id)

        if not cleanup_success:
            print(f"❌ 环境清理失败，跳过测试用例 {test_case_id}")
            result = {
                "test_case_id": test_case['id'],
                "test_mode": test_case.get('mode', 'single_turn'),
                "total_turns": len(test_case['conversation']['turns']),
                "original_user_id": test_case.get('user_id'),
                "execution_user_id": test_user_id,
                "session_id": session_id,
                "cleanup_status": "failed",
                "turn_results": [],
                "timestamp": datetime.now().isoformat(),
                "error": "环境清理失败"
            }
            result_collector.add_result(result)
            return

        # 执行每个turn（串行执行）
        turns = test_case['conversation']['turns']
        test_mode = test_case.get('mode', 'single_turn')
        all_turn_results = []

        for turn_idx, turn in enumerate(turns):
            print(f"\n{'-'*80}")
            print(f"   Turn {turn_idx + 1}/{len(turns)} (测试用例: {test_case_id})")
            print(f"{'-'*80}")

            request_data = convert_turn_to_api_request(turn, test_user_id, turn_idx + 1)
            if not request_data:
                all_turn_results.append({
                    "turn_id": turn_idx + 1,
                    "status": "conversion_failed"
                })
                continue

            execution_result = await execute_api_test(session_id, request_data, test_case, turn_idx + 1, max_retries=3)

            turn_result = {
                "turn_id": turn_idx + 1,
                "user_input": turn.get('user_input', {}),
                "execution_result": execution_result,
                "expected_behavior": turn.get('expected_behavior', {}),
            }
            all_turn_results.append(turn_result)

            # 如果不是最后一个turn，等待一段时间
            if turn_idx < len(turns) - 1:
                await asyncio.sleep(1)  # 减少等待时间

        # 保存测试结果
        result_data = {
            "test_case_id": test_case['id'],
            "test_mode": test_mode,
            "total_turns": len(turns),
            "original_user_id": test_case['user_id'],
            "execution_user_id": test_user_id,
            "session_id": session_id,
            "turn_results": all_turn_results,
            "timestamp": datetime.now().isoformat(),
            "note": "并行执行：使用final_cast.json中的user_id确保数据隔离"
        }

        result_collector.add_result(result_data)
        print(f"\n✅ 测试用例 {test_case_id} 并行执行完成")

    finally:
        # 释放并发控制权限
        semaphore_manager.release()


async def run_parallel_tests(test_cases, max_concurrent=5):
    """运行并行测试"""
    print(f"\n🚀 开始并行测试")
    print(f"   总测试用例数: {len(test_cases)}")
    print(f"   最大并发数: {max_concurrent}")
    print(f"   并发策略: 基于user_id的数据隔离")

    # 创建信号量管理器
    semaphore_manager = SemaphoreManager(max_concurrent)

    # 创建结果收集器
    result_collector = TestResultCollector()

    # 创建所有测试任务
    tasks = []
    for i, test_case in enumerate(test_cases):
        task = execute_single_test_case(
            test_case, i, len(test_cases),
            semaphore_manager, result_collector
        )
        tasks.append(task)

    # 等待所有测试完成
    await asyncio.gather(*tasks)

    return result_collector.get_results()


async def main():
    """主函数"""
    start_time = time.time()
    start_datetime = datetime.now()

    parser = argparse.ArgumentParser(description='并行测试全部44个测试用例')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径')
    parser.add_argument('--input', '-i', type=str, default='raw_data/final_cast_v3-101.json', help='输入测试用例文件路径')
    parser.add_argument('--limit', '-l', type=int, help='限制测试用例数量')
    parser.add_argument('--concurrent', '-c', type=int, default=5, help='最大并发数 (默认: 5)')
    parser.add_argument('--timestamp', '-t', type=str, help='时间戳')
    args = parser.parse_args()

    # 创建输出目录
    output_dir = PROJECT_ROOT / "test_results_parallel"
    output_dir.mkdir(exist_ok=True)
    print(f"\n📁 输出目录: {output_dir}")

    print("\n" + "="*80)
    print("🧪 并行测试全部44个测试用例")
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
    print(f"   最大并发数: {args.concurrent}")

    # 运行并行测试
    results = await run_parallel_tests(test_cases, args.concurrent)

    # 保存结果
    timestamp = args.timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.output:
        output_file = args.output
    else:
        output_file = output_dir / f"test_results_parallel_{timestamp}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n\n" + "="*80)
    print("📊 并行测试完成")
    print("="*80)

    # 统计结果
    total_tests = len(results)
    cleanup_failed = sum(1 for r in results if r.get('cleanup_status') == 'failed')
    successful_tests = total_tests - cleanup_failed

    total_turns = sum(len(r['turn_results']) for r in results if 'cleanup_status' not in r or r['cleanup_status'] != 'failed')
    successful_turns = sum(1 for r in results for t in r['turn_results'] if 'execution_result' in t and t['execution_result'].get('status') == 'success')
    incomplete_turns = sum(1 for r in results for t in r['turn_results'] if 'execution_result' in t and t['execution_result'].get('status') == 'incomplete')
    failed_turns = sum(1 for r in results for t in r['turn_results'] if 'execution_result' in t and t['execution_result'].get('status') not in ['success', 'incomplete'])

    print(f"总测试数: {total_tests}")
    print(f"✅ 成功执行: {successful_tests} 个")
    print(f"❌ 清理失败: {cleanup_failed} 个")
    print(f"总轮数: {total_turns}")
    print(f"成功轮数: {successful_turns}")
    print(f"不完整轮数: {incomplete_turns}")
    print(f"失败轮数: {failed_turns}")

    # 执行时间统计
    end_time = time.time()
    end_datetime = datetime.now()
    execution_time = end_time - start_time

    print("\n" + "="*80)
    print("⏱️  并行执行时间统计")
    print("="*80)
    print(f"开始时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结束时间: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总执行时间: {execution_time:.2f}秒 ({execution_time/60:.2f}分钟)")
    print(f"并发数: {args.concurrent}")
    if successful_tests > 0:
        print(f"平均每个测试: {execution_time/successful_tests:.2f}秒")
    print("="*80)

    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
