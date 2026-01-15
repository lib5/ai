#!/usr/bin/env python3
"""
测试结果验证脚本 - 最终版
使用Azure OpenAI GPT-4.1验证chat API测试结果的正确性
"""

import json
import asyncio
import aiohttp
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 加载.env文件
load_dotenv('/home/libo/chatapi/.env')

# 获取Azure OpenAI配置
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_API_KEY = os.getenv('AZURE_API_KEY') or os.getenv('AZURE_OPENAI_API_KEY')
AZURE_API_VERSION = os.getenv('AZURE_API_VERSION') or os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
DEPLOYMENT_NAME = os.getenv('AZURE_DEPLOYMENT_NAME') or os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1')

print("="*60)
print("测试结果验证工具 - 使用 Azure OpenAI GPT-4.1")
print("="*60)

print(f"使用Azure OpenAI配置:")
print(f"  端点: {AZURE_ENDPOINT}")
print(f"  模型: {DEPLOYMENT_NAME}")
print(f"  API版本: {AZURE_API_VERSION}")
print()


async def validate_single_case(session, test_case):
    """验证单个测试用例"""
    test_case_id = test_case.get('test_case_id', 'unknown')
    user_input = test_case.get('turn_results', [{}])[0].get('user_input', {})
    execution_result = test_case.get('turn_results', [{}])[0].get('execution_result', {})
    expected_behavior = test_case.get('expected_behavior', {})

    # 构建验证提示词
    if user_input.get('type') == 'text':
        input_display = f"文本输入: {user_input.get('content', '')}"
    elif user_input.get('type') == 'image':
        input_display = f"图像输入: {user_input.get('content', '')}"
    else:
        input_display = f"输入: {json.dumps(user_input, ensure_ascii=False, indent=2)}"

    # 格式化实际执行结果
    actual_tool_calls = []
    tool_results = []
    if 'raw_data' in execution_result:
        for item in execution_result['raw_data']:
            if item.get('type') == 'tool' or (item.get('role') == 'assistant' and item.get('type') == 'tool'):
                content = item.get('content', {})
                if content.get('status') == 'start':
                    actual_tool_calls.append({
                        'tool_name': content.get('name', ''),
                        'tool_cn': content.get('name_cn', ''),
                        'arguments': content.get('arguments', ''),
                    })
                elif content.get('status') == 'success':
                    tool_results.append({
                        'tool_name': content.get('name', ''),
                        'observation': content.get('observation', '')
                    })

    # 格式化期望行为
    expected_steps = expected_behavior.get('steps', [])

    prompt = f"""
你是一个专业的AI系统测试验证专家。请分析以下测试用例的执行结果，判断其正确性。

## 测试用例信息
测试ID: {test_case_id}
{input_display}

## 期望行为
期望执行步骤: {json.dumps(expected_steps, ensure_ascii=False, indent=2)}

## 实际执行结果
实际调用的工具: {json.dumps(actual_tool_calls, ensure_ascii=False, indent=2)}
工具执行结果: {json.dumps(tool_results, ensure_ascii=False, indent=2)}
执行状态: {execution_result.get('status', 'unknown')}

## 验证标准
请从以下维度评估（每项1-10分，10分最佳）：

1. **工具选择准确性**: 是否选择了正确的工具？
2. **参数提取准确性**: 工具参数是否准确反映了用户意图？
3. **数据处理合理性**: 数据格式转换、默认值处理等是否合理？
4. **业务逻辑正确性**: 对用户需求的理解和处理是否正确？
5. **响应完整性**: 返回的信息是否完整、准确？

## 判断标准
- **正确**: 工具选择正确，主要参数准确，业务逻辑正确
- **部分正确**: 工具选择正确，但有参数错误或细节问题
- **错误**: 工具选择错误或理解完全错误

请以JSON格式返回验证结果：
```json
{{
  "overall_score": 总分(1-10),
  "is_correct": "正确/错误/部分正确",
  "dimension_scores": {{
    "tool_selection": 工具选择分数,
    "parameter_accuracy": 参数准确性分数,
    "data_processing": 数据处理分数,
    "business_logic": 业务逻辑分数,
    "response_completeness": 响应完整性分数
  }},
  "key_issues": ["关键问题1", "关键问题2"],
  "suggestions": ["改进建议1", "改进建议2"],
  "detailed_analysis": "详细分析说明"
}}
```
"""

    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_API_VERSION}"

    headers = {
        "Authorization": f"Bearer {AZURE_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": DEPLOYMENT_NAME,
        "messages": [
            {"role": "system", "content": "你是一个专业的AI系统测试验证专家。你需要分析测试用例的执行结果，判断其正确性，并以JSON格式返回结果。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2000
    }

    try:
        async with session.post(url, headers=headers, json=data, timeout=60) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Azure OpenAI API调用失败: {response.status} - {error_text}")

            result = await response.json()
            validation_text = result['choices'][0]['message']['content']

            # 尝试解析JSON
            try:
                validation_data = json.loads(validation_text)
                return {
                    'test_case_id': test_case_id,
                    'is_correct': validation_data.get('is_correct', 'unknown'),
                    'score': validation_data.get('overall_score', 0),
                    'dimension_scores': validation_data.get('dimension_scores', {}),
                    'issues': validation_data.get('key_issues', []),
                    'suggestions': validation_data.get('suggestions', []),
                    'reasoning': validation_data.get('detailed_analysis', ''),
                    'status': 'success'
                }
            except json.JSONDecodeError:
                # 尝试从文本中提取JSON
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', validation_text, re.DOTALL)
                if json_match:
                    try:
                        validation_data = json.loads(json_match.group(1))
                        return {
                            'test_case_id': test_case_id,
                            'is_correct': validation_data.get('is_correct', 'unknown'),
                            'score': validation_data.get('overall_score', 0),
                            'dimension_scores': validation_data.get('dimension_scores', {}),
                            'issues': validation_data.get('key_issues', []),
                            'suggestions': validation_data.get('suggestions', []),
                            'reasoning': validation_data.get('detailed_analysis', ''),
                            'status': 'success'
                        }
                    except json.JSONDecodeError:
                        pass

                return {
                    'test_case_id': test_case_id,
                    'is_correct': 'unknown',
                    'score': 0,
                    'dimension_scores': {},
                    'issues': ['无法解析验证结果'],
                    'suggestions': [],
                    'reasoning': validation_text,
                    'status': 'failed'
                }

    except Exception as e:
        return {
            'test_case_id': test_case_id,
            'is_correct': 'error',
            'score': 0,
            'dimension_scores': {},
            'issues': [f'验证失败: {str(e)}'],
            'suggestions': [],
            'reasoning': '',
            'status': 'failed'
        }


async def main():
    """主函数"""
    # 确保输出目录存在
    import os
    os.makedirs("test_dataset_quantity/validation_reports", exist_ok=True)

    test_file = "test_dataset_quantity/test_results_intermediate_20260113_203830.json"

    # 读取测试文件
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
    print(f"将验证前 5 个测试用例")
    print()

    # 只取前5个测试用例进行测试
    test_cases_to_validate = test_cases[:5]

    results = []

    try:
        async with aiohttp.ClientSession() as session:
            for i, test_case in enumerate(test_cases_to_validate):
                print(f"正在验证第 {i+1}/{len(test_cases_to_validate)} 个: {test_case.get('test_case_id')}")

                result = await validate_single_case(session, test_case)
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
        if result['dimension_scores']:
            print(f"  维度分数: {result['dimension_scores']}")
        if result['issues']:
            print(f"  问题: {'; '.join(result['issues'])}")
        if result['reasoning']:
            print(f"  分析: {result['reasoning'][:100]}...")

    # 保存结果
    output_file = f"test_dataset_quantity/validation_reports/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'validation_summary': {
                'total_cases': total,
                'successful': successful,
                'failed': failed,
                'success_rate': successful / total if total > 0 else 0,
                'correct_count': correct if successful > 0 else 0,
                'partial_count': partial if successful > 0 else 0,
                'wrong_count': wrong if successful > 0 else 0,
                'average_score': avg_score if successful > 0 else 0
            },
            'validation_details': results,
            'timestamp': datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: {output_file}")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
