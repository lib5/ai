#!/usr/bin/env python3
"""
测试结果验证脚本 - 并行处理版本（简洁版）
使用Gemini-3-Flash-Preview验证chat API测试结果的正确性
"""

import json
import asyncio
import aiohttp
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import threading

# 加载.env文件
load_dotenv('/home/libo/chatapi/.env')

# OpenAI 配置（Gemini-3-Flash-Preview）
openai_api_key: str = os.getenv("OPENAI_API_KEY", "sk-hk69mLmsHF6FfIM8cPn2Zitfk0Jca6suzwIptZymPn6h1u6x")
openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://llm.onerouter.pro/v1")
openai_model: str = os.getenv("OPENAI_MODEL", "gemini-3-flash-preview")

# 创建日志目录
SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = LOG_DIR / f"validation_parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# 线程锁用于日志写入
log_lock = threading.Lock()

# 简单日志记录器（支持并行）
class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.buffer = []

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"

        # 线程安全的缓冲
        with log_lock:
            self.buffer.append(log_msg)

    def save(self):
        with log_lock:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.buffer))

logger = Logger(LOG_FILE)

print("="*60)
print("测试结果验证工具 - 并行处理版本 (使用 Gemini-3-Flash-Preview)")
print("="*60)
print()

logger.log("开始验证过程 - 并行版本")
logger.log(f"OpenAI配置:")
logger.log(f"  Base URL: {openai_base_url}")
logger.log(f"  模型: {openai_model}")
logger.log(f"  API Key: {openai_api_key[:10]}...")
logger.log(f"日志文件: {LOG_FILE}")
print()
print("🚀 新增功能：并行处理")
print("  默认并发数：5个")
print("🔧 失败重试机制：")
print("  默认重试次数：5次")
print("  禁用重试：--no-retry")
print("  自定义重试次数：--retry <次数>")
print()


async def validate_single_turn(session, test_case_id, turn_result, turn_index, base_timestamp_with_weekday, logger, previous_turns=None):
    """验证单个turn（支持多轮上下文）

    Args:
        session: HTTP会话
        test_case_id: 测试用例ID
        turn_result: 当前轮的结果
        turn_index: 当前轮索引（从0开始）
        base_timestamp_with_weekday: 基准时间
        logger: 日志记录器
        previous_turns: 前面的轮次数据列表，用于提供上下文
    """
    turn_id = turn_result.get('turn_id', f'turn_{turn_index}')
    user_input = turn_result.get('user_input', {})
    execution_result = turn_result.get('execution_result', {})
    expected_behavior = turn_result.get('expected_behavior', {})

    # 初始化历史轮次列表
    if previous_turns is None:
        previous_turns = []

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

    # 🔧 构建历史对话上下文
    history_context = ""
    if previous_turns:
        history_context = "注意：这是多轮对话中的第" + str(turn_index + 1) + "轮，以下是前面轮次的对话历史供参考：\n\n"
        for i, prev_turn in enumerate(previous_turns):
            history_context += f"### 第{i + 1}轮对话\n"

            # 获取历史轮次的用户输入
            prev_user_input = prev_turn.get('user_input', {})
            if prev_user_input.get('type') == 'text':
                history_context += f"**用户输入**: {prev_user_input.get('content', '')}\n"
            elif prev_user_input.get('type') == 'image':
                history_context += f"**图像输入**: {prev_user_input.get('content', '')}\n"

            # 获取历史轮次的执行结果
            prev_execution_result = prev_turn.get('execution_result', {})
            prev_tool_calls = []
            prev_assistant_responses = []

            if 'raw_data' in prev_execution_result:
                for item in prev_execution_result['raw_data']:
                    if item.get('type') == 'tool' or (item.get('role') == 'assistant' and item.get('type') == 'tool'):
                        content = item.get('content', {})
                        if content.get('status') == 'start':
                            prev_tool_calls.append({
                                'tool_name': content.get('name', ''),
                                'tool_cn': content.get('name_cn', ''),
                                'arguments': content.get('arguments', ''),
                            })
                    elif item.get('type') == 'markdown' or (item.get('role') == 'assistant' and item.get('type') == 'markdown'):
                        prev_assistant_responses.append({
                            'content': item.get('content', ''),
                        })

            # 记录历史工具调用
            if prev_tool_calls:
                history_context += f"**实际调用的工具**: {json.dumps(prev_tool_calls, ensure_ascii=False, indent=2)}\n"
            else:
                history_context += "**实际调用的工具**: []\n"

            # 记录历史Assistant响应
            if prev_assistant_responses:
                history_context += "**Assistant响应**:\n"
                for j, response in enumerate(prev_assistant_responses):
                    content = response.get('content', '')
                    history_context += f"- {content}\n"

            history_context += "\n"

    prompt = f"""
你是一个专业的AI系统测试验证专家。请分析以下测试用例的执行结果，判断其正确性。

## 测试用例信息
测试ID: {test_case_id}
{input_display}

## 时间信息
测试基准时间: {base_timestamp_with_weekday}
注：用户输入中的"今天下午两点"等相对时间表达应基于此基准时间来判断
**关于时间判断，你必须遵守以下首要规则：**
1.  **忽略期望时间**：  在评估"时间判断准确性"时，**请完全忽略测试用例中"期望执行步骤"里的start_time,它可能与本次评测的基准时间不符，不具备参考价值**
2.  **唯一时间基准**：所有关于"今天"、"明天"、"下周"等相对时间的正确性判断，**有且仅有一个正确标准：即基于下方提供的"测试基准时间"进行推算的结果**。
3.  **验证实际时间**：你只需判断"实际调用的工具"中的时间参数，是否与基于**测试基准时间**推算出的正确时间相匹配，可以远超基准时间 合理就行。
参考下面两个例子 下面两个例子评估错误 虽然与预期不符但是实际结果是正确的 那时间准确性这一项分数应该是10分
- "时间参数严重错误：'后天中午'基于基准时间2026-01-16T10:45:59应为2026-01-18T12:00:00，但实际创建时间为2026-01-18T12:00:00，表面看似正确，但实际上'后天'应为2026-01-18，实际参数是正确的。"

- 用户输入为'下周四'，基准时间为2026-01-16（周五），下周四应为2026-01-22，但实际创建时间为2026-01-22，参数正确，但期望行为中的时间为2026-01-23，期望行为有误。实际执行结果是正确的 时间参数分数应该为高分

## 历史对话上下文
{history_context}

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
    - 使用了错误的参数 判断为错误 如工具调用时使用了错误的参数名 'industry'，导致 Pydantic 校验失败报错
3. **时间判断准确性**: 对于日程相关测试，请重点检查：
   - 实际调用中的时间参数是否基于**测试基准时间**正确转换？如果转化正确 则这项准确性分数满分。请严格应用下方"日期星期计算规则"。
   -  如果期望时间有误但符合实际就要给10分 这种情况下不能输出时间参数严重错误
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
   - `"周X" = 基准时间所在周内的星期X 如果基准时间超过周X 则可以理解为下周X
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

 由于期望的基准时间和评测基准时间不一致 因此一切以评测的基准时间为准 不考虑期望的时间
- **## 注意
-不需要管incomplete状态**，如果一轮对话中incomplete=true，表示这一轮没有调用工具，这是正常的，不影响评估结果 若期望中存在调用工具 需要根据上下文判断是否一定需要调用该工具 若一定需要调用 则判断错误。

## 补充
1. 用户表达出意图就可以调用 不需要明确指出
2. 对于生日的年份可以补全 不算错误
3. 相比于预期可以添加多余参数 只要合理就可以添加
4. id可以不一致
5. 创建人脉时需要去查找人脉 这是正确的  有上下文的情况下，更新人脉时也可以不查找,只要工具结果执行正确即可
6. 提醒时间的格式必须是后面10个值中的一个：-5m​ 表示 5 分钟前； -10m​ 表示 10 分钟前；-15m​ 表示 15 分钟前；-30m​ 表示 30 分钟前；-1h​ 表示 1 小时前；-2h​ 表示 2 小时前；-1d​ 表示 1 天前；-2d​ 表示 2 天前；-1w​ 表示 1 周前；-2w​ 表示 2 周前。单位：d=天，m=分钟，w=周，h=小时 如果不是 那么is_correct必须判为错误
7. 对于日程的时间 如果用户未明确要求，**结束时间、持续时长、提醒时间（reminder_time）可以灵活设置，也可以不设置 因为默认-5m，只要逻辑合理即可。
8. reminder_time、日程结束时间，如果用户问题中没有明确要求这个时长 便可以和预期不一致
9. note不一致但相近也是可以的 如 用户期望为'服务器相关行业'，实际为'服务器'是正确的
10. 对于日程创建的时间 以基准时间为准 如果合理则不需要和期望时间保持一致  如 用户说'今天下午八点'，基准时间为2026-01-16，实际却创建在2026-01-16 20:00:00，期望应为2026-01-16 20:00:00，但期望行为中时间为2026-01-13 20:00:00，期望行为本身有误 因此他的参数提取是正确的 判断为对
11. 期望有误但执行结果合理 则不需要和期望保持一致 可以判断为正确
12. full_day可以是日期 (start_time、end_time)与full_day有其中一个就可以
13. 响应内容在"content"字段中查看
14. 待测试数据可以与预期不一致 对于复杂任务chunks_count>=14 ，只要最后都完成了用户的意图 都可以算正确，使用的工具、参数可以和期望不一致
15. 多轮对话中如果可以从前几轮直接获取得到数据，Assistant也可以不需要调用查询工具直接得到结果 如第一轮说了江涵的生日和手机号 第二轮可以直接输出这两条数据 也可以通过搜索联系人得到
16. 多余创建的日程和人脉 合理也可以接受 不能给低分
17. 根据id查找的不会误删、找错联系人
18. 工具选择和参数提取均未发生，但是最后输出的结果合理，过程合理(从上下文中得到信息) 这不影响影响业务逻辑和响应完整性
19. **多路径格式支持**: 当expected_behavior为数组时，每个元素包含"description"和"steps"，表示一个可能的执行路径。只要实际执行符合任一路径，即判定正确。
20. 用户提供具体时间点（如中午、下午）时 使用 start_time 和 end_time 而非 full_day 如果使用full_day则时间参数严重错误
21. 对于查询人脉/日程 查找范围不能特别限制 否则算错误 如 用户问产品例会安排了吗？ 搜索条件应该只有\"title\": \"产品例会\" 而没有时间 因为可能会漏掉一些日程


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
  "detailed_analysis": "简要分析说明(50字以内)"
}}
```
"""

    url = f"{openai_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": openai_model,
        "messages": [
            {"role": "system", "content": "你是一个专业的AI系统测试验证专家。你需要分析测试用例的执行结果，判断其正确性，并以JSON格式返回结果。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 4000
    }

    # 记录发送给Gemini的请求信息
    logger.log("-" * 60)
    logger.log(f"第{turn_index + 1}轮 - 发送给Gemini的请求:")
    logger.log(f"URL: {url}")
    logger.log(f"完整Prompt:")
    logger.log(prompt)
    logger.log("-" * 60)

    try:
        async with session.post(url, headers=headers, json=data, timeout=60) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.log(f"API调用失败: {response.status} - {error_text}", "ERROR")
                raise Exception(f"OpenAI API调用失败: {response.status} - {error_text}")

            result = await response.json()
            validation_text = result['choices'][0]['message']['content']

            # 记录Gemini响应
            logger.log("Gemini原始响应:")
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

        # 构建历史轮次数据（前面的所有轮次）
        previous_turns = turn_results[:turn_index] if turn_index > 0 else []

        turn_validation_result = await validate_single_turn(
            session, test_case_id, turn_result, turn_index,
            base_timestamp_with_weekday, logger, previous_turns
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


# 并发处理单个测试用例
async def process_single_case(args):
    """并发处理单个测试用例的包装函数"""
    session, test_case, case_index, enable_retry, max_retries = args
    return await validate_single_case_with_retry(session, test_case, case_index, enable_retry, max_retries)


async def validate_single_case_with_retry(session, test_case, case_index, enable_retry, max_retries):
    """验证单个测试用例并处理重试"""
    result = await validate_single_case(session, test_case, case_index)

    # 重试机制
    if enable_retry and result['status'] != 'success':
        retry_attempt = 1
        retry_cases = [(case_index, test_case)]

        while retry_cases and retry_attempt <= max_retries:
            logger.log(f"🔄 第{retry_attempt}轮重试开始，共{len(retry_cases)}个用例")
            current_retry_cases = retry_cases.copy()
            retry_cases = []

            for original_index, test_case_item in current_retry_cases:
                retry_result = await validate_single_case(session, test_case_item, original_index)

                if retry_result['status'] != 'success':
                    if retry_attempt < max_retries:
                        retry_cases.append((original_index, test_case_item))
                    logger.log(f"❌ 第{retry_attempt}轮重试仍失败")
                else:
                    result = retry_result
                    logger.log(f"✅ 重试成功！用例 {test_case.get('test_case_id')} 现在验证通过")
                    break

            retry_attempt += 1

    return result


async def main():
    """主函数"""
    # 记录开始时间
    start_time = time.time()
    start_datetime = datetime.now()

    parser = argparse.ArgumentParser(description='测试结果验证脚本 - 并行版本')
    parser.add_argument('--input', '-i', type=str, help='输入测试结果文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出验证报告文件路径 (可选，将自动生成)')
    parser.add_argument('--limit', '-l', type=int, help='限制验证的测试用例数量 (默认: 全部)')
    parser.add_argument('--timestamp', '-t', type=str, help='时间戳 (可选，用于生成文件名)')
    parser.add_argument('--retry', '-r', type=int, default=5, help='失败重试次数 (默认: 5次)')
    parser.add_argument('--no-retry', action='store_true', help='禁用重试机制')
    parser.add_argument('--concurrency', '-c', type=int, default=5, help='并发数 (默认: 5个并发)')
    args = parser.parse_args()

    # 确保输出目录存在
    import os
    os.makedirs("validation_reports", exist_ok=True)

    # 自动发现输入文件
    if args.input:
        test_file = args.input
    else:
        # 智能查找最新的测试结果文件
        import glob
        pattern = str(SCRIPT_DIR / "test_results_merged_*.json")
        matching_files = glob.glob(pattern)

        if matching_files:
            # 获取最新的文件
            test_file = max(matching_files, key=os.path.getmtime)
            print(f"🔍 自动发现输入文件: {test_file}")
        else:
            print("❌ 未找到测试结果文件，请使用 --input 参数指定")
            return

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

    # 限制测试用例数量
    if args.limit:
        test_cases_to_validate = test_cases[:args.limit]
        print(f"将验证前 {args.limit} 个测试用例")
    else:
        test_cases_to_validate = test_cases
        print(f"将验证全部 {len(test_cases)} 个测试用例")

    print()

    # 并发配置
    enable_retry = not args.no_retry
    max_retries = args.retry if enable_retry else 0
    concurrency = args.concurrency

    logger.log(f"并发机制: 启用, 并发数: {concurrency}")
    logger.log(f"重试机制: {'启用' if enable_retry else '禁用'}, 最大重试次数: {max_retries}")

    print(f"🚀 并发数: {concurrency}")
    print(f"🔧 重试机制: {'启用' if enable_retry else '禁用'}, 最大重试次数: {max_retries}")
    print()

    results = []
    problem_cases = []

    # 🔄 执行并行验证
    try:
        async with aiohttp.ClientSession() as session:
            # 准备并发任务
            tasks = []
            semaphore = asyncio.Semaphore(concurrency)
            completed_count = 0
            total_count = len(test_cases_to_validate)

            # 实时进度显示
            progress_lock = asyncio.Lock()

            async def update_progress():
                async with progress_lock:
                    nonlocal completed_count
                    progress = (completed_count / total_count * 100) if total_count > 0 else 0
                    bar_length = 40
                    filled_length = int(bar_length * completed_count / total_count)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    print(f"\r🚀 验证进度: |{bar}| {completed_count}/{total_count} ({progress:.1f}%)", end='', flush=True)

            # 初始化进度条
            print(f"🚀 验证进度: |{'-' * 40}| 0/{total_count} (0.0%)")
            print("🚀 开始并行验证...")
            print()

            # 创建所有任务
            for i, test_case in enumerate(test_cases_to_validate):
                # 使用信号量包装
                async def create_task(sem, session, test_case, case_index):
                    nonlocal completed_count
                    async with sem:
                        result = await validate_single_case_with_retry(
                            session, test_case, case_index, enable_retry, max_retries
                        )

                        # 完成任务后更新进度
                        async with progress_lock:
                            completed_count += 1
                            count = completed_count

                        # 更新进度条
                        await update_progress()

                        # 实时显示完成的结果
                        print(f"\n✅ 完成 #{count}: {result['test_case_id']}")
                        print(f"   状态: {result['status']}, 正确性: {result['is_correct']}, 评分: {result['score']}/10")
                        if result['issues']:
                            print(f"   问题: {', '.join(result['issues'][:2])}")

                        return result

                task = create_task(semaphore, session, test_case, i)
                tasks.append(task)

            start_parallel_time = time.time()

            # 并发执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)

            parallel_time = time.time() - start_parallel_time
            print(f"\n✅ 并行验证完成！用时: {parallel_time:.2f}秒")

        # 处理结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.log(f"测试用例 {i+1} 处理失败: {result}", "ERROR")
                final_results.append({
                    'test_case_id': test_cases_to_validate[i].get('test_case_id', 'unknown'),
                    'is_correct': 'error',
                    'score': 0,
                    'dimension_scores': {},
                    'issues': [f'处理异常: {str(result)}'],
                    'suggestions': [],
                    'reasoning': '',
                    'status': 'failed',
                    'turn_count': 0,
                    'successful_turns': 0,
                    'turn_details': []
                })
            else:
                final_results.append(result)

                # 记录问题用例
                if result['is_correct'] == '错误':
                    problem_cases.append(result)

    except Exception as e:
        logger.log(f"验证过程中发生错误: {e}", "ERROR")
        print(f"验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return

    # 打印摘要
    logger.log("="*80)
    logger.log("验证摘要")
    logger.log("="*80)
    print("\n" + "="*60)
    print("验证摘要")
    print("="*60)

    total = len(final_results)
    successful = sum(1 for r in final_results if r['status'] == 'success')
    failed = total - successful

    logger.log(f"总测试用例数: {total}")
    logger.log(f"验证成功: {successful}")
    logger.log(f"验证失败: {failed}")
    print(f"总测试用例数: {total}")
    print(f"验证成功: {successful}")
    print(f"验证失败: {failed}")

    # 计算正确率
    correct = sum(1 for r in final_results if r['status'] == 'success' and r['is_correct'] == '正确')
    wrong = sum(1 for r in final_results if r['status'] == 'success' and r['is_correct'] == '错误')
    accuracy = (correct / total * 100) if total > 0 else 0

    if successful > 0:
        logger.log(f"  正确: {correct}")
        logger.log(f"  错误: {wrong}")
        logger.log(f"  正确率: {accuracy:.1f}%")
        print(f"  正确: {correct}")
        print(f"  错误: {wrong}")
        print(f"  正确率: {accuracy:.1f}%")

        avg_score = sum(r['score'] for r in final_results if r['status'] == 'success') / successful
        logger.log(f"平均评分: {avg_score:.2f}/10")
        print(f"平均评分: {avg_score:.2f}/10")

    # 保存结果
    timestamp = args.timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.output:
        output_file = args.output
    else:
        output_file = f"validation_reports/validation_report_parallel_{timestamp}.json"

    final_report = {
        'validation_summary': {
            'total_cases': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'correct_count': correct,
            'wrong_count': wrong,
            'accuracy_rate': accuracy,
            'average_score': avg_score if successful > 0 else 0,
            'parallel_config': {
                'concurrency': concurrency,
                'retry_enabled': enable_retry,
                'max_retries': max_retries
            }
        },
        'validation_details': final_results,
        'problem_cases': problem_cases,
        'log_file': str(LOG_FILE),
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

    # 计算并显示执行时间
    end_time = time.time()
    end_datetime = datetime.now()
    execution_time = end_time - start_time

    print("\n" + "="*60)
    print("⏱️  执行时间统计")
    print("="*60)
    print(f"开始时间: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结束时间: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总执行时间: {execution_time:.2f}秒 ({execution_time/60:.2f}分钟)")
    print(f"平均每个测试: {execution_time/len(final_results):.2f}秒")
    if parallel_time > 0:
        print(f"并行优化提升: {(len(final_results) * 10) / parallel_time:.1f} 个测试/秒")
    print("="*60)

    return final_report


if __name__ == '__main__':
    print("""
🚀 并行处理版本使用说明：

1. 基本使用（5个并发）：
   python validate_test_gemini_results_parallel.py

2. 自定义并发数（例如10个并发）：
   python validate_test_gemini_results_parallel.py --concurrency 10

3. 禁用重试机制：
   python validate_test_gemini_results_parallel.py --no-retry

4. 自定义重试次数（例如3次）：
   python validate_test_gemini_results_parallel.py --retry 3

5. 指定输入和输出文件：
   python validate_test_gemini_results_parallel.py -i test_results.json -o report.json

6. 限制验证数量（例如只验证前10个）：
   python validate_test_gemini_results_parallel.py --limit 10

组合使用示例：
- 10个并发 + 3次重试：
  python validate_test_gemini_results_parallel.py --concurrency 10 --retry 3

- 5个并发 + 禁用重试：
  python validate_test_gemini_results_parallel.py --concurrency 5 --no-retry

优势：
✅ 大幅提升验证效率（5-10倍速度提升）
✅ 智能并发控制，避免API限制
✅ 保持所有原有功能（多路径验证、重试机制等）
✅ 实时进度显示
""")
    asyncio.run(main())
