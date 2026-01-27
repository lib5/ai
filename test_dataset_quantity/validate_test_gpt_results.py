#!/usr/bin/env python3
"""
测试结果验证脚本 - 多路径支持版
使用Azure OpenAI GPT-4.1验证chat API测试结果的正确性

功能特点:
- 支持传统单路径期望格式 (steps数组)
- 支持多路径期望格式 (paths数组，每个路径包含description和steps)
- 只要实际执行符合任一路径，即判定为正确
- 灵活的工具调用验证
"""

import json
import asyncio
import aiohttp
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv('/home/libo/chatapi/.env')

# 获取Azure OpenAI配置
AZURE_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_API_KEY = os.getenv('AZURE_API_KEY') or os.getenv('AZURE_OPENAI_API_KEY')
AZURE_API_VERSION = os.getenv('AZURE_API_VERSION') or os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
DEPLOYMENT_NAME = os.getenv('AZURE_DEPLOYMENT_NAME') or os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4.1')

# 创建日志目录
LOG_DIR = Path(__file__).parent / "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = f"{LOG_DIR}/validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# 简单日志记录器
class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.buffer = []

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        self.buffer.append(log_msg)

    def save(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.buffer))

logger = Logger(LOG_FILE)

print("="*60)
print("测试结果验证工具 - 使用 Azure OpenAI GPT-4.1")
print("="*60)

logger.log("开始验证过程")
logger.log(f"Azure OpenAI配置:")
logger.log(f"  端点: {AZURE_ENDPOINT}")
logger.log(f"  模型: {DEPLOYMENT_NAME}")
logger.log(f"  API版本: {AZURE_API_VERSION}")
logger.log(f"日志文件: {LOG_FILE}")
print()


async def validate_single_turn(session, test_case_id, turn_result, turn_index, base_timestamp_with_weekday, logger):
    """验证单个turn"""
    turn_id = turn_result.get('turn_id', f'turn_{turn_index}')
    user_input = turn_result.get('user_input', {})
    execution_result = turn_result.get('execution_result', {})
    expected_behavior = turn_result.get('expected_behavior', {})

    logger.log(f"  ── 第{turn_index + 1}轮对话 ──")
    logger.log(f"  Turn ID: {turn_id}")

    # 记录用户输入
    if user_input.get('type') == 'text':
        input_display = f"文本输入: {user_input.get('content', '')}"
    elif user_input.get('type') == 'image':
        input_display = f"图像输入: {user_input.get('content', '')}"
    else:
        input_display = f"输入: {json.dumps(user_input, ensure_ascii=False, indent=2)}"

    logger.log(f"  用户输入: {user_input.get('content', '')}")
    logger.log(f"  输入类型: {user_input.get('type')}")

    # 🔧 支持多路径期望格式
    # 新格式：expected_behavior 是一个数组，包含多个可能的执行路径
    expected_behavior_paths = expected_behavior if isinstance(expected_behavior, list) else []
    # 旧格式兼容：steps 数组
    expected_steps = expected_behavior.get('steps', []) if isinstance(expected_behavior, dict) else []

    logger.log(f"  多路径期望数: {len(expected_behavior_paths)}")
    logger.log(f"  传统步骤期望数: {len(expected_steps)}")

    # 优先使用多路径格式
    if expected_behavior_paths:
        logger.log("  ✅ 使用多路径期望格式:")
        logger.log(f"    📝 共{len(expected_behavior_paths)}个可能的执行路径")
        for i, path in enumerate(expected_behavior_paths):
            desc = path.get('description', f'路径{i+1}')
            steps = path.get('steps', [])
            logger.log(f"    路径 {i+1}: {desc}")
            logger.log(f"      步骤数: {len(steps)}")
            for j, step in enumerate(steps):
                step_type = step.get('type', '')
                tool_name = step.get('tool_name', '')
                logger.log(f"        步骤{j+1}: {step_type} - {tool_name}")
        logger.log(f"    🎯 验证规则: 只要实际执行符合任一路径，即判定正确")
    elif expected_steps:
        logger.log("  📋 使用传统步骤期望格式:")
        for i, step in enumerate(expected_steps):
            logger.log(f"    步骤 {i+1}: {json.dumps(step, ensure_ascii=False)}")
    else:
        logger.log("  ⚠️ 未找到期望行为数据")

    # 格式化实际执行结果
    actual_tool_calls = []
    tool_results = []
    assistant_responses = []
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
            elif item.get('type') == 'markdown' or (item.get('role') == 'assistant' and item.get('type') == 'markdown'):
                assistant_responses.append({
                    'message_id': item.get('message_id', ''),
                    'content': item.get('content', ''),
                    'is_merged': item.get('is_merged', False),
                    'original_fragments': item.get('original_fragments', 1)
                })

    logger.log(f"  实际工具调用数: {len(actual_tool_calls)}")
    for i, tool_call in enumerate(actual_tool_calls):
        logger.log(f"    工具 {i+1}: {tool_call.get('tool_name')} - {tool_call.get('tool_cn', '')}")
        logger.log(f"      参数: {tool_call.get('arguments', '')}")

    logger.log(f"  工具执行结果数: {len(tool_results)}")
    logger.log(f"  Assistant响应数: {len(assistant_responses)}")
    for i, response in enumerate(assistant_responses):
        logger.log(f"    响应 {i+1}: {response.get('content', '')[:100]}...")

    # 🔧 构建多路径验证prompt
    if expected_behavior_paths:
        # 使用多路径格式
        expected_content = json.dumps(expected_behavior_paths, ensure_ascii=False, indent=2)
        prompt_header = "## 期望行为 (多路径格式)\n注意：expected_behavior是一个数组，包含多个可能的执行路径。只要实际执行符合其中一个路径，即为正确。\n"
    elif expected_steps:
        # 使用传统格式
        expected_content = json.dumps(expected_steps, ensure_ascii=False, indent=2)
        prompt_header = "## 期望行为 (传统格式)\n"
    else:
        expected_content = "未找到期望行为数据"
        prompt_header = "## 期望行为\n"

    # 构建Assistant响应的markdown内容
    assistant_responses_summary = ""
    if assistant_responses:
        assistant_responses_summary = "\n## 合并后的Assistant响应\n"
        for i, response in enumerate(assistant_responses):
            # 构建合并后的响应信息
            content = response.get('content', '')
            is_merged = response.get('is_merged', False)
            fragments = response.get('original_fragments', 1)

            assistant_responses_summary += f"\n### 响应 {i+1}:\n"
            assistant_responses_summary += f"{content}\n"

            if is_merged and fragments > 1:
                assistant_responses_summary += f"*(注: 此响应由{fragments}个流式片段合并而成)*\n"

    prompt = f"""
你是一个专业的AI系统测试验证专家。请分析以下测试用例的执行结果，判断其正确性。

## 测试用例信息
测试ID: {test_case_id}
{input_display}

## 时间信息 
测试基准时间: {base_timestamp_with_weekday}
注：用户输入中的"今天下午两点"等相对时间表达应基于此基准时间来判断
**关于时间判断，你必须遵守以下首要规则：**
1.  **忽略期望时间**：
    - 输入为文本输入时候 在评估"时间判断准确性"时，**请完全忽略测试用例中"期望执行步骤"里的start_time,它可能与本次评测的基准时间不符，不具备参考价值
    - 如果输入是图像输入时 要保持与期望start_time一致。
2.  **唯一时间基准**：所有关于"今天"、"明天"、"下周"等相对时间的正确性判断，**有且仅有一个正确标准：即基于下方提供的"测试基准时间"进行推算的结果**。
3.  **验证实际时间**：你只需判断"实际调用的工具"中的时间参数，是否与基于**测试基准时间**推算出的正确时间相匹配，可以远超基准时间 合理就行。
参考下面两个例子 下面两个例子评估错误 虽然与预期不符但是实际结果是正确的 那时间准确性这一项分数应该是10分
- "时间参数严重错误：'后天中午'基于基准时间2026-01-16T10:45:59应为2026-01-18T12:00:00，但实际创建时间为2026-01-18T12:00:00，表面看似正确，但实际上'后天'应为2026-01-18，实际参数是正确的。"

- 用户输入为'下周四'，基准时间为2026-01-16（周五），下周四应为2026-01-22，但实际创建时间为2026-01-22，参数正确，但期望行为中的时间为2026-01-23，期望行为有误。实际执行结果是正确的 时间参数分数应该为高分

## 期望行为
{prompt_header}
{expected_content}

## 实际执行结果
实际调用的工具: {json.dumps(actual_tool_calls, ensure_ascii=False, indent=2)}
工具执行结果: {json.dumps(tool_results, ensure_ascii=False, indent=2)}
执行状态: {execution_result.get('status', 'unknown')}
{assistant_responses_summary}
## 验证标准
请从以下维度评估（每项1-10分，10分最佳）：

1. **工具选择准确性**: 是否选择了正确的工具？
2. **参数提取准确性**: 工具参数是否准确反映了用户意图？特别是时间参数是否正确？对于人脉 除了note之外 其他要严格一致
    - reminder_time要完全符合用户意图 否则必须判断错误  如日程提醒时间(reminder_time)设置为-1d，未完全符合用户要求的提前一周(-1w)提醒 判断为错误
3. **时间判断准确性**: 对于日程相关测试，请重点检查：
   - 实际调用中的时间参数是否基于**测试基准时间**正确转换？如果转化正确 则这项准确性分数满分。请严格应用下方"日期星期计算规则"。
   -注意注意  如果期望时间有误但符合实际就要给10分 这种情况下不能输出时间参数严重错误
   -  对于这种情况 "时间参数严重错误：'明天晚上八点'应为2026-01-17 20:00:00，但实际创建在2026-01-17 20:00:00，表面看似正确，但基准时间为2026-01-16，'明天'应为2026-01-17，实际参数是正确的。 这种不算时间参数严重错误 算参数提取正确

4. **数据处理合理性**: 数据格式转换、默认值处理等是否合理？
5. **业务逻辑正确性**: 对用户需求的理解和处理是否正确？
6. **响应完整性**:
   - **Markdown响应完整性**: 检查Assistant的markdown响应内容是否完整、准确，是否遗漏重要信息？
   - **响应质量**: 响应内容是否清晰、准确、有条理？
   - **信息准确性**: 响应中的信息是否与工具执行结果一致？


## 时间判断要求
如果是日程、会议相关的测试用例，请特别关注：
- 基准时间：{base_timestamp_with_weekday}
- 用户说"今天下午两点"，基准时间是{base_timestamp_with_weekday}
- 那么期望的开始时间应该是当天下午2点（即14:00）
- 实际执行的时间参数应该与期望时间匹配或合理接近

## 日期星期计算规则
请严格按照以下规则进行日期计算：
1. **日期-星期对应**：
   - 星期一 = 周一 = 周1
   - 星期二 = 周二 = 周2
   - 星期三 = 周三 = 周3
   - 星期四 = 周四 = 周4
   - 星期五 = 周五 = 周5
   - 星期六 = 周六 = 周6
   - 星期日 = 周日 = 周7

2. **相对时间处理**：
   - "下周"指的是：从基准时间开始遇到的第一个周一开始到周日结束的完整周  基准时间是在周一 那么下周是从下一个周一开始 如基准时间为2026-01-19，'下周'应为2026-01-26至2026-02-01。
   - "下周四"指的是：下一周中的周四
   - `"周X" = 基准时间所在周内的星期X
   - "下周"指的是：从第一个周一开始的完整一周
   - "下个月"指的是：基准时间所在月的下一个月

3. **日期计算示例**：
   - 如果基准时间是2026-01-19（周一）
   - "周三" = 2026-01-21 
   - "下周一" = 2026-01-26
   - "下周四" = 2026-01-29



## 判断标准
- **正确**: 工具选择正确，主要参数准确(可以不一致但合理、相近就可以)，时间判断正确，业务逻辑正确
- **错误**: 工具选择错误，理解完全错误或者时间参数严重错误、某个参数不合理、某个参数与预期完全不一致

## 🔧 多路径验证规则
- **多路径验证**: 如果expected_behavior是数组格式，包含多个可能的执行路径，**只要实际执行符合其中一个路径，即为正确**
- **路径匹配**: 检查实际工具调用序列是否与任一路径的steps匹配
- **灵活执行**: 允许执行额外的工具调用，只要不影响核心逻辑

## 注意
- 由于期望的基准时间和评测基准时间不一致 因此一切以评测的基准时间为准 不考虑期望的时间
- **不需要管incomplete状态**，如果一轮对话中incomplete=true，表示这一轮没有调用工具，这是正常的，不影响评估结果 若期望中存在调用工具 需要根据上下文判断是否一定需要调用该工具 若一定需要调用 则判断错误。

## 补充
1. 用户表达出意图就可以调用 不需要明确指出
2. 对于生日的年份可以补全 不算错误
3. 相比于预期可以添加多余参数 只要合理就可以添加
4. id可以不一致
5. 创建人脉时需要去查找人脉 这是正确的  有上下文的情况下，更新人脉时也可以不查找,只要工具结果执行正确即可
6. 提醒时间的格式必须是后面10个值中的一个：-5m​ 表示 5 分钟前； -10m​ 表示 10 分钟前；-15m​ 表示 15 分钟前；-30m​ 表示 30 分钟前；-1h​ 表示 1 小时前；-2h​ 表示 2 小时前；-1d​ 表示 1 天前；-2d​ 表示 2 天前；-1w​ 表示 1 周前；-2w​ 表示 2 周前。单位：d=天，m=分钟，w=周，h=小时
7. 对于日程的时间 如果用户未明确要求，**结束时间、持续时长、提醒时间（reminder_time）可以灵活设置，也可以不设置 因为默认-5m，只要逻辑合理即可。
8. reminder_time、日程结束时间，如果用户问题中没有明确要求这个时长 便可以和预期不一致
9. note不一致但相近也是可以的 如 用户期望为'服务器相关行业'，实际为'服务器'是正确的
10. 对于日程创建的时间 以基准时间为准 如果合理则不需要和期望时间保持一致  如 用户说'今天下午八点'，基准时间为2026-01-16，实际却创建在2026-01-16 20:00:00，期望应为2026-01-16 20:00:00，但期望行为中时间为2026-01-13 20:00:00，期望行为本身有误 因此他的参数提取是正确的 判断为对
11. 期望有误但执行结果合理 则不需要和期望保持一致 可以判断为正确
12. full_day可以是日期 (start_time、end_time)与full_day有其中一个就可以
13. 响应内容在"content"字段中查看
14. 待测试数据可以与预期不一致 对于复杂任务chunks_count>=14 ，只要最后都完成了用户的意图 都可以算正确，使用的工具、参数可以和期望不一致
15. 多轮对话中如果可以从前1-3轮直接获取得到数据，可以不需要调用查询工具 如第一轮说了江涵的生日和手机号 第二轮可以直接输出这两条数据 也可以通过搜索联系人得到
16. 多余创建的日程和人脉 合理也可以接受 不能给低分
17. 根据id查找的不会误删、找错联系人
18. 工具选择和参数提取均未发生，但是最后输出的结果合理，过程合理(从上下文中得到信息) 这不影响影响业务逻辑和响应完整性
19. **多路径格式支持**: 当expected_behavior为数组时，每个元素包含"description"和"steps"，表示一个可能的执行路径。只要实际执行符合任一路径，即判定正确。 

请以JSON格式返回验证结果：
```json
{{
  "overall_score": 总分(1-10),
  "is_correct": "正确/错误",
  "dimension_scores": {{
    "tool_selection": 工具选择分数,
    "parameter_accuracy": 参数准确性分数,
    "time_accuracy": 时间准确性分数,
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

    # 记录发送给GPT的请求信息
    logger.log("-" * 60)
    logger.log(f"第{turn_index + 1}轮 - 发送给GPT-4.1的请求:")
    logger.log(f"URL: {url}")
    logger.log(f"完整Prompt:")
    logger.log(prompt)
    logger.log("-" * 60)

    try:
        async with session.post(url, headers=headers, json=data, timeout=60) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.log(f"API调用失败: {response.status} - {error_text}", "ERROR")
                raise Exception(f"Azure OpenAI API调用失败: {response.status} - {error_text}")

            result = await response.json()
            validation_text = result['choices'][0]['message']['content']

            # 记录GPT响应
            logger.log("GPT-4.1原始响应:")
            logger.log("-" * 60)
            logger.log(validation_text)
            logger.log("-" * 60)

            # 尝试解析JSON
            validation_data = None
            try:
                validation_data = json.loads(validation_text)
                logger.log("JSON解析成功")
            except json.JSONDecodeError:
                # 尝试从文本中提取JSON
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', validation_text, re.DOTALL)
                if json_match:
                    try:
                        validation_data = json.loads(json_match.group(1))
                        logger.log("从代码块中提取JSON成功")
                    except json.JSONDecodeError:
                        logger.log("从代码块提取JSON失败", "WARNING")
                        validation_data = None

            if validation_data:
                result = {
                    'turn_id': turn_id,
                    'turn_index': turn_index,
                    'is_correct': validation_data.get('is_correct', 'unknown'),
                    'score': validation_data.get('overall_score', 0),
                    'dimension_scores': validation_data.get('dimension_scores', {}),
                    'issues': validation_data.get('key_issues', []),
                    'suggestions': validation_data.get('suggestions', []),
                    'reasoning': validation_data.get('detailed_analysis', ''),
                    'status': 'success',
                    'raw_prompt': prompt,
                    'raw_response': validation_text
                }
                logger.log(f"  第{turn_index + 1}轮验证结果: {result['is_correct']}, 评分: {result['score']}/10")
                logger.log(f"  维度分数: {result['dimension_scores']}")
                logger.log(f"  主要问题: {result['issues']}")
                return result
            else:
                logger.log("  无法解析验证结果", "ERROR")
                return {
                    'turn_id': turn_id,
                    'turn_index': turn_index,
                    'is_correct': 'unknown',
                    'score': 0,
                    'dimension_scores': {},
                    'issues': ['无法解析验证结果'],
                    'suggestions': [],
                    'reasoning': validation_text,
                    'status': 'failed',
                    'raw_prompt': prompt,
                    'raw_response': validation_text
                }

    except Exception as e:
        logger.log(f"  第{turn_index + 1}轮验证失败: {str(e)}", "ERROR")
        return {
            'turn_id': turn_id,
            'turn_index': turn_index,
            'is_correct': 'error',
            'score': 0,
            'dimension_scores': {},
            'issues': [f'验证失败: {str(e)}'],
            'suggestions': [],
            'reasoning': '',
            'status': 'failed'
        }


async def validate_single_case(session, test_case, case_index=0):
    """验证单个测试用例（支持多轮）"""
    test_case_id = test_case.get('test_case_id', 'unknown')
    turn_results = test_case.get('turn_results', [])

    logger.log("="*80)
    logger.log(f"测试用例 #{case_index + 1}: {test_case_id}")
    logger.log(f"总轮数: {len(turn_results)}")
    logger.log("="*80)

    # 获取基准时间戳用于时间判断
    base_timestamp = test_case.get('timestamp', '')
    # 解析时间戳并获取星期几
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(base_timestamp.replace('Z', '+00:00'))
        weekday_cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][dt.weekday()]
        base_timestamp_with_weekday = f"{base_timestamp} ({weekday_cn})"
    except:
        base_timestamp_with_weekday = base_timestamp

    logger.log(f"基准时间戳: {base_timestamp_with_weekday}")

    # 验证所有turns
    turn_validation_results = []
    for turn_index, turn_result in enumerate(turn_results):
        logger.log("")  # 空行分隔
        logger.log(f"开始验证第{turn_index + 1}轮 (共{len(turn_results)}轮)")
        turn_validation_result = await validate_single_turn(
            session, test_case_id, turn_result, turn_index,
            base_timestamp_with_weekday, logger
        )
        turn_validation_results.append(turn_validation_result)
        logger.log(f"第{turn_index + 1}轮验证完成，状态: {turn_validation_result['status']}")

    logger.log(f"所有轮次验证完成，共验证{len(turn_validation_results)}轮")

    # 聚合所有turns的分数
    total_score = sum(r['score'] for r in turn_validation_results if r['status'] == 'success')
    num_successful_turns = sum(1 for r in turn_validation_results if r['status'] == 'success')
    avg_score = (total_score / num_successful_turns) if num_successful_turns > 0 else 0

    # 计算维度平均分
    dimension_scores = {}
    if num_successful_turns > 0:
        all_dimensions = set()
        for r in turn_validation_results:
            if r['status'] == 'success':
                all_dimensions.update(r['dimension_scores'].keys())

        for dim in all_dimensions:
            dim_scores = [
                r['dimension_scores'].get(dim, 0)
                for r in turn_validation_results
                if r['status'] == 'success' and dim in r['dimension_scores']
            ]
            dimension_scores[dim] = sum(dim_scores) / len(dim_scores) if dim_scores else 0

    # 判断整体正确性：所有turns都正确才算正确
    all_correct = all(r['is_correct'] == '正确' for r in turn_validation_results if r['status'] == 'success')
    any_error = any(r['is_correct'] == '错误' for r in turn_validation_results if r['status'] == 'success')

    overall_is_correct = '正确' if all_correct else ('错误' if any_error else 'unknown')

    # 汇总所有问题和建议
    all_issues = []
    all_suggestions = []
    all_reasoning = []
    logger.log(f"开始汇总{len(turn_validation_results)}轮的结果")
    for r in turn_validation_results:
        logger.log(f"  处理第{r['turn_index'] + 1}轮，状态: {r['status']}")
        if r['status'] == 'success':
            issue_prefix = f"第{r['turn_index'] + 1}轮: "
            all_issues.extend([issue_prefix + str(issue) for issue in r['issues']])
            all_suggestions.extend([issue_prefix + str(suggestion) for suggestion in r['suggestions']])
            if r.get('reasoning'):
                reasoning_prefix = f"第{r['turn_index'] + 1}轮分析: "
                all_reasoning.append(reasoning_prefix + str(r['reasoning']))
        else:
            logger.log(f"    跳过第{r['turn_index'] + 1}轮，状态非success")

    logger.log(f"汇总完成，共{len(all_issues)}个问题，{len(all_suggestions)}个建议")

    # 构建最终结果
    final_result = {
        'test_case_id': test_case_id,
        'is_correct': overall_is_correct,
        'score': avg_score,
        'dimension_scores': dimension_scores,
        'issues': all_issues,
        'suggestions': all_suggestions,
        'reasoning': '\n\n'.join(all_reasoning),
        'status': 'success' if num_successful_turns == len(turn_results) else 'partial',
        'turn_count': len(turn_results),
        'successful_turns': num_successful_turns,
        'turn_details': turn_validation_results,
        'aggregated': True
    }

    # 打印汇总结果
    logger.log("")
    logger.log("="*80)
    logger.log(f"测试用例汇总: {test_case_id}")
    logger.log(f"总轮数: {len(turn_results)}")
    logger.log(f"成功验证轮数: {num_successful_turns}")
    logger.log(f"整体正确性: {overall_is_correct}")
    logger.log(f"平均评分: {avg_score:.2f}/10")
    logger.log(f"维度分数: {dimension_scores}")
    logger.log("="*80)

    return final_result
async def main():
    """主函数"""
    # 确保输出目录存在
    import os
    os.makedirs("test_dataset_quantity/validation_reports", exist_ok=True)

    test_file = "test_dataset_quantity/test_results_74_merged_20260121_201332-gemini.json"

    # 读取测试文件
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        logger.log(f"错误: 测试文件不存在: {test_file}", "ERROR")
        return
    except Exception as e:
        logger.log(f"错误: 读取测试文件失败: {e}", "ERROR")
        return

    logger.log(f"读取到 {len(test_cases)} 个测试用例")
    print(f"读取到 {len(test_cases)} 个测试用例")
    print(f"将验证前 5 个测试用例")
    print()

    # 只取前5个测试用例进行测试
    test_cases_to_validate = test_cases[:]

    results = []
    problem_cases = []  # 记录错误用例

    try:
        async with aiohttp.ClientSession() as session:
            for i, test_case in enumerate(test_cases_to_validate):
                logger.log(f"开始验证第 {i+1}/{len(test_cases_to_validate)} 个测试用例")
                print(f"正在验证第 {i+1}/{len(test_cases_to_validate)} 个: {test_case.get('test_case_id')}")

                result = await validate_single_case(session, test_case, i)
                results.append(result)

                # 记录问题用例
                if result['is_correct'] == '错误':
                    problem_cases.append(result)
                    logger.log(f"⚠️ 发现问题用例: {result['test_case_id']} - {result['is_correct']}")
                else:
                    logger.log(f"✅ 正常用例: {result['test_case_id']} - {result['is_correct']}")

                print(f"  结果: {result['is_correct']}, 评分: {result['score']}/10")
                if result['issues']:
                    print(f"  问题: {', '.join(result['issues'][:2])}")
                print()

    except Exception as e:
        logger.log(f"验证过程中发生错误: {e}", "ERROR")
        print(f"验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

    # 打印摘要
    logger.log("="*80)
    logger.log("验证摘要")
    logger.log("="*80)
    print("="*60)
    print("验证摘要")
    print("="*60)

    total = len(results)
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = total - successful

    logger.log(f"总测试用例数: {total}")
    logger.log(f"验证成功: {successful}")
    logger.log(f"验证失败: {failed}")
    print(f"总测试用例数: {total}")
    print(f"验证成功: {successful}")
    print(f"验证失败: {failed}")

    # 计算正确率（基于所有验证成功的测试用例）
    correct = sum(1 for r in results if r['status'] == 'success' and r['is_correct'] == '正确')
    wrong = sum(1 for r in results if r['status'] == 'success' and r['is_correct'] == '错误')
    accuracy = (correct / total * 100) if total > 0 else 0

    if successful > 0:
        logger.log(f"  正确: {correct}")
        logger.log(f"  错误: {wrong}")
        logger.log(f"  正确率: {accuracy:.1f}%")
        print(f"  正确: {correct}")
        print(f"  错误: {wrong}")
        print(f"  正确率: {accuracy:.1f}%")

        avg_score = sum(r['score'] for r in results if r['status'] == 'success') / successful
        logger.log(f"平均评分: {avg_score:.2f}/10")
        print(f"平均评分: {avg_score:.2f}/10")

    # 详细处理问题用例
    logger.log("")
    logger.log("="*80)
    logger.log("问题用例详细分析")
    logger.log("="*80)
    if problem_cases:
        logger.log(f"发现 {len(problem_cases)} 个问题用例:")

        for i, case in enumerate(problem_cases):
            logger.log("")
            logger.log(f"问题用例 #{i+1}: {case['test_case_id']}")
            logger.log(f"  正确性: {case['is_correct']}")
            logger.log(f"  评分: {case['score']}/10")
            logger.log(f"  问题: {case['issues']}")
            logger.log(f"  推理: {case.get('reasoning', '')[:200]}...")

            # 记录原始输入输出
            logger.log("  详细信息:")
            logger.log(f"    用户输入: {case.get('user_input', {}).get('content', '')}")
            logger.log(f"    期望步骤: {case.get('expected_behavior', {}).get('steps', [])}")
            logger.log(f"    完整原始Prompt:")
            logger.log(case.get('raw_prompt', ''))
            logger.log(f"    完整GPT响应:")
            logger.log(case.get('raw_response', ''))
    else:
        logger.log("✅ 没有发现问题用例!")

    print()
    print("详细结果:")

    for result in results:
        print(f"\n{result['test_case_id']}:")
        print(f"  正确性: {result['is_correct']}")
        print(f"  评分: {result['score']}/10")
        if 'turn_count' in result and result['turn_count'] > 1:
            print(f"  总轮数: {result['turn_count']}")
            # 显示每轮的分数
            if 'turn_details' in result:
                print(f"  各轮分数:")
                for turn in result['turn_details']:
                    if turn.get('status') == 'success':
                        print(f"    第{turn['turn_index'] + 1}轮: {turn['score']}/10 - {turn['is_correct']}")
                    else:
                        print(f"    第{turn['turn_index'] + 1}轮: 验证失败")
        if result['dimension_scores']:
            print(f"  维度分数: {result['dimension_scores']}")
        if result['issues']:
            print(f"  问题: {'; '.join(result['issues'])}")
        if result['reasoning']:
            print(f"  分析: {result['reasoning'][:100]}...")

    # 保存结果
    output_file = f"test_dataset_quantity/validation_reports/validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    final_report = {
        'validation_summary': {
            'total_cases': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'correct_count': correct,
            'wrong_count': wrong,
            'accuracy_rate': accuracy,
            'average_score': avg_score if successful > 0 else 0
        },
        'validation_details': results,
        'problem_cases': problem_cases,
        'log_file': str(LOG_FILE),  # 将Path对象转换为字符串
        'timestamp': datetime.now().isoformat()
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    logger.log(f"\n验证完成!")
    logger.log(f"JSON报告: {output_file}")
    logger.log(f"详细日志: {LOG_FILE}")

    print(f"\n结果已保存到: {output_file}")
    print(f"详细日志: {LOG_FILE}")
    print("="*60)

    # 保存日志文件
    logger.save()

    return final_report


if __name__ == '__main__':
    asyncio.run(main())
