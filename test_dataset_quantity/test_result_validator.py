#!/usr/bin/env python3
"""
测试结果验证脚本
通过大模型验证 chat API 测试结果的正确性

使用方法:
1. 配置文件自动读取API密钥
2. 运行验证脚本

依赖: pip install aiohttp
"""

import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import re
import argparse
import sys
from dataclasses import dataclass

# 添加项目根目录到路径
sys.path.append('/home/libo/chatapi')
from config import settings

@dataclass
class ValidationResult:
    """验证结果数据类"""
    test_case_id: str
    is_correct: str  # 正确/错误/部分正确
    score: float  # 1-10分
    confidence: float  # 置信度 0-1
    issues: List[str]
    suggestions: List[str]
    reasoning: str
    dimension_scores: Dict[str, float]
    timestamp: str

class TestResultValidator:
    def __init__(self):
        """初始化验证器 - 使用Azure OpenAI GPT-4.1"""
        self.api_key = settings.azure_api_key
        self.base_url = f"{settings.azure_endpoint}/openai/deployments/{settings.azure_deployment_name}"
        self.model = settings.azure_deployment_name
        self.api_version = settings.azure_api_version
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def validate_with_llm(self, test_case: Dict[str, Any]) -> ValidationResult:
        """使用大模型验证单个测试用例"""

        # 提取测试用例信息
        test_case_id = test_case.get('test_case_id', 'unknown')
        user_input = test_case.get('turn_results', [{}])[0].get('user_input', {})
        execution_result = test_case.get('turn_results', [{}])[0].get('execution_result', {})
        expected_behavior = test_case.get('expected_behavior', {})

        # 构建验证提示词
        prompt = self._build_validation_prompt(
            test_case_id,
            user_input,
            execution_result,
            expected_behavior
        )

        try:
            # 调用Azure OpenAI API进行验证
            async with self.session.post(
                f"{self.base_url}/chat/completions?api-version={self.api_version}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的AI系统测试验证专家。你需要分析测试用例的执行结果，判断其正确性，并以JSON格式返回结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Azure OpenAI API调用失败: {response.status} - {error_text}")

                result = await response.json()
                validation_text = result['choices'][0]['message']['content']

                # 解析JSON结果
                validation_data = self._extract_json_from_text(validation_text)

                # 构建ValidationResult对象
                return ValidationResult(
                    test_case_id=test_case_id,
                    is_correct=validation_data.get('is_correct', 'unknown'),
                    score=validation_data.get('overall_score', 0.0),
                    confidence=validation_data.get('confidence', 0.5),
                    issues=validation_data.get('key_issues', []),
                    suggestions=validation_data.get('suggestions', []),
                    reasoning=validation_data.get('detailed_analysis', ''),
                    dimension_scores=validation_data.get('dimension_scores', {}),
                    timestamp=datetime.now().isoformat()
                )

        except Exception as e:
            return ValidationResult(
                test_case_id=test_case_id,
                is_correct='error',
                score=0.0,
                confidence=0.0,
                issues=[f'验证失败: {str(e)}'],
                suggestions=[],
                reasoning=f'验证过程中发生错误: {str(e)}',
                dimension_scores={},
                timestamp=datetime.now().isoformat()
            )

    def _build_validation_prompt(self, test_case_id: str, user_input: Dict,
                                execution_result: Dict, expected_behavior: Dict) -> str:
        """构建验证提示词"""

        # 格式化用户输入
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
响应类型: {execution_result.get('response_analysis', {}).get('response_types', [])}

## 验证维度
请从以下维度评估（每项1-10分，10分最佳）：

1. **工具选择准确性** (score_tool_selection):
   - 是否选择了正确的工具？
   - 例如：创建联系人应该用contacts_create，创建日程应该用schedules_create

2. **参数提取准确性** (score_parameter_accuracy):
   - 工具参数是否准确反映了用户意图？
   - 例如：用户说"8月8号生日"，应该转换为"08-08"或合理格式

3. **数据处理合理性** (score_data_processing):
   - 数据格式转换、默认值处理等是否合理？
   - 例如：电话格式、地址解析、生日转换等

4. **业务逻辑正确性** (score_business_logic):
   - 对用户需求的理解和处理是否正确？
   - 例如：图像识别是否准确，名片信息提取是否完整

5. **响应完整性** (score_response_completeness):
   - 返回的信息是否完整、准确？

## 判断标准
- **正确**: 工具选择正确，主要参数准确，业务逻辑正确
- **部分正确**: 工具选择正确，但有参数错误或细节问题
- **错误**: 工具选择错误或理解完全错误

## 验证结果格式
请严格按以下JSON格式返回结果，不要包含其他文字：
```json
{{
  "overall_score": 总分(1-10),
  "confidence": 置信度(0-1),
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
        return prompt

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取JSON"""
        # 尝试提取代码块中的JSON
        json_patterns = [
            r'```json\s*(\{{.*?\}})\s*```',
            r'```\s*(\{{.*?\}})\s*```',
            r'(\{{.*?\}})'
        ]

        for pattern in json_patterns:
            matches = re.search(pattern, text, re.DOTALL)
            if matches:
                try:
                    json_str = matches.group(1)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

        # 尝试直接解析整个文本
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 如果都无法解析，返回默认结构
        return {
            'overall_score': 0.0,
            'confidence': 0.0,
            'is_correct': 'error',
            'dimension_scores': {},
            'key_issues': ['无法解析验证结果'],
            'suggestions': [],
            'detailed_analysis': text
        }

    async def validate_test_file(self, test_file_path: str, output_path: str = None) -> Dict[str, Any]:
        """验证整个测试文件"""
        print(f"开始验证测试文件: {test_file_path}")

        # 读取测试数据
        with open(test_file_path, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)

        print(f"共找到 {len(test_cases)} 个测试用例")

        # 验证每个测试用例
        validation_results = []
        for i, test_case in enumerate(test_cases):
            print(f"正在验证第 {i+1}/{len(test_cases)} 个测试用例: {test_case.get('test_case_id')}")

            result = await self.validate_with_llm(test_case)
            validation_results.append({
                'test_case_id': result.test_case_id,
                'is_correct': result.is_correct,
                'score': result.score,
                'confidence': result.confidence,
                'issues': result.issues,
                'suggestions': result.suggestions,
                'reasoning': result.reasoning,
                'dimension_scores': result.dimension_scores,
                'timestamp': result.timestamp,
                'status': 'success' if result.is_correct != 'error' else 'failed'
            })

            # 每10个测试用例保存一次中间结果
            if (i + 1) % 10 == 0:
                await self._save_intermediate_results(validation_results, output_path, i + 1)

        # 生成最终报告
        final_report = {
            'validation_summary': self._generate_summary(validation_results),
            'validation_details': validation_results,
            'timestamp': datetime.now().isoformat()
        }

        if not output_path:
            output_path = f"/home/libo/chatapi/test_dataset_quantity/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)

        print(f"\n验证完成！结果已保存到: {output_path}")
        return final_report

    async def _save_intermediate_results(self, results: List[Dict], output_path: str, count: int):
        """保存中间结果"""
        if not output_path:
            return

        intermediate_path = output_path.replace('.json', f'_intermediate_{count}.json')
        with open(intermediate_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    def _generate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """生成验证摘要"""
        total = len(results)
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = total - successful

        if successful == 0:
            return {
                'total_cases': total,
                'successful': successful,
                'failed': failed,
                'success_rate': 0.0,
                'message': '所有验证都失败了'
            }

        # 统计正确性
        correct_count = sum(1 for r in results if r['is_correct'] == '正确')
        partial_count = sum(1 for r in results if r['is_correct'] == '部分正确')
        wrong_count = sum(1 for r in results if r['is_correct'] == '错误')

        # 计算平均分数
        scores = [r['score'] for r in results if r['status'] == 'success' and r['score'] > 0]
        avg_score = sum(scores) / len(scores) if scores else 0

        # 计算置信度
        confidences = [r['confidence'] for r in results if r['status'] == 'success' and r['confidence'] > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # 统计维度分数
        dimension_stats = {
            'tool_selection': [],
            'parameter_accuracy': [],
            'data_processing': [],
            'business_logic': [],
            'response_completeness': []
        }

        for result in results:
            if result['status'] == 'success':
                for dim, score in result['dimension_scores'].items():
                    if dim in dimension_stats and isinstance(score, (int, float)):
                        dimension_stats[dim].append(score)

        # 计算维度平均分
        dimension_avg = {
            dim: sum(scores) / len(scores) if scores else 0
            for dim, scores in dimension_stats.items()
        }

        # 收集常见问题
        all_issues = []
        all_suggestions = []
        for result in results:
            if result['status'] == 'success':
                all_issues.extend(result.get('issues', []))
                all_suggestions.extend(result.get('suggestions', []))

        return {
            'total_cases': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total,
            'correctness_stats': {
                'correct': correct_count,
                'partial_correct': partial_count,
                'incorrect': wrong_count,
                'correct_rate': correct_count / total if total > 0 else 0,
                'partial_rate': partial_count / total if total > 0 else 0
            },
            'average_score': avg_score,
            'average_confidence': avg_confidence,
            'dimension_average_scores': dimension_avg,
            'quality_distribution': {
                'high_quality': sum(1 for s in scores if s >= 8),
                'medium_quality': sum(1 for s in scores if 5 <= s < 8),
                'low_quality': sum(1 for s in scores if s < 5)
            },
            'common_issues': list(set(all_issues))[:10],  # 去重并限制数量
            'common_suggestions': list(set(all_suggestions))[:10]
        }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='验证测试结果 - 使用Azure OpenAI GPT-4.1')
    parser.add_argument('test_file', help='测试结果JSON文件路径')
    parser.add_argument('--output', help='输出报告路径')

    args = parser.parse_args()

    print("="*60)
    print("测试结果验证工具 - 使用 Azure OpenAI GPT-4.1")
    print("="*60)

    # 检查配置
    if not settings.azure_api_key:
        print("错误: Azure OpenAI API密钥未配置")
        print("请在.env文件中设置 AZURE_OPENAI_API_KEY")
        return

    if not settings.azure_endpoint:
        print("错误: Azure OpenAI端点未配置")
        print("请在.env文件中设置 AZURE_OPENAI_ENDPOINT")
        return

    print(f"使用Azure OpenAI配置:")
    print(f"  端点: {settings.azure_endpoint}")
    print(f"  模型: {settings.azure_deployment_name}")
    print(f"  API版本: {settings.azure_api_version}")
    print()

    async with TestResultValidator() as validator:
        report = await validator.validate_test_file(args.test_file, args.output)

        # 打印摘要
        print("\n" + "="*60)
        print("验证摘要")
        print("="*60)
        summary = report['validation_summary']

        print(f"总测试用例数: {summary['total_cases']}")
        print(f"验证成功: {summary['successful']}")
        print(f"验证失败: {summary['failed']}")
        print(f"成功率: {summary['success_rate']:.2%}")

        if 'correctness_stats' in summary:
            print("\n正确性统计:")
            cs = summary['correctness_stats']
            print(f"  完全正确: {cs['correct']} ({cs['correct_rate']:.2%})")
            print(f"  部分正确: {cs['partial_correct']} ({cs['partial_rate']:.2%})")
            print(f"  完全错误: {cs['incorrect']}")

        print(f"\n平均总分: {summary['average_score']:.2f}/10")
        print(f"平均置信度: {summary['average_confidence']:.2f}")

        if 'dimension_average_scores' in summary:
            print("\n各维度平均分:")
            for dim, score in summary['dimension_average_scores'].items():
                print(f"  {dim}: {score:.2f}/10")

        if 'quality_distribution' in summary:
            print("\n质量分布:")
            qd = summary['quality_distribution']
            print(f"  高质量 (≥8分): {qd['high_quality']} 个")
            print(f"  中等质量 (5-7分): {qd['medium_quality']} 个")
            print(f"  低质量 (<5分): {qd['low_quality']} 个")

        if 'common_issues' in summary and summary['common_issues']:
            print("\n常见问题:")
            for issue in summary['common_issues'][:5]:
                print(f"  • {issue}")

        if 'common_suggestions' in summary and summary['common_suggestions']:
            print("\n改进建议:")
            for suggestion in summary['common_suggestions'][:5]:
                print(f"  • {suggestion}")

        print("\n" + "="*60)


if __name__ == '__main__':
    asyncio.run(main())