#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
秘书Agent测试用例生成器（使用GPT-4.1动态生成）

根据自然语言查询调用GPT-4.1生成JSON测试用例，用于测试秘书agent的功能。
使用完整的秘书Agent工具和规则信息。
"""

import json
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.true_react_agent import TrueReActAgent


class GPTBasedTestCaseGenerator:
    """基于GPT-4.1的测试用例生成器"""

    def __init__(self):
        self.agent = None
        self.user_id = "user_18600241181"

    async def initialize(self):
        """初始化GPT-4.1 agent"""
        self.agent = TrueReActAgent()
        await self.agent.initialize()

    async def generate_test_case(self, query: str, test_case_id: Optional[str] = None) -> Dict:
        """使用GPT-4.1生成测试用例"""
        if not test_case_id:
            test_case_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 构建提示词，让GPT-4.1分析查询并生成测试用例
        system_prompt = self._build_generation_prompt()
        user_prompt = f"""请分析以下用户查询，并生成相应的测试用例JSON：

用户查询：{query}

请严格按照指定的JSON格式输出测试用例。"""

        # 调用GPT-4.1
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        print(f"\n{'='*80}")
        print(f"[GPT-4.1] 开始分析查询并生成测试用例")
        print(f"{'='*80}")

        # 使用agent的模型服务
        response = await self.agent.openai_service.chat_completion(
            messages,
            max_tokens=4000,
            temperature=0.1
        )

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        print(f"\n[GPT-4.1 输出]")
        print(f"{'='*80}")
        print(content)
        print(f"{'='*80}\n")

        # 尝试解析JSON
        try:
            # 处理markdown代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            content = content.strip()
            test_case = json.loads(content)

            # 添加必要的字段
            test_case["id"] = test_case_id
            test_case["user_id"] = self.user_id

            return test_case

        except json.JSONDecodeError as e:
            print(f"[错误] JSON解析失败: {e}")
            print(f"[原始内容]: {content}")
            raise

    def _build_generation_prompt(self) -> str:
        """构建生成测试用例的系统提示词"""
        return """你是一个专业的测试用例生成器，专门为秘书Agent系统生成测试用例。

## 秘书Agent完整系统信息


### 日期星期对照表（2025年12月-2026年2月）
12月01日 = 星期一 到 12月31日 = 星期三
1月01日 = 星期四 到 1月31日 = 星期六
2月01日 = 星期日 到 2月28日 = 星期六

### 时间计算规则
- 查找某一天是星期几：直接查看上方对照表
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

### 9. chat_messages_search - 搜索聊天消息
- 参数：query(必需), start_time(可选), end_time(可选)
- 说明：query是必需的

### 10. finish - 完成任务并返回最终答案
- 参数：answer(必需)
- 说明：当已经有足够信息回答问题时使用

## 秘书Agent规则

### 核心规则
1. 每次迭代只能选择一个工具
2. 当认为已经可以回答问题时，使用finish工具并提供完整答案
3. 如果工具执行失败，考虑其他方案
4. 不要重复使用相同的工具和参数
5. 是智能小秘书，名字叫做Moly
6. 所有回复以结论和行动为先，少解释、不废话、不重复用户已知信息
7. 信息不足时只提出一个最关键的问题
8. 输出必须基于工具调用的结果，不能主观臆断
9. 需要简要回答，节省用户阅读时间

### 工具使用规则
1. 创建日程时不要去调用查询日程工具
2. 用户有修改日程的意思优先考虑schedules_update工具
3. notes参数不能有生日

## 你的任务
分析用户的自然语言查询，生成对应的JSON格式测试用例，用于测试秘书Agent的功能。

## 分析策略
1. **识别操作类型**：创建、搜索、更新、删除联系人或日程等
2. **提取实体信息**：从查询中提取姓名、生日、电话、邮箱、公司等信息
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
  "mode": "single_turn | multi_turn",
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
              "tool_name": "调用的工具名称",
              "parameters": {工具参数}
            },
            {
              "step": 2,
              "type": "tool_result",
              "result": {
                "success": true,
                "data": "工具返回的数据"
              }
            },
            {
              "step": 3,
              "type": "finish",
              "expected_response": "最终回复"
            }
          ]
        }
      }
    ]
  },
  "metadata": {
    "conversation_type": "single_turn | multi_turn",
    "turns": 1,
    "context_complexity": "low | medium | high",
    "required_tools": ["工具1", "工具2"]
  }
}
```

## 输出要求
- 严格分析查询的意图，正确选择工具
- 准确提取查询中的实体信息（姓名、生日、电话等）
- 根据秘书Agent的ReAct模式设计合理的步骤流程
- 每两个step是一个工具调用的过程包括输入参数以及工具执行的结果 finish工具只有一个step
- 确保JSON格式正确，字段完整
- 描述要简洁明了
- 只输出JSON，不要包含其他解释性文字
- 不要使用markdown代码块标记
- 确保JSON格式正确，可以直接使用
- 输出工具返回数据要模拟 不能直接返回一句话
"""


async def main():
    """主函数"""
    print("=" * 80)
    print("基于GPT-4.1的秘书Agent测试用例生成器")
    print("=" * 80)
    print()

    generator = GPTBasedTestCaseGenerator()

    # 初始化agent
    print("正在初始化GPT-4.1...")
    await generator.initialize()
    print("初始化完成！\n")

    # 示例测试用例
    examples = [
        "新建人脉老徐，生日是8月8号"
    ]

    print("示例测试用例：")
    for i, query in enumerate(examples, 1):
        print(f"{i}. {query}")
    print()

    print("-" * 80)
    print()

    # 生成示例测试用例
    for i, query in enumerate(examples, 1):
        print(f"\n{'='*80}")
        print(f"示例 {i}/{len(examples)}: {query}")
        print(f"{'='*80}")

        try:
            test_case = await generator.generate_test_case(
                query,
                f"TEST_GPT_GENERATED_{i:03d}"
            )

            # 保存到文件
            output_file = f"test_case_gpt_generated_{i:03d}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(test_case, f, ensure_ascii=False, indent=2)

            print(f"\n✅ 测试用例已生成并保存到: {output_file}")
            print(f"   ID: {test_case['id']}")
            print(f"   名称: {test_case['name']}")
            print(f"   所需工具: {test_case['metadata']['required_tools']}")

        except Exception as e:
            print(f"\n❌ 生成失败: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 80)
    print("交互模式 - 输入自定义查询")
    print("=" * 80)
    print()

    while True:
        print("请输入查询（或输入 'exit' 退出）：")
        query = input().strip()

        if query.lower() in ['exit', 'quit', 'q']:
            print("再见！")
            break

        if not query:
            print("查询不能为空，请重试。\n")
            continue

        print()
        print("请输入测试用例ID（可选，直接回车使用默认ID）：")
        test_case_id = input().strip() or f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        print()
        print("请输入输出文件名（可选，直接回车使用默认文件名）：")
        output_file = input().strip() or f"test_case_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            # 生成测试用例
            test_case = await generator.generate_test_case(query, test_case_id)

            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(test_case, f, ensure_ascii=False, indent=2)

            print(f"\n✅ 测试用例已生成并保存到: {output_file}")
            print(f"   ID: {test_case['id']}")
            print(f"   名称: {test_case['name']}")
            print(f"   所需工具: {test_case['metadata']['required_tools']}")

        except Exception as e:
            print(f"\n❌ 生成失败: {e}")
            import traceback
            traceback.print_exc()

        print()
        print("-" * 80)
        print()


if __name__ == "__main__":
    asyncio.run(main())
