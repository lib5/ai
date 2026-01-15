# 测试结果验证工具

这是一个使用 Azure OpenAI GPT-4.1 验证 chat API 测试结果正确性的工具。

## 功能特性

- ✅ 使用 Azure OpenAI GPT-4.1 进行智能验证
- ✅ 自动从配置文件读取API密钥
- ✅ 多维度评估（工具选择、参数准确性、数据处理、业务逻辑、响应完整性）
- ✅ 批量处理测试用例
- ✅ 生成详细验证报告
- ✅ 中间结果保存，防止意外中断
- ✅ 统计分析和可视化摘要

## 安装依赖

```bash
pip install aiohttp python-dotenv
```

## 配置文件

确保你的 `.env` 文件中包含以下配置：

```bash
# Azure OpenAI 配置
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
```

## 使用方法

### 1. 基本使用

```bash
python /home/libo/chatapi/test_dataset_quantity/test_result_validator.py /path/to/test_results.json
```

### 2. 指定输出路径

```bash
python /home/libo/chatapi/test_dataset_quantity/test_result_validator.py /path/to/test_results.json --output /path/to/validation_report.json
```

## 输出示例

```
============================================================
测试结果验证工具 - 使用 Azure OpenAI GPT-4.1
============================================================
使用Azure OpenAI配置:
  端点: https://your-resource.openai.azure.com/
  模型: gpt-4.1
  API版本: 2024-02-15-preview

开始验证测试文件: /path/to/test_results.json
共找到 44 个测试用例
正在验证第 1/44 个测试用例: TEST_EXCEL_000
正在验证第 2/44 个测试用例: TEST_EXCEL_001
...
验证完成！结果已保存到: /path/to/validation_report.json

============================================================
验证摘要
============================================================
总测试用例数: 44
验证成功: 44
验证失败: 0
成功率: 100.00%

正确性统计:
  完全正确: 38 (86.36%)
  部分正确: 5 (11.36%)
  完全错误: 1 (2.27%)

平均总分: 8.45/10
平均置信度: 0.87

各维度平均分:
  tool_selection: 9.23/10
  parameter_accuracy: 8.12/10
  data_processing: 8.45/10
  business_logic: 8.67/10
  response_completeness: 8.78/10

质量分布:
  高质量 (≥8分): 35 个
  中等质量 (5-7分): 8 个
  低质量 (<5分): 1 个

常见问题:
  • 生日格式处理不一致
  • 电话号码提取不完整
  • 地址解析精度待提升

改进建议:
  • 优化日期格式标准化
  • 增强 OCR 识别能力
  • 改进自然语言理解

============================================================
```

## 验证维度

### 1. 工具选择准确性 (score_tool_selection)
- 检查是否选择了正确的工具
- 例如：创建联系人应该用 `contacts_create`，创建日程应该用 `schedules_create`

### 2. 参数提取准确性 (score_parameter_accuracy)
- 工具参数是否准确反映了用户意图
- 例如：用户说"8月8号生日"，应该转换为"08-08"或合理格式

### 3. 数据处理合理性 (score_data_processing)
- 数据格式转换、默认值处理等是否合理
- 例如：电话格式、地址解析、生日转换等

### 4. 业务逻辑正确性 (score_business_logic)
- 对用户需求的理解和处理是否正确
- 例如：图像识别是否准确，名片信息提取是否完整

### 5. 响应完整性 (score_response_completeness)
- 返回的信息是否完整、准确

## 输出格式

### 正确性判断
- **正确**: 工具选择正确，主要参数准确，业务逻辑正确
- **部分正确**: 工具选择正确，但有参数错误或细节问题
- **错误**: 工具选择错误或理解完全错误

### 评分标准
- **1-3分**: 基本错误或完全错误
- **4-6分**: 部分正确，有明显问题
- **7-8分**: 基本正确，细节待改进
- **9-10分**: 完全正确，表现优秀

### 置信度
- **0.0-0.3**: 低置信度，验证结果不够可靠
- **0.4-0.7**: 中等置信度，验证结果基本可信
- **0.8-1.0**: 高置信度，验证结果非常可靠

## 输出文件

### 主要输出
- `validation_report_YYYYMMDD_HHMMSS.json`: 完整验证报告

### 中间结果
- `validation_report_YYYYMMDD_HHMMSS_intermediate_N.json`: 每10个测试用例保存一次

### 报告结构
```json
{
  "validation_summary": {
    "total_cases": 44,
    "successful": 44,
    "failed": 0,
    "success_rate": 1.0,
    "correctness_stats": {
      "correct": 38,
      "partial_correct": 5,
      "incorrect": 1,
      "correct_rate": 0.8636,
      "partial_rate": 0.1136
    },
    "average_score": 8.45,
    "average_confidence": 0.87,
    "dimension_average_scores": {...},
    "quality_distribution": {...},
    "common_issues": [...],
    "common_suggestions": [...]
  },
  "validation_details": [
    {
      "test_case_id": "TEST_EXCEL_000",
      "is_correct": "正确",
      "score": 9.5,
      "confidence": 0.95,
      "issues": [...],
      "suggestions": [...],
      "reasoning": "...",
      "dimension_scores": {...},
      "timestamp": "2026-01-15T14:30:00.000000",
      "status": "success"
    }
  ],
  "timestamp": "2026-01-15T14:30:00.000000"
}
```

## 注意事项

1. **API 成本**: 每个测试用例需要调用一次 Azure OpenAI GPT-4.1，请确保有足够的 API 配额
2. **执行时间**: 验证速度取决于 API 响应时间，建议在网络稳定的环境下运行
3. **中间结果**: 每10个测试用例会自动保存中间结果，防止意外中断导致进度丢失
4. **结果解释**: GPT-4.1 的判断基于训练数据和提示词，建议结合人工审查
5. **敏感信息**: 请不要在测试数据中包含敏感信息

## 故障排除

### API 调用失败
- 检查 Azure OpenAI 配置是否正确
- 检查网络连接
- 检查 API 配额是否充足

### JSON 解析失败
- 检查 Azure OpenAI API 响应格式
- 查看详细错误日志
- 尝试调整 temperature 和 max_tokens 参数

### 验证结果不准确
- 检查测试数据格式是否正确
- 尝试调整验证提示词
- 考虑使用更严格的评分标准

## 示例代码

```python
import asyncio
from test_result_validator import TestResultValidator

async def main():
    async with TestResultValidator() as validator:
        report = await validator.validate_test_file(
            "/path/to/test_results.json",
            "/path/to/output.json"
        )
        print("验证完成！")
        print(f"正确率: {report['validation_summary']['correctness_stats']['correct_rate']:.2%}")

asyncio.run(main())
```
