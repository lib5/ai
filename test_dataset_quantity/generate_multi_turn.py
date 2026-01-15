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

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.true_react_agent import TrueReActAgent


class MultiTurnTestCaseGenerator:
    """多轮测试用例生成器"""

    def __init__(self):
        self.agent = None

    async def initialize(self):
        """初始化"""
        self.agent = TrueReActAgent()
        await self.agent.initialize()

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

            try:
                # 调用GPT生成测试用例
                response = await self.agent.openai_service.chat_completion(
                    messages,
                    max_tokens=4000,
                    temperature=0.1
                )

                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"   ✅ GPT响应完成")

                # 解析JSON响应
                test_case_json = self._extract_json_from_response(content)

                # 构建turn结构
                turn = {
                    "turn_id": turn_number,
                    "user_input": test_case_json["conversation"]["turns"][0]["user_input"],
                    "context": {
                        "requires_context": False,
                        "depends_on": []
                    },
                    "expected_behavior": test_case_json["conversation"]["turns"][0]["expected_behavior"]
                }

                # 如果是图片类型，强制将content替换为原始路径
                if turn["user_input"].get("type") == "image":
                    turn["user_input"]["content"] = query

                turns.append(turn)

                # 存储轮次的重要信息用于后续上下文
                self._store_turn_context(turn, previous_turns_context)

            except Exception as e:
                print(f"   ❌ 第 {turn_number} 轮生成失败: {e}")
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
                                "expected_response": f"无法生成第 {turn_number} 轮的测试用例"
                            }
                        ]
                    }
                }
                turns.append(turn)

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
- 🚨 严格禁止：不要在工具返回数据中编造任何用户未提及的信息
"""

    def _extract_json_from_response(self, response: str) -> Dict:
        """从GPT响应中提取JSON"""
        import re

        # 尝试直接解析JSON
        try:
            return json.loads(response)
        except:
            pass

        # 尝试从代码块中提取JSON
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass

        # 尝试提取第一个完整的JSON对象
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass

        # 如果都无法解析，返回默认结构
        print(f"   ⚠️  无法解析JSON，使用默认结构")
        return {
            "conversation": {
                "turns": [{
                    "user_input": {
                        "type": "text",
                        "content": "无法解析的内容"
                    },
                    "expected_behavior": {
                        "steps": [{
                            "step": 1,
                            "type": "finish",
                            "expected_response": "无法解析响应"
                        }]
                    }
                }]
            }
        }

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
    parser.add_argument('--excel', required=True, help='Excel文件路径（例如：多轮.xlsx）')
    parser.add_argument('--output', default='multi_turn_test_cases.json', help='输出JSON文件名（默认：multi_turn_test_cases.json）')
    args = parser.parse_args()

    if not args.count and not args.all:
        print("错误：必须指定 --count 或 --all 参数")
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
    print("正在初始化GPT-4.1...")
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

    # 处理数据
    for idx in range(start_idx, end_idx):
        try:
            # 获取一行数据（包含多个轮次）
            row_data = df.iloc[idx].to_dict()

            test_case_id = f"MULTI_TURN_{idx:03d}"

            print(f"\n[进度] {idx - start_idx + 1}/{total_count}")
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


if __name__ == "__main__":
    asyncio.run(main())
