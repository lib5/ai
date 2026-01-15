#!/usr/bin/env python3
"""
测试前两个测试用例
确保每个测试用例都使用不同的user_id
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
        test_phone = "13800138013"
        test_code = "123456"

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
                print(f"✅ 创建会话成功")
                print(f"   Session ID: {session_id}")
                print(f"   User ID: {user_id}")
                return session_id, user_id
            else:
                print(f"❌ 登录失败: {response.status_code} - {response.text}")
                return None, None
    except Exception as e:
        print(f"⚠️ 无法创建会话: {str(e)}")
        return None, None


def convert_test_case_to_api_request(test_case, unique_user_id):
    """将测试用例转换为API请求格式（使用唯一的user_id）"""
    user_input = test_case['conversation']['turns'][0]['user_input']
    query_type = user_input['type']
    content = user_input['content']

    print(f"\n转换测试用例: {test_case['id']}")
    print(f"   查询类型: {query_type}")
    print(f"   内容: {content[:80]}...")
    print(f"   使用user_id: {unique_user_id}")

    # 构建请求数据
    if query_type == 'text':
        # 纯文本
        request_data = {
            "user_id": unique_user_id,  # 使用唯一的user_id
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


async def execute_api_test(session_id, request_data, test_case):
    """执行API测试"""
    print(f"\n{'='*80}")
    print(f"🚀 执行测试: {test_case['id']}")
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

                                print(f"\n[Chunk {chunk_count}]")
                                print(f"   Type: {data.get('type', 'unknown')}")
                                if 'content' in data:
                                    print(f"   Content: {data['content'][:100]}...")
                                if 'data' in data:
                                    print(f"   Data Keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else 'N/A'}")

                            except json.JSONDecodeError:
                                print(f"   ⚠️ JSON解析失败: {data_str[:100]}")

                    print("\n" + "="*80)
                    print(f"✅ 测试完成，共收到 {chunk_count} 个响应块")
                    print("="*80)

                    return {
                        "status": "success",
                        "chunks_count": chunk_count,
                        "responses": all_responses
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
    print("🧪 测试前两个测试用例")
    print("="*80)

    # 加载测试用例
    print("\n📖 加载测试数据...")
    with open('/home/libo/chatapi/test_dataset/final_cast.json', 'r', encoding='utf-8') as f:
        test_cases = json.load(f)

    # 取前两个测试用例
    test_cases = test_cases[:2]
    print(f"   加载了 {len(test_cases)} 个测试用例")

    # 创建会话
    print("\n🔐 创建测试会话...")
    session_id, user_id = await create_test_session()

    if not session_id:
        print("❌ 无法创建会话，退出测试")
        return

    # 执行测试
    results = []
    used_user_ids = set()  # 记录已使用的user_id

    for i, test_case in enumerate(test_cases):
        print(f"\n\n{'#'*80}")
        print(f"第 {i+1}/{len(test_cases)} 个测试")
        print(f"{'#'*80}")

        # 为每个测试用例生成唯一的user_id
        unique_user_id = generate_unique_user_id(i)
        print(f"\n✅ 为测试用例 {test_case['id']} 生成唯一user_id: {unique_user_id}")

        # 确保user_id唯一
        while unique_user_id in used_user_ids:
            unique_user_id = generate_unique_user_id(i)
        used_user_ids.add(unique_user_id)

        # 转换测试用例（传递唯一user_id）
        request_data = convert_test_case_to_api_request(test_case, unique_user_id)
        if not request_data:
            print(f"❌ 转换失败，跳过")
            results.append({
                "test_case_id": test_case['id'],
                "status": "conversion_failed"
            })
            continue

        # 执行API测试
        execution_result = await execute_api_test(session_id, request_data, test_case)

        # 保存结果
        result_data = {
            "test_case_id": test_case['id'],
            "original_user_id": test_case['user_id'],
            "execution_user_id": unique_user_id,
            "execution_result": execution_result,
            "expected_behavior": test_case['conversation']['turns'][0]['expected_behavior'],
            "timestamp": datetime.now().isoformat()
        }

        results.append(result_data)

        print(f"\n📝 测试 {test_case['id']} 完成，user_id: {unique_user_id}")

    # 保存结果到文件
    output_file = f"/home/libo/chatapi/test_dataset/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n\n" + "="*80)
    print("📊 测试完成")
    print("="*80)
    print(f"总测试数: {len(results)}")
    print(f"成功: {sum(1 for r in results if r['execution_result']['status'] == 'success')}")
    print(f"失败: {sum(1 for r in results if r['execution_result']['status'] != 'success')}")

    print(f"\n使用的user_id列表:")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result['test_case_id']} -> {result['execution_user_id']}")

    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
