#!/usr/bin/env python3
"""
测试全部44个测试用例（包括17个单轮和27个多轮）
多轮对话按turn顺序执行，每个turn都调用API
"""
import asyncio
import json
import os
import sys
import base64
from pathlib import Path
from datetime import datetime

import httpx

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# API配置
API_BASE_URL = os.getenv("TEST_BASE_URL", "http://192.168.106.108:8000")
print(f"API_BASE_URL: {API_BASE_URL}")


def generate_unique_user_id(test_index):
    """为每个测试用例生成唯一的user_id"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    return f"test_user_{test_index:03d}_{timestamp}"


def load_image_as_base64(image_path):
    """将图片转换为base64格式"""
    try:
        if not os.path.isfile(image_path):
            print(f"❌ 图片文件不存在: {image_path}")
            return None

        with open(image_path, 'rb') as f:
            image_data = f.read()

        # 根据文件扩展名确定content_type
        if image_path.lower().endswith('.png'):
            content_type = 'image/png'
        elif image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif image_path.lower().endswith('.gif'):
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
    """创建测试会话"""
    try:
        # 尝试登录获取session_id
        test_phone = "13800138013"
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
                    user_id = data.get("user_id")
                    print(f"✅ 创建会话成功")
                    print(f"   Session ID: {session_id}")
                    print(f"   User ID: {user_id}")
                    return session_id, user_id
                else:
                    print(f"⚠️ 登录接口不存在或失败: {response.status_code}")
                    return None, None
            except Exception as e:
                print(f"⚠️ 登录接口不存在: {str(e)}")
                return None, None
    except Exception as e:
        print(f"⚠️ 无法创建会话: {str(e)}")
        return None, None


def convert_turn_to_api_request(turn, unique_user_id, turn_index):
    """将单个turn转换为API请求格式"""
    user_input = turn['user_input']
    query_type = user_input['type']
    content = user_input['content']

    print(f"   Turn {turn_index}: {query_type}")
    print(f"   内容: {content[:80]}...")

    # 构建请求数据
    if query_type == 'text':
        # 纯文本
        request_data = {
            "user_id": unique_user_id,
            "content": content
        }
        print(f"   ✅ 转换为纯文本请求")

    elif query_type == 'image':
        # 图片处理
        image_base64 = load_image_as_base64(content)
        if image_base64:
            request_data = {
                "user_id": unique_user_id,
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
            print(f"   ✅ 转换为图片请求")
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

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"\n📤 发送API请求")
            print(f"   URL: {API_BASE_URL}/api/v1/chat")
            print(f"   user_id: {request_data.get('user_id')}")
            print(f"   请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)[:500]}...")

            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "X-App-Id": "test-app",
                "X-App-Version": "1.0.0",
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
                    print("="*80)

                    return {
                        "status": status,
                        "chunks_count": chunk_count,
                        "raw_data": all_responses,
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
                    return {
                        "status": "failed",
                        "error": f"HTTP {response.status_code}",
                        "error_text": error_text.decode('utf-8', errors='ignore')
                    }

    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }


async def main():
    """主函数"""
    print("\n" + "="*80)
    print("🧪 测试全部44个测试用例（包括多轮对话）")
    print("="*80)

    # 加载测试用例
    print("\n📖 加载测试数据...")
    with open('/home/libo/chatapi/test_dataset/final_cast.json', 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    print(f"   加载了 {len(test_cases)} 个测试用例")

    # 分类统计
    single_turn = [t for t in test_cases if t.get('mode', 'single_turn') == 'single_turn']
    multi_turn = [t for t in test_cases if t.get('mode', 'single_turn') == 'multi_turn']

    print(f"   单轮测试: {len(single_turn)} 个")
    print(f"   多轮测试: {len(multi_turn)} 个")

    # 创建会话
    print("\n🔐 创建测试会话...")
    session_id, user_id = await create_test_session()

    if not session_id:
        print("ℹ️ 无session_id，继续测试（可能不需要认证）")

    # 执行测试
    results = []
    used_user_ids = set()  # 记录已使用的user_id

    for i, test_case in enumerate(test_cases):
        print(f"\n\n{'#'*80}")
        print(f"测试用例 {i+1}/{len(test_cases)}: {test_case['id']}")
        print(f"{'#'*80}")

        # 为每个测试用例生成唯一的user_id
        unique_user_id = generate_unique_user_id(i)
        print(f"\n✅ 生成唯一user_id: {unique_user_id}")

        # 确保user_id唯一
        while unique_user_id in used_user_ids:
            unique_user_id = generate_unique_user_id(i)
        used_user_ids.add(unique_user_id)

        # 获取所有turns
        turns = test_case['conversation']['turns']
        test_mode = test_case.get('mode', 'single_turn')

        print(f"\n📝 测试模式: {test_mode}")
        print(f"   总轮数: {len(turns)}")

        # 执行每个turn
        all_turn_results = []
        for turn_idx, turn in enumerate(turns):
            print(f"\n{'-'*80}")
            print(f"   Turn {turn_idx + 1}/{len(turns)}")
            print(f"{'-'*80}")

            # 转换turn为API请求
            request_data = convert_turn_to_api_request(turn, unique_user_id, turn_idx + 1)
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
            "original_user_id": test_case['user_id'],
            "execution_user_id": unique_user_id,
            "turn_results": all_turn_results,
            "timestamp": datetime.now().isoformat()
        }

        results.append(result_data)

        print(f"\n📝 测试用例 {test_case['id']} 完成")

        # 每执行完5个测试，保存一次中间结果
        if (i + 1) % 5 == 0:
            output_file = f"/home/libo/chatapi/test_dataset/test_results_intermediate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 中间结果已保存到: {output_file}")

    # 保存最终结果到文件
    output_file = f"/home/libo/chatapi/test_dataset/test_results_all_44_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n\n" + "="*80)
    print("📊 所有44个测试完成")
    print("="*80)
    print(f"总测试数: {len(results)}")

    # 统计整体状态
    total_turns = sum(len(r['turn_results']) for r in results)
    successful_turns = sum(1 for r in results for t in r['turn_results'] if t['execution_result']['status'] == 'success')
    incomplete_turns = sum(1 for r in results for t in r['turn_results'] if t['execution_result']['status'] == 'incomplete')
    failed_turns = sum(1 for r in results for t in r['turn_results'] if t['execution_result']['status'] not in ['success', 'incomplete'])

    print(f"总轮数: {total_turns}")
    print(f"成功轮数: {successful_turns}")
    print(f"不完整轮数: {incomplete_turns}")
    print(f"失败轮数: {failed_turns}")

    print(f"\n使用的user_id列表:")
    for i, result in enumerate(results):
        mode = result['test_mode']
        print(f"  {i+1}. {result['test_case_id']} [{mode}] -> {result['execution_user_id']}")

    print(f"\n结果已保存到: {output_file}")

    # 分类统计
    print("\n" + "="*80)
    print("📊 分类统计")
    print("="*80)

    single_turn_results = [r for r in results if r['test_mode'] == 'single_turn']
    multi_turn_results = [r for r in results if r['test_mode'] == 'multi_turn']

    print(f"\n单轮测试 ({len(single_turn_results)} 个):")
    for result in single_turn_results:
        status = result['turn_results'][0]['execution_result']['status'] if result['turn_results'] else 'unknown'
        print(f"  {result['test_case_id']}: {status}")

    print(f"\n多轮测试 ({len(multi_turn_results)} 个):")
    for result in multi_turn_results:
        turn_statuses = [t['execution_result']['status'] for t in result['turn_results']]
        print(f"  {result['test_case_id']}: {turn_statuses}")


if __name__ == "__main__":
    asyncio.run(main())