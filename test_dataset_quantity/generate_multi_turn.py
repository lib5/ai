#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多轮Excel测试用例生成器
- 支持多轮对话的测试用例生成
- 每行是一条多轮测试数据，每列是一个轮次的用户问题

使用方式:
python generate_multi_turn.py --count 2 --excel 多轮.xlsx
python generate_multi_turn.py --all --excel 多轮.xlsx
"""

import json
import asyncio
import sys
import os
import pandas as pd
import argparse
import base64
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
import openai

# 加载.env文件
load_dotenv('/home/libo/chatapi/.env')

# OpenAI 配置（Gemini-3-Flash-Preview）
openai_api_key: str = os.getenv("OPENAI_API_KEY", "sk-hk69mLmsHF6FfIM8cPn2Zitfk0Jca6suzwIptZymPn6h1u6x")
openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://llm.onerouter.pro/v1")
openai_model: str = os.getenv("OPENAI_MODEL", "gemini-3-flash-preview")


class MultiTurnTestCaseGenerator:
    """多轮测试用例生成器"""

    def __init__(self):
        self.client = None

    async def initialize(self):
        """初始化"""
        print(f"正在初始化Gemini-3-Flash-Preview...")
        print(f"  Base URL: {openai_base_url}")
        print(f"  模型: {openai_model}")
        print(f"  API Key: {openai_api_key[:10]}...")

        self.client = openai.AsyncOpenAI(
            api_key=openai_api_key,
            base_url=openai_base_url
        )

    def _generate_unique_user_id(self) -> str:
        """生成唯一的user_id"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        return f"user_{timestamp}"

    def _is_image_url(self, text: str) -> bool:
        """判断是否为本地图片文件"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

        # 检查是否为本地图片文件
        if os.path.isfile(text):
            # 检查文件扩展名
            return any(text.lower().endswith(ext) for ext in image_extensions)

        return False

    def _get_current_time_info(self) -> str:
        """获取当前时间信息"""
        current_time = datetime.now()
        current_date_str = current_time.strftime('%Y-%m-%d')
        weekday_str = ['一', '二', '三', '四', '五', '六', '日'][current_time.weekday()]
        return f"今天当前时间：{current_date_str}，今天是星期{weekday_str}"

    def _download_and_convert_image(self, url: str) -> str:
        """读取本地图片并转换为base64格式"""
        try:
            print(f"   📁 正在读取本地图片: {url[:80]}...")

            # 检查文件是否存在
            if not os.path.isfile(url):
                print(f"   ❌ 文件不存在: {url}")
                return ""

            # 读取本地图片文件
            with open(url, 'rb') as f:
                image_data = f.read()

            # 根据文件扩展名确定content_type
            if url.lower().endswith('.png'):
                content_type = 'image/png'
            elif url.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif url.lower().endswith('.jpg') or url.lower().endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif url.lower().endswith('.webp'):
                content_type = 'image/webp'
            else:
                content_type = 'image/jpeg'  # 默认

            # 转换为base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            base64_data = f"data:{content_type};base64,{image_base64}"

            print(f"   ✅ 本地图片读取成功，大小: {len(image_data)} bytes")
            return base64_data

        except Exception as e:
            print(f"   ❌ 图片读取失败: {e}")
            return ""

    def _build_prompt_for_turn(self, query: str, turn_number: int, total_turns: int, is_first_turn: bool, previous_context: List[Dict] = None) -> str:
        """为特定轮次构建提示词"""
        time_info = self._get_current_time_info()

        if self._is_image_url(query):
            image_base64 = self._download_and_convert_image(query)

            if image_base64:
                base_prompt = f"""请分析以下本地图片内容，并生成相应的测试用例JSON：

{time_info}

图片文件：{query}
图片内容已转换为base64格式，请分析图片中的信息。

⚠️ 重要：不要生成 image_analysis 工具调用步骤。
直接基于图片内容生成测试用例，图片内容应该被Agent直接理解并执行相应操作。

🚨 重要约束：
1. 只能使用图片中明确显示的信息
2. 🚫 严格禁止编造虚假数据：公司、职位、邮箱、地址等
3. 🚫 如果工具返回数据包含未提及的字段，必须使用null或空值
4. 🚫 不要编造联系人ID、创建时间等虚假信息

这是第 {turn_number} 轮对话（总共 {total_turns} 轮）。

请严格按照指定的JSON格式输出测试用例。"""

                # 如果不是第一轮，添加上下文信息
                if not is_first_turn and previous_context:
                    context_info = self._format_previous_context(previous_context)
                    user_prompt = f"""请分析以下本地图片内容，并生成相应的测试用例JSON：

{time_info}

上下文信息：
{context_info}

图片文件：{query}
图片内容已转换为base64格式，请分析图片中的信息。

⚠️ 重要：不要生成 image_analysis 工具调用步骤。
直接基于图片内容生成测试用例，图片内容应该被Agent直接理解并执行相应操作。

🚨 重要约束：
1. 只能使用图片中明确显示的信息，以及前面轮次中已经创建或获取的信息
2. 🚫 严格禁止编造虚假数据：公司、职位、邮箱、地址等
3. 🚫 如果工具返回数据包含未提及的字段，必须使用null或空值
4. 🚫 不要编造联系人ID、创建时间等虚假信息

这是第 {turn_number} 轮对话（总共 {total_turns} 轮）。

请严格按照指定的JSON格式输出测试用例。"""
                else:
                    user_prompt = base_prompt
            else:
                base_prompt = f"""请根据以下本地图片文件信息，生成相应的测试用例JSON：

{time_info}

⚠️ 重要说明：图片文件无法读取。

图片文件：{query}

🚨 重要约束：
1. 🚫 严格禁止编造虚假数据：公司、职位、邮箱、地址等
2. 🚫 如果工具返回数据包含未提及的字段，必须使用null或空值
3. 🚫 不要编造联系人ID、创建时间等虚假信息

⚠️ 重要：不要生成 image_analysis 工具调用步骤。
请生成一个合理的测试用例。

这是第 {turn_number} 轮对话（总共 {total_turns} 轮）。

请严格按照指定的JSON格式输出测试用例。"""

                # 如果不是第一轮，添加上下文信息
                if not is_first_turn and previous_context:
                    context_info = self._format_previous_context(previous_context)
                    user_prompt = f"""请根据以下本地图片文件信息，生成相应的测试用例JSON：

{time_info}

上下文信息：
{context_info}

⚠️ 重要说明：图片文件无法读取。

图片文件：{query}

🚨 重要约束：
1. 🚫 严格禁止编造虚假数据：公司、职位、邮箱、地址等
2. 🚫 如果工具返回数据包含未提及的字段，必须使用null或空值
3. 🚫 不要编造联系人ID、创建时间等虚假信息

⚠️ 重要：不要生成 image_analysis 工具调用步骤。
请生成一个合理的测试用例。

这是第 {turn_number} 轮对话（总共 {total_turns} 轮）。

请严格按照指定的JSON格式输出测试用例。"""
                else:
                    user_prompt = base_prompt
        else:
            # 构建基础提示
            base_prompt = f"""请分析以下用户查询，并生成相应的测试用例JSON：

{time_info}

用户查询：{query}

这是第 {turn_number} 轮对话（总共 {total_turns} 轮）。

🚨 重要约束：
1. 只能使用用户明确提到的信息（姓名、生日、电话等）
2. 🚫 严格禁止编造虚假数据：公司、职位、邮箱、地址等
3. 🚫 如果工具返回数据包含未提及的字段，必须使用null或空值
4. 🚫 不要编造联系人ID、创建时间等虚假信息

请严格按照指定的JSON格式输出测试用例。"""

            # 如果不是第一轮，添加上下文信息
            if not is_first_turn and previous_context:
                context_info = self._format_previous_context(previous_context)
                user_prompt = f"""请分析以下用户查询，并生成相应的测试用例JSON：

{time_info}

上下文信息：
{context_info}

用户查询：{query}

这是第 {turn_number} 轮对话（总共 {total_turns} 轮）。

🚨 重要约束：
1. 只能使用用户明确提到的信息，以及前面轮次中已经创建或获取的信息
2. 🚫 严格禁止编造虚假数据：公司、职位、邮箱、地址等
3. 🚫 如果工具返回数据包含未提及的字段，必须使用null或空值
4. 🚫 不要编造联系人ID、创建时间等虚假信息

请严格按照指定的JSON格式输出测试用例。"""
            else:
                user_prompt = base_prompt

        return user_prompt

    def _format_previous_context(self, previous_context: List[Dict]) -> str:
        """格式化前面轮次的上下文信息"""
        if not previous_context:
            return ""

        context_parts = []
        for ctx in previous_context:
            if ctx['type'] == 'contact_created':
                contact_info = ctx['contact_info']
                context_parts.append(f"- 在第{ctx['turn_id']}轮已创建联系人：{contact_info['name']}")
                for key, value in contact_info.items():
                    if key != 'name' and value is not None:
                        context_parts.append(f"  • {key}: {value}")
            elif ctx['type'] == 'contact_searched':
                contact_info = ctx['contact_info']
                context_parts.append(f"- 在第{ctx['turn_id']}轮已搜索到联系人：{contact_info['name']}")
                for key, value in contact_info.items():
                    if key != 'name' and value is not None:
                        context_parts.append(f"  • {key}: {value}")
            elif ctx['type'] == 'schedule_created':
                schedule_info = ctx['schedule_info']
                context_parts.append(f"- 在第{ctx['turn_id']}轮已创建日程：{schedule_info['title']}")
                for key, value in schedule_info.items():
                    if key != 'title' and value is not None:
                        context_parts.append(f"  • {key}: {value}")

        return "\n".join(context_parts) if context_parts else ""

    def _store_turn_context(self, turn: Dict, previous_context: List[Dict]):
        """存储轮次的上下文信息"""
        steps = turn.get("expected_behavior", {}).get("steps", [])

        for step in steps:
            if step.get("type") == "tool_result":
                result_data = step.get("result", {}).get("data", {})

                # 如果是创建联系人
                if "name" in result_data and "id" in result_data:
                    # 提取有用的信息
                    contact_info = {
                        "name": result_data.get("name"),
                        "birthday": result_data.get("birthday"),
                        "phone": result_data.get("phone"),
                        "email": result_data.get("email"),
                        "company": result_data.get("company"),
                        "position": result_data.get("position"),
                        "notes": result_data.get("notes")
                    }
                    # 过滤掉None值
                    contact_info = {k: v for k, v in contact_info.items() if v is not None}

                    previous_context.append({
                        "type": "contact_created",
                        "turn_id": turn["turn_id"],
                        "contact_info": contact_info
                    })

                # 如果是搜索联系人
                elif "contacts" in result_data:
                    contacts = result_data["contacts"]
                    if contacts and isinstance(contacts, list) and contacts[0]:
                        contact = contacts[0]
                        # 提取有用的信息
                        contact_info = {
                            "name": contact.get("name"),
                            "birthday": contact.get("birthday"),
                            "phone": contact.get("phone"),
                            "email": contact.get("email"),
                            "company": contact.get("company"),
                            "position": contact.get("position"),
                            "notes": contact.get("notes")
                        }
                        # 过滤掉None值
                        contact_info = {k: v for k, v in contact_info.items() if v is not None}

                        previous_context.append({
                            "type": "contact_searched",
                            "turn_id": turn["turn_id"],
                            "contact_info": contact_info
                        })

                # 如果是创建日程
                elif "title" in result_data and "id" in result_data:
                    schedule_info = {
                        "title": result_data.get("title"),
                        "description": result_data.get("description"),
                        "start_time": result_data.get("start_time"),
                        "end_time": result_data.get("end_time"),
                        "location": result_data.get("location"),
                        "category": result_data.get("category")
                    }
                    # 过滤掉None值
                    schedule_info = {k: v for k, v in schedule_info.items() if v is not None}

                    previous_context.append({
                        "type": "schedule_created",
                        "turn_id": turn["turn_id"],
                        "schedule_info": schedule_info
                    })

    async def generate_multi_turn_test_case(self, row_data: Dict, test_case_id: str) -> Dict:
        """生成多轮测试用例"""
        # 生成唯一的user_id
        unique_user_id = self._generate_unique_user_id()

        # 获取所有轮次的查询
        turn_queries = []
        for col_name, query in row_data.items():
            if pd.notna(query) and str(query).strip():
                turn_queries.append(str(query).strip())

        if not turn_queries:
            raise ValueError("没有找到有效的查询数据")

        total_turns = len(turn_queries)
        turns = []

        # 存储前面轮次的重要信息，用于后续轮次的上下文
        previous_turns_context = []

        for turn_idx, query in enumerate(turn_queries):
            turn_number = turn_idx + 1
            print(f"\n   📝 生成第 {turn_number} 轮测试用例")
            print(f"      Query: {query[:100]}...")

            # 构建提示词
            user_prompt = self._build_prompt_for_turn(query, turn_number, total_turns, turn_idx == 0, previous_turns_context)

            # 构建请求
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": user_prompt}
            ]

            max_retries = 5
            retry_count = 0
            api_success = False

            while retry_count < max_retries and not api_success:
                try:
                    print(f"   🔄 第 {turn_number} 轮第 {retry_count + 1} 次尝试...")
                    # 调用Gemini生成测试用例
                    response = await self.client.chat.completions.create(
                        model=openai_model,
                        messages=messages,
                        max_tokens=4000,
                        temperature=0.1
                    )

                    content = response.choices[0].message.content
                    print(f"   ✅ Gemini API调用成功")
                    print(f"   📄 响应长度: {len(content)} 字符")
                    print(f"   📄 响应预览: {content[:500]}...")

                    # 检查响应是否包含无法理解的提示
                    if self._is_unclear_response(content):
                        print(f"   ⚠️  检测到无法理解的响应，将重试...")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(2 * retry_count)  # 递增等待时间
                            continue

                    # 检查响应是否完整（基本完整性检查）
                    if not self._is_response_complete(content):
                        print(f"   ⚠️  响应可能被截断，将在1秒后重试...")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(1)
                            continue

                    api_success = True

                    # 解析JSON响应 (使用新的重试机制)
                    test_case_json = await self._parse_json_with_retry(content)

                    # 验证JSON结构和解析结果
                    if test_case_json.get("id") == "PARSE_ERROR":
                        print(f"   ⚠️  JSON解析失败，将重试...")
                        retry_count += 1
                        if retry_count < max_retries:
                            await asyncio.sleep(2 * retry_count)
                            continue

                    if "conversation" not in test_case_json or "turns" not in test_case_json["conversation"]:
                        print(f"   ⚠️  JSON结构不完整，使用默认结构")
                        test_case_json = {
                            "id": "STRUCTURE_ERROR",
                            "conversation": {
                                "turns": [{
                                    "user_input": {
                                        "type": "text",
                                        "content": query
                                    },
                                    "context": {
                                        "requires_context": False,
                                        "depends_on": []
                                    },
                                    "expected_behavior": {
                                        "steps": [{
                                            "step": 1,
                                            "type": "finish",
                                            "expected_response": "我正在理解您的需求，请稍等片刻或尝试重新描述您的请求。"
                                        }]
                                    }
                                }]
                            }
                        }

                            # 构建turn结构
                    is_first_turn = (turn_idx == 0)
                    turn = {
                        "turn_id": turn_number,
                        "user_input": test_case_json["conversation"]["turns"][0]["user_input"],
                        "context": {
                            "requires_context": not is_first_turn,
                            "depends_on": list(range(1, turn_number)) if not is_first_turn else []
                        },
                        "expected_behavior": test_case_json["conversation"]["turns"][0]["expected_behavior"]
                    }

                    # 如果是图片类型，强制将content替换为原始路径
                    if turn["user_input"].get("type") == "image":
                        turn["user_input"]["content"] = query

                    turns.append(turn)

                    # 存储轮次的重要信息用于后续上下文
                    self._store_turn_context(turn, previous_turns_context)

                    print(f"   ✅ 第 {turn_number} 轮处理完成")

                except Exception as e:
                    retry_count += 1
                    error_msg = str(e)[:200]
                    print(f"   ❌ 第 {turn_number} 轮第 {retry_count} 次尝试失败: {error_msg}")

                    if retry_count >= max_retries:
                        print(f"   💥 第 {turn_number} 轮达到最大重试次数（{max_retries}），使用错误处理结构")

                        # 创建更详细的错误信息
                        error_response = f"请求处理遇到问题，请稍后重试或重新描述您的需求。（错误次数：{retry_count}）"

                        # 创建基本的turn结构
                        turn = {
                            "turn_id": turn_number,
                            "user_input": {
                                "type": "text",
                                "content": query
                            },
                            "context": {
                                "requires_context": False,
                                "depends_on": []
                            },
                            "expected_behavior": {
                                "steps": [
                                    {
                                        "step": 1,
                                        "type": "finish",
                                        "expected_response": error_response
                                    }
                                ]
                            }
                        }
                        turns.append(turn)
                    else:
                        print(f"   ⏳ 等待 {2 * retry_count} 秒后重试...")
                        await asyncio.sleep(2 * retry_count)

        # 构建最终测试用例
        test_case = {
            "id": test_case_id,
            "user_id": unique_user_id,
            "name": f"多轮对话测试用例 - {len(turns)} 轮",
            "description": f"多轮对话测试，包含 {len(turns)} 个轮次的交互",
            "mode": "multi_turn",
            "conversation": {
                "turns": turns
            },
            "metadata": {
                "conversation_type": "multi_turn",
                "turns": len(turns),
                "context_complexity": "high",
                "required_tools": self._extract_required_tools(turns)
            }
        }

        return test_case

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的测试用例生成器，专门为秘书Agent系统生成测试用例。

## 秘书Agent完整系统信息

### 日期星期对照表（2025年12月-2026年2月）
12月01日 = 星期一 到 12月31日 = 星期三
1月01日 = 星期四 到 1月31日 = 星期六
2月01日 = 星期日 到 2月28日 = 星期六

### 时间计算规则
- 查找某一天是星期几：根据上面的日期范围计算
- "下周"指的是从当前日期开始遇到的第一个周一开始到周日结束的完整周

## 可用工具（秘书Agent会使用）

### 1. contacts_create - 创建联系人
- 参数：name(可选), company(可选), position(可选), phone(可选), email(可选), address(可选), notes(可选), relationship_type(可选), birthday(可选), gender(可选), industry(可选)
- 说明：所有参数都是可选的，可以只提供部分信息

### 2. contacts_update - 更新联系人
- 参数：id(必需), name(可选), company(可选), position(可选), phone(可选), email(可选), address(可选), notes(可选), relationship_type(可选), birthday(可选), gender(可选), industry(可选)
- 说明：id是必需的，其他参数可选

### 3. contacts_delete - 删除联系人
- 参数：id(必需)
- 说明：需要提供联系人ID

### 4. contacts_search - 搜索联系人
- 参数：contact_id(可选), name(可选), company(可选), position(可选), phone(可选), email(可选), address(可选), context_search(可选)
- 说明：所有参数都是可选的，可以模糊查询

### 5. schedules_create - 创建日程
- 参数：title(必需), description(可选), start_time(可选), end_time(可选), full_day(可选), reminder_time(可选), location(可选), category(可选)
- 说明：
  * title是必需的
  * start_time和end_time必须同时设置（要么都填，要么都不填）
  * 不能同时设置start_time/end_time和full_day
  * description必须包含日程的大概内容、日程的相关人员

### 6. schedules_update - 更新日程
- 参数：id(必需), title(可选), description(可选), start_time(可选), end_time(可选), full_day(可选), reminder_time(可选), location(可选), category(可选)
- 说明：id是必需的，其他参数可选

### 7. schedules_delete - 删除日程
- 参数：id(必需)
- 说明：需要提供日程ID

### 8. schedules_search - 搜索日程
- 参数：title(可选), description(可选), start_time(可选), end_time(可选), location(可选), category(可选), query(可选)
- 说明：
  * 至少要包含一个以上的参数
  * 如果有start_time参数必须设置end_time参数
  * end_time值默认是start_time的当天的最后时刻
  * 优先使用query以外的参数，如果选择了除query以外的参数就不要再使用query参数了


### 9. finish - 完成任务并返回最终答案
- 参数：answer(必需)
- 说明：当已经有足够信息回答问题时使用

## 秘书Agent规则

### 核心规则
1. 每次迭代只能选择一个工具
2. 当认为已经可以回答问题时，使用finish工具并提供完整答案
3. 不能连续使用同一个工具超过3次
4. 如果一个工具调用失败，可以尝试使用其他工具
5. 时间相关查询可以参考日期星期对照表

## 测试用例生成任务

### 输出：完整的测试用例JSON

### 分析步骤
1. **理解查询意图**：分析用户想要完成什么任务
2. **选择合适工具**：根据意图选择最合适的工具
3. **确定工具调用**：根据操作类型选择合适的工具
4. **构建预期行为**：设计完整的ReAct流程（思考-行动-观察）
5. **处理时间信息**：正确处理相对时间（如下周、明天下午等）
6. **遵循规则**：确保工具调用符合所有约束条件

## 测试用例JSON格式
```json
{
  "id": "TEST_CASE_ID",
  "user_id": "user_18600241181",
  "name": "测试用例名称",
  "description": "测试用例描述",
  "mode": "single_turn",
  "conversation": {
    "turns": [
      {
        "turn_id": 1,
        "user_input": {
          "type": "text | image | mixed",
          "content": "用户输入内容"
        },
        "context": {
          "requires_context": false,
          "depends_on": []
        },
        "expected_behavior": {
          "steps": [
            {
              "step": 1,
              "type": "tool_call",
              "tool_name": "工具名称",
              "parameters": {
                "参数": "值"
              }
            },
            {
              "step": 2,
              "type": "tool_result",
              "result": {
                "success": true,
                "data": {
                  "返回数据": "模拟的真实返回数据"
                }
              }
            },
            {
              "step": 3,
              "type": "finish",
              "expected_response": "用户期望看到的最终回复"
            }
          ]
        }
      }
    ]
  },
  "metadata": {
    "conversation_type": "single_turn",
    "turns": 1,
    "context_complexity": "low | medium | high",
    "required_tools": ["工具1", "工具2"]
  }
}
```

## 输出要求
- 严格分析查询的意图，正确选择工具
- 准确提取查询中的实体信息（姓名、生日、电话等）
- 🚨 重要约束：只能使用用户明确提到的信息，不能编造虚假数据
- 🚨 如果工具返回的数据包含用户未提到的字段，必须使用null或空值
- 根据秘书Agent的ReAct模式设计合理的步骤流程
- 每两个step是一个工具调用的过程包括输入参数以及工具执行的结果 finish工具只有一个step
- 确保JSON格式正确，字段完整
- 描述要简洁明了
- 只输出JSON，不要包含其他解释性文字
- 不要使用markdown代码块标记
- 确保JSON格式正确，可以直接使用
- 输出工具返回数据要模拟 不能直接返回一句话
- 每条测试都是独立的数据 不需要有任何依赖
- 🚨 user_id必须独一无二：每个测试用例都必须使用不同的user_id，建议使用时间戳格式（如：user_20260113_152922_311）
- 🚨 严格禁止：不要在工具返回数据中编造任何用户未提及的信息
"""

    def _extract_json_from_response(self, response: str) -> Dict:
        """从Gemini响应中提取JSON (已弃用，改用_parse_json_with_retry)"""
        import re

        print(f"   📄 原始响应长度: {len(response)} 字符")
        print(f"   📄 响应前200字符: {response[:200]}...")

        # 尝试直接解析JSON
        try:
            result = json.loads(response)
            print(f"   ✅ 直接JSON解析成功")
            return result
        except Exception as e:
            print(f"   ⚠️  直接JSON解析失败: {str(e)[:50]}")

        # 尝试从代码块中提取JSON - 修复正则表达式处理嵌套大括号
        json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                print(f"   ✅ 从代码块JSON解析成功")
                return result
            except Exception as e:
                print(f"   ⚠️  代码块JSON解析失败: {str(e)[:50]}")

        # 尝试提取第一个完整的JSON对象（改进的正则表达式）
        json_pattern = r'\{(?:[^{}]|\{[^{}]*\})*\}'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                print(f"   ✅ 提取JSON对象解析成功")
                return result
            except Exception as e:
                print(f"   ⚠️  提取JSON对象解析失败: {str(e)[:50]}")
                # 尝试修复常见的JSON格式问题
                fixed_json = self._try_fix_json(match.group())
                if fixed_json:
                    try:
                        result = json.loads(fixed_json)
                        print(f"   ✅ 修复后JSON解析成功")
                        return result
                    except Exception as e2:
                        print(f"   ⚠️  修复后JSON解析仍然失败: {str(e2)[:50]}")

        # 如果都无法解析，返回默认结构
        print(f"   ❌ 所有JSON解析方法都失败，使用默认错误结构")
        # 返回一个完整的、有效格式的JSON结构
        return {
            "id": "PARSE_ERROR",
            "conversation": {
                "turns": [{
                    "user_input": {
                        "type": "text",
                        "content": "无法解析API响应内容"
                    },
                    "context": {
                        "requires_context": False,
                        "depends_on": []
                    },
                    "expected_behavior": {
                        "steps": [{
                            "step": 1,
                            "type": "finish",
                            "expected_response": "我正在理解您的需求，请稍等片刻或尝试重新描述您的请求。"
                        }]
                    }
                }]
            }
        }

    def _try_fix_json(self, json_str: str) -> Optional[str]:
        """尝试修复常见的JSON格式问题"""
        import re
        try:
            # 移除可能的尾随逗号
            fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
            # 修复单引号为双引号
            fixed = re.sub(r"'([^']*)':", r'"\1":', fixed)
            fixed = re.sub(r": '([^']*)'", r': "\1"', fixed)
            # 修复未闭合的字符串
            fixed = self._fix_unclosed_strings(fixed)
            # 修复换行符
            fixed = fixed.replace('\n', '\\n').replace('\r', '\\r')
            # 修复制表符
            fixed = fixed.replace('\t', '\\t')
            return fixed
        except Exception as e:
            print(f"   ⚠️  JSON修复尝试失败: {str(e)[:50]}")
            return None

    def _fix_unclosed_strings(self, json_str: str) -> str:
        """修复未闭合的字符串"""
        # 计算字符串中未闭合的双引号数量
        double_quotes = json_str.count('"') - json_str.count('\\"')
        # 如果是奇数，说明有未闭合的字符串
        if double_quotes % 2 == 1:
            # 在最后添加闭合引号
            json_str = json_str.rstrip() + '"'
        return json_str

    async def _parse_json_with_retry(self, response: str, max_retries: int = 3) -> Dict:
        """使用多种策略重试解析JSON"""
        import json
        import re

        print(f"   📄 开始JSON解析，响应长度: {len(response)} 字符")

        # 策略1: 直接解析
        try:
            result = json.loads(response)
            print(f"   ✅ 策略1成功: 直接JSON解析")
            return result
        except Exception as e:
            print(f"   ⚠️  策略1失败: {str(e)[:100]}")

        # 策略2: 从代码块中提取
        try:
            json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                result = json.loads(match.group(1))
                print(f"   ✅ 策略2成功: 从代码块提取JSON")
                return result
        except Exception as e:
            print(f"   ⚠️  策略2失败: {str(e)[:100]}")

        # 策略3: 提取第一个完整的JSON对象
        try:
            json_pattern = r'\{(?:[^{}]|\{[^{}]*\})*\}'
            match = re.search(json_pattern, response, re.DOTALL)
            if match:
                # 尝试修复JSON
                fixed_json = self._try_fix_json(match.group())
                if fixed_json:
                    result = json.loads(fixed_json)
                    print(f"   ✅ 策略3成功: 提取并修复JSON对象")
                    return result
        except Exception as e:
            print(f"   ⚠️  策略3失败: {str(e)[:100]}")

        # 策略4: 逐行清理和修复
        for retry in range(max_retries):
            try:
                print(f"   🔄 策略4重试 {retry + 1}/{max_retries}")

                # 清理响应文本
                cleaned = response.strip()

                # 如果有markdown代码块标记，提取内容
                if cleaned.startswith('```'):
                    # 移除开头的```和可能的json标记
                    cleaned = re.sub(r'^```[a-zA-Z]*\s*', '', cleaned)
                    # 移除结尾的```
                    cleaned = re.sub(r'\s*```$', '', cleaned)

                # 尝试直接解析
                result = json.loads(cleaned)
                print(f"   ✅ 策略4成功: 清理后解析")
                return result
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"   ⚠️  策略4重试 {retry + 1} 失败: {error_msg}")

                # 如果不是最后一次重试，等待一下
                if retry < max_retries - 1:
                    await asyncio.sleep(0.5)

        # 策略5: 尝试提取部分JSON并补全
        try:
            print(f"   🔄 策略5: 尝试提取部分JSON")

            # 查找第一个{
            first_brace = response.find('{')
            last_brace = response.rfind('}')

            if first_brace != -1 and last_brace != -1:
                partial = response[first_brace:last_brace + 1]

                # 尝试修复
                fixed = self._try_fix_json(partial)
                if fixed:
                    result = json.loads(fixed)
                    print(f"   ✅ 策略5成功: 提取部分JSON并修复")
                    return result
        except Exception as e:
            print(f"   ⚠️  策略5失败: {str(e)[:100]}")
            import traceback
            traceback.print_exc()

        # 所有策略都失败，返回默认错误结构
        print(f"   ❌ 所有JSON解析策略都失败，使用默认错误结构")

        return {
            "id": "PARSE_ERROR",
            "conversation": {
                "turns": [{
                    "user_input": {
                        "type": "text",
                        "content": "无法解析API响应内容"
                    },
                    "context": {
                        "requires_context": False,
                        "depends_on": []
                    },
                    "expected_behavior": {
                        "steps": [{
                            "step": 1,
                            "type": "finish",
                            "expected_response": "我正在理解您的需求，请稍等片刻或尝试重新描述您的请求。"
                        }]
                    }
                }]
            }
        }

    def _is_response_complete(self, response: str) -> bool:
        """检查API响应是否完整"""
        # 基本完整性检查
        # 1. 检查是否有未闭合的大括号
        open_braces = response.count('{')
        close_braces = response.count('}')
        if open_braces != close_braces:
            return False

        # 2. 检查是否有未闭合的方括号
        open_brackets = response.count('[')
        close_brackets = response.count(']')
        if open_brackets != close_brackets:
            return False

        # 3. 检查是否以完整JSON结构结尾（以}结尾）
        stripped = response.strip()
        if not stripped.endswith('}') and not stripped.endswith(']'):
            return False

        # 4. 检查响应长度是否过短（可能截断）
        if len(response) < 200:
            return False

        return True

    def _is_unclear_response(self, response: str) -> bool:
        """检查响应是否包含无法理解的提示"""
        unclear_patterns = [
            "抱歉，我无法理解",
            "无法理解您的请求",
            "重新描述",
            "无法处理",
            "无法解析",
            "我无法理解",
            "抱歉，无法",
            "无法帮助您",
            "无法完成",
            "无法识别",
            "不清楚您的需求",
            "请重新描述",
            "重新提问",
            "I cannot understand",
            "Sorry, I can't",
            "Unable to understand",
            "I'm sorry, I cannot"
        ]

        response_lower = response.lower()
        for pattern in unclear_patterns:
            if pattern.lower() in response_lower:
                return True

        # 检查响应是否过短且没有JSON结构
        if len(response.strip()) < 50 and '{' not in response and '[' not in response:
            return True

        return False

    def _extract_required_tools(self, turns: List[Dict]) -> List[str]:
        """提取所有需要的工具"""
        tools = set()
        for turn in turns:
            steps = turn.get("expected_behavior", {}).get("steps", [])
            for step in steps:
                if step.get("type") == "tool_call":
                    tool_name = step.get("tool_name")
                    if tool_name and tool_name != "finish":
                        tools.add(tool_name)
        return list(tools)


async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='多轮Excel测试用例生成器')
    parser.add_argument('--count', type=int, help='测试指定数量的数据（例如：--count 2）')
    parser.add_argument('--all', action='store_true', help='测试所有数据')
    parser.add_argument('--failed', action='store_true', help='只生成之前失败的测试用例')
    parser.add_argument('--excel', required=True, help='Excel文件路径（例如：多轮.xlsx）')
    parser.add_argument('--output', default='multi_turn_test_cases.json', help='输出JSON文件名（默认：multi_turn_test_cases.json）')
    args = parser.parse_args()

    if not args.count and not args.all and not args.failed:
        print("错误：必须指定 --count、--all 或 --failed 参数")
        return

    print("=" * 80)
    print("多轮Excel测试用例生成器")
    print("=" * 80)
    print("特性：")
    print("  ✓ 支持多轮对话测试用例生成")
    print("  ✓ 每行一条测试数据，每列一个轮次")
    print("  ✓ 本地图片文件自动处理")
    print("  ✓ 动态时间戳")
    print("=" * 80)
    print()

    generator = MultiTurnTestCaseGenerator()

    # 初始化
    print("正在初始化Gemini-3-Flash-Preview...")
    await generator.initialize()
    print("初始化完成！\n")

    # 读取Excel
    excel_path = args.excel
    print(f"📖 读取Excel文件: {excel_path}")
    df = pd.read_excel(excel_path)
    print(f"   总行数: {len(df)}")
    print(f"   列名: {df.columns.tolist()}\n")

    # 确定要处理的数据范围
    if args.all:
        print(f"🚀 开始生成多轮测试用例 (全部数据)")
        start_idx = 0
        end_idx = len(df)
        total_count = end_idx - start_idx
    elif args.failed:
        print(f"🚀 开始生成多轮测试用例 (只重新生成失败的用例)")
        # 有问题的测试用例对应的行索引
        # MULTI_TURN_028, MULTI_TURN_034
        failed_indices = [1, 7]  # 对应Excel中的行号-1
        start_idx = min(failed_indices)
        end_idx = max(failed_indices) + 1
        total_count = len(failed_indices)
        print(f"   失败的行索引: {failed_indices}")
    else:
        count = args.count
        print(f"🚀 开始生成多轮测试用例 (指定数量: {count})")
        start_idx = 0
        end_idx = min(count, len(df))
        total_count = count

    print("=" * 80)

    all_test_cases = []
    successful = 0
    failed = 0

    # 确定要处理的具体行
    if args.failed:
        # 只处理失败的行
        indices_to_process = [1, 7]  # Excel行索引-1
    else:
        # 处理指定范围内的所有行
        indices_to_process = list(range(start_idx, end_idx))

    # 处理数据
    for idx in indices_to_process:
        try:
            # 获取一行数据（包含多个轮次）
            row_data = df.iloc[idx].to_dict()

            test_case_id = f"MULTI_TURN_{idx + 27:03d}"

            print(f"\n[进度] {indices_to_process.index(idx) + 1}/{total_count}")
            print(f"   测试用例ID: {test_case_id}")
            print(f"   User ID将使用: {generator._generate_unique_user_id()[:30]}...")

            # 计算轮次数量
            turn_count = len([v for v in row_data.values() if pd.notna(v) and str(v).strip()])
            print(f"   轮次数量: {turn_count}")

            test_case = await generator.generate_multi_turn_test_case(row_data, test_case_id)

            # 添加到数组
            all_test_cases.append(test_case)

            print(f"✅ 成功生成多轮测试用例")
            print(f"   实际User ID: {test_case['user_id']}")
            print(f"   轮次数量: {test_case['metadata']['turns']}")
            successful += 1

        except Exception as e:
            print(f"❌ 失败: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1

    # 保存到JSON文件
    if args.failed:
        # 如果是重新生成失败的用例，使用不同的输出文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'multi_turn_failed_retries_{timestamp}.json'
    else:
        output_file = args.output

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_test_cases, f, ensure_ascii=False, indent=2)

    # 总结
    print("\n" + "=" * 80)
    print("📊 多轮测试用例生成完成")
    print("=" * 80)
    print(f"✅ 成功: {successful} 个")
    print(f"❌ 失败: {failed} 个")
    print(f"📁 总计: {successful + failed} 个")
    print(f"\n📄 输出文件: {output_file}")
    print(f"📊 JSON结构: 数组包含 {len(all_test_cases)} 个多轮测试用例")
    print("\n📝 特点:")
    print(f"   • 每个测试用例都有唯一的user_id")
    print(f"   • 支持多轮对话")
    print(f"   • 本地图片文件自动处理")
    print(f"   • 动态时间戳")
    print(f"\n🔧 使用方式:")
    print(f"   • 测试前2条: python generate_multi_turn.py --count 2 --excel {args.excel}")
    print(f"   • 测试所有数据: python generate_multi_turn.py --all --excel {args.excel}")
    print(f"   • 重新生成失败用例: python generate_multi_turn.py --failed --excel {args.excel}")


if __name__ == "__main__":
    asyncio.run(main())
