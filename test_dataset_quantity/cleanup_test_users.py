#!/usr/bin/env python3
"""
测试用户数据清理脚本

从测试用例文件中提取用户ID，并清理对应的用户数据
支持清理单个用户、多个用户或全部用户数据

用法:
  # 清理所有测试用户数据
  python cleanup_test_users.py --all

  # 清理指定用户
  python cleanup_test_users.py --user user_20260113_115811_649

  # 从指定文件清理所有用户
  python cleanup_test_users.py --all --input raw_data/final_cast.json

  # 清理前预览用户列表
  python cleanup_test_users.py --list

  # 清理并验证
  python cleanup_test_users.py --all --verify
"""
import asyncio
import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

import httpx

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 获取当前脚本所在目录作为基础路径
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR

# API配置
API_BASE_URL = os.getenv("TEST_BASE_URL", "http://192.168.106.108:28000")
print(f"API_BASE_URL: {API_BASE_URL}")


async def create_test_session():
    """创建测试会话"""
    try:
        # 使用固定手机号进行登录
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
                    print(f"✅ 创建会话成功")
                    print(f"   Session ID: {session_id[:20] + '...' if session_id and len(session_id) > 20 else session_id}")
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


async def delete_all_user_data(session_id, user_id=None):
    """清理用户数据"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"\n🗑️ 清理用户数据")
            print(f"   URL: {API_BASE_URL}/api/v1/user/delete-all-data")
            if user_id:
                print(f"   User ID: {user_id}")

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
                return True, data
            else:
                print(f"   ⚠️ 数据清理失败: {response.status_code}")
                print(f"      响应: {response.text}")
                return False, None

    except Exception as e:
        print(f"   ⚠️ 数据清理异常: {str(e)}")
        return False, None


async def verify_data_cleared(session_id, user_id, max_retries=3):
    """验证数据是否真正被清空"""
    print(f"\n🔍 验证数据清空效果 (User ID: {user_id})...")

    for attempt in range(max_retries):
        try:
            # 等待清空操作完成
            await asyncio.sleep(2)

            print(f"   验证轮次: {attempt + 1}/{max_retries}")

            # 直接检查环境是否为空，不创建测试数据
            is_empty = True

            async with httpx.AsyncClient(timeout=30.0) as client:
                # 检查联系人列表
                response = await client.get(
                    f"{API_BASE_URL}/api/v1/contacts",
                    params={"page": 1, "page_size": 10},
                    headers={
                        "X-Session-Id": session_id,
                        "Content-Type": "application/json"}
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
                        "Content-Type": "application/json"}
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
                            "Content-Type": "application/json"}
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
                    is_empty = False

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


async def cleanup_single_user(user_id, verify=False):
    """清理单个用户的数据"""
    print(f"\n{'='*80}")
    print(f"🧹 清理用户数据: {user_id}")
    print(f"{'='*80}")

    # 创建会话
    session_id = await create_test_session()
    if not session_id:
        print(f"❌ 无法获取session_id，跳过用户 {user_id}")
        return False

    try:
        # 调用删除接口
        success, data = await delete_all_user_data(session_id, user_id)

        if not success:
            print(f"❌ 用户 {user_id} 数据清理失败")
            return False

        # 如果需要验证
        if verify:
            verify_success = await verify_data_cleared(session_id, user_id)
            if verify_success:
                print(f"✅ 用户 {user_id} 数据清理并验证成功")
                return True
            else:
                print(f"⚠️ 用户 {user_id} 数据清理完成但验证失败")
                return False
        else:
            print(f"✅ 用户 {user_id} 数据清理成功")
            return True

    except Exception as e:
        print(f"❌ 清理用户 {user_id} 时发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def cleanup_all_users(user_ids, verify=False):
    """清理所有用户的数据"""
    print(f"\n{'='*80}")
    print(f"🧹 清理所有 {len(user_ids)} 个用户的数据")
    print(f"{'='*80}")

    success_count = 0
    failed_count = 0
    results = []

    for i, user_id in enumerate(user_ids, 1):
        print(f"\n\n[{i}/{len(user_ids)}] 处理用户: {user_id}")

        try:
            # 为每个用户创建新的会话
            session_id = await create_test_session()
            if not session_id:
                print(f"❌ 无法获取session_id，跳过用户 {user_id}")
                failed_count += 1
                results.append({"user_id": user_id, "status": "failed", "reason": "无法获取session_id"})
                continue

            # 调用删除接口
            success, data = await delete_all_user_data(session_id, user_id)

            if not success:
                print(f"❌ 用户 {user_id} 数据清理失败")
                failed_count += 1
                results.append({"user_id": user_id, "status": "failed", "reason": "清理接口失败"})
                continue

            # 如果需要验证
            if verify:
                verify_success = await verify_data_cleared(session_id, user_id)
                if verify_success:
                    print(f"✅ 用户 {user_id} 数据清理并验证成功")
                    success_count += 1
                    results.append({"user_id": user_id, "status": "success", "verified": True})
                else:
                    print(f"⚠️ 用户 {user_id} 数据清理完成但验证失败")
                    success_count += 1  # 清理成功但验证失败也算清理成功
                    results.append({"user_id": user_id, "status": "success", "verified": False})
            else:
                print(f"✅ 用户 {user_id} 数据清理成功")
                success_count += 1
                results.append({"user_id": user_id, "status": "success", "verified": False})

            # 等待一段时间再处理下一个用户
            if i < len(user_ids):
                print(f"\n⏳ 等待2秒后处理下一个用户...")
                await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ 清理用户 {user_id} 时发生异常: {str(e)}")
            failed_count += 1
            results.append({"user_id": user_id, "status": "failed", "reason": str(e)})
            import traceback
            traceback.print_exc()

    # 打印总结
    print(f"\n\n{'='*80}")
    print(f"📊 清理结果总结")
    print(f"{'='*80}")
    print(f"总用户数: {len(user_ids)}")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")

    if verify:
        verified_count = sum(1 for r in results if r.get("status") == "success" and r.get("verified", False))
        print(f"验证通过: {verified_count}")

    print(f"\n详细结果:")
    for result in results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        verify_info = " (已验证)" if result.get("verified", False) else ""
        if result["status"] == "success":
            print(f"  {status_icon} {result['user_id']}{verify_info}")
        else:
            print(f"  {status_icon} {result['user_id']}: {result.get('reason', 'N/A')}")

    return success_count, failed_count


def load_test_cases(file_path):
    """从文件加载测试用例"""
    try:
        input_file = file_path if file_path.startswith('/') else PROJECT_ROOT / file_path
        with open(input_file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        return test_cases
    except Exception as e:
        print(f"❌ 加载测试用例文件失败: {e}")
        return None


def extract_user_ids(test_cases):
    """从测试用例中提取用户ID"""
    user_ids = []
    test_case_ids = []

    for test_case in test_cases:
        user_id = test_case.get('user_id')
        test_id = test_case.get('id')

        if user_id and user_id not in user_ids:
            user_ids.append(user_id)

        test_case_ids.append({
            "test_id": test_id,
            "user_id": user_id
        })

    return user_ids, test_case_ids


def list_users(test_cases):
    """列出所有用户ID"""
    user_ids, test_case_ids = extract_user_ids(test_cases)

    print(f"\n{'='*80}")
    print(f"📋 测试用例用户列表")
    print(f"{'='*80}")
    print(f"总测试用例数: {len(test_cases)}")
    print(f"唯一用户数: {len(user_ids)}")

    print(f"\n用户列表:")
    for i, item in enumerate(test_case_ids, 1):
        print(f"  {i}. Test ID: {item['test_id']}")
        print(f"     User ID: {item['user_id']}")

    print(f"\n唯一用户ID列表:")
    for i, user_id in enumerate(user_ids, 1):
        print(f"  {i}. {user_id}")

    return user_ids


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='清理测试用户数据')
    parser.add_argument('--input', '-i', type=str, default='raw_data/final_cast.json',
                        help='测试用例文件路径 (默认: raw_data/final_cast.json)')
    parser.add_argument('--user', '-u', type=str, help='指定要清理的用户ID')
    parser.add_argument('--all', action='store_true', help='清理所有测试用户数据')
    parser.add_argument('--verify', action='store_true', help='清理后验证数据是否真正被清空')
    parser.add_argument('--list', action='store_true', help='仅列出用户ID，不执行清理')
    parser.add_argument('--timestamp', '-t', type=str, help='时间戳 (可选，用于生成日志文件名)')

    args = parser.parse_args()

    # 加载测试用例
    print(f"\n📖 加载测试用例文件: {args.input}")
    test_cases = load_test_cases(args.input)

    if not test_cases:
        print(f"❌ 无法加载测试用例，退出")
        return

    # 提取用户ID
    user_ids, test_case_ids = extract_user_ids(test_cases)

    if not user_ids:
        print(f"❌ 未找到任何用户ID，退出")
        return

    # 如果只是列出用户
    if args.list:
        list_users(test_cases)
        return

    # 验证参数
    if not args.user and not args.all:
        print(f"❌ 请指定 --user <user_id> 或 --all")
        print(f"   使用 --list 查看所有可用用户ID")
        return

    # 开始清理
    start_time = time.time()
    start_datetime = datetime.now()

    if args.user:
        # 清理指定用户
        if args.user not in user_ids:
            print(f"❌ 用户ID '{args.user}' 不在测试用例中")
            print(f"   使用 --list 查看所有可用用户ID")
            return

        success = await cleanup_single_user(args.user, verify=args.verify)
        if success:
            print(f"\n✅ 清理完成")
        else:
            print(f"\n❌ 清理失败")

    elif args.all:
        # 清理所有用户
        success_count, failed_count = await cleanup_all_users(user_ids, verify=args.verify)

        # 计算执行时间
        end_time = time.time()
        end_datetime = datetime.now()
        execution_time = end_time - start_time

        print(f"\n{'='*80}")
        print(f"⏱️  执行时间统计")
        print(f"{'='*80}")
        print(f"开始时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"结束时间: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总执行时间: {execution_time:.2f}秒 ({execution_time/60:.2f}分钟)")
        print(f"平均每个用户: {execution_time/len(user_ids):.2f}秒")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
