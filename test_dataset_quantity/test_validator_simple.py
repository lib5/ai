#!/usr/bin/env python3
"""
简化版测试结果验证脚本
只验证前3个测试用例，快速测试功能
"""

import json
import asyncio
import aiohttp
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.append('/home/libo/chatapi')
from config import settings


async def validate_test_case(validator, test_case):
    """验证单个测试用例"""
    test_case_id = test_case.get('test_case_id', 'unknown')
    user_input = test_case.get('turn_results', [{}])[0].get('user_input', {})
    execution_result = test_case.get('turn_results', [{}])[0].get('execution_result', {})
    expected_behavior = test_case.get('expected_behavior', {})

    # 构建简化版验证提示词
    prompt = f"""
测试ID: {test_case_id}
用户输入: {user_input.get('content', '') if user_input.get('type') == 'text' else user_input.get('content', '')}

请判断以下测试用例的执行结果是否正确：
1. 工具选择是否正确？
2. 参数提取是否准确？
3. 整体业务逻辑是否正确？

请以JSON格式返回结果：
{{
  "is_correct": "正确/错误/部分正确",
  "score": 1-10分,
  "issues": ["问题1", "问题2"],
  "reasoning": "详细分析"
}}
"""

    try:
        # 调用Azure OpenAI API
        async with validator.session.post(
            f"{validator.base_url}/chat/completions?api-version={validator.api_version}",
            headers={
                "Authorization": f"Bearer {validator.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": validator.model,
                "messages": [
                    {"role": "system", "content": "你是专业的测试验证专家"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            timeout=30
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"API调用失败: {response.status} - {error_text}")

            result = await response.json()
            validation_text = result['choices'][0]['message']['content']

            # 尝试解析JSON
            try:
                validation_data = json.loads(validation_text)
                return {
                    'test_case_id': test_case_id,
                    'is_correct': validation_data.get('is_correct', 'unknown'),
                    'score': validation_data.get('score', 0),
                    'issues': validation_data.get('issues', []),
                    'reasoning': validation_data.get('reasoning', ''),
                    'status': 'success'
                }
            except json.JSONDecodeError:
                return {
                    'test_case_id': test_case_id,
                    'is_correct': 'unknown',
                    'score': 0,
                    'issues': ['无法解析验证结果'],
                    'reasoning': validation_text,
                    'status': 'failed'
                }

    except Exception as e:
        return {
            'test_case_id': test_case_id,
            'is_correct': 'error',
            'score': 0,
            'issues': [f'验证失败: {str(e)}'],
            'reasoning': '',
            'status': 'failed'
        }


async def main():
    """主函数"""
    print("="*60)
    print("简化版测试结果验证工具")
    print("="*60)

    # 检查配置
    if not settings.azure_api_key:
        print("错误: Azure OpenAI API密钥未配置")
        return

    if not settings.azure_endpoint:
        print("错误: Azure OpenAI端点未配置")
        return

    print(f"使用Azure OpenAI配置:")
    print(f"  端点: {settings.azure_endpoint}")
    print(f"  模型: {settings.azure_deployment_name}")
    print(f"  API版本: {settings.azure_api_version}")
    print()

    # 读取测试文件
    test_file = "test_dataset_quantity/test_results_intermediate_20260113_203830.json"

    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        print(f"错误: 测试文件不存在: {test_file}")
        return
    except Exception as e:
        print(f"错误: 读取测试文件失败: {e}")
        return

    print(f"读取到 {len(test_cases)} 个测试用例")
    print(f"将验证前 3 个测试用例")
    print()

    # 只取前3个测试用例
    test_cases_to_validate = test_cases[:3]

    # 创建验证器
    validator = type('Validator', (), {
        'api_key': settings.azure_api_key,
        'base_url': f"{settings.azure_endpoint}/openai/deployments/{settings.azure_deployment_name}",
        'model': settings.azure_deployment_name,
        'api_version': settings.azure_api_version,
        'session': aiohttp.ClientSession()
    })()

    results = []

    try:
        async with aiohttp.ClientSession() as session:
            validator.session = session

            for i, test_case in enumerate(test_cases_to_validate):
                print(f"正在验证第 {i+1}/{len(test_cases_to_validate)} 个: {test_case.get('test_case_id')}")

                result = await validate_test_case(validator, test_case)
                results.append(result)

                print(f"  结果: {result['is_correct']}, 评分: {result['score']}/10")
                if result['issues']:
                    print(f"  问题: {', '.join(result['issues'][:2])}")
                print()

    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

    # 打印摘要
    print("="*60)
    print("验证摘要")
    print("="*60)

    total = len(results)
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = total - successful

    print(f"总测试用例数: {total}")
    print(f"验证成功: {successful}")
    print(f"验证失败: {failed}")

    if successful > 0:
        correct = sum(1 for r in results if r['is_correct'] == '正确')
        partial = sum(1 for r in results if r['is_correct'] == '部分正确')
        wrong = sum(1 for r in results if r['is_correct'] == '错误')

        print(f"  正确: {correct}")
        print(f"  部分正确: {partial}")
        print(f"  错误: {wrong}")

        avg_score = sum(r['score'] for r in results if r['status'] == 'success') / successful
        print(f"平均评分: {avg_score:.2f}/10")

    print()
    print("详细结果:")

    for result in results:
        print(f"\n{result['test_case_id']}:")
        print(f"  正确性: {result['is_correct']}")
        print(f"  评分: {result['score']}/10")
        if result['issues']:
            print(f"  问题: {'; '.join(result['issues'])}")
        if result['reasoning']:
            print(f"  推理: {result['reasoning'][:100]}...")

    print("\n" + "="*60)


if __name__ == '__main__':
    asyncio.run(main())
