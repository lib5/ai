#!/usr/bin/env python3
"""
模拟 _format_chat_history 的行为，测试空消息列表的处理
"""

import json
from typing import List, Dict, Any

def _format_chat_history(messages: List[Dict[str, Any]], max_messages: int = 5) -> str:
    """
    格式化聊天历史为提示词格式（从 true_react_agent.py 复制）
    """
    if not messages:
        return ""

    # 取最近的消息（messages 已经按时间倒序）
    recent_messages = messages[:max_messages]
    # 反转顺序，让旧消息在前
    recent_messages = list(reversed(recent_messages))

    history_lines = []
    for msg in recent_messages:
        role = msg.get("role", "unknown")
        if role == "user":
            # 用户消息
            content = msg.get("content", [])
            if isinstance(content, list):
                text_items = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "input_text"
                ]
                text = " ".join(text_items)
            else:
                text = str(content)
            history_lines.append(f"用户: {text[:200]}")
        elif role == "assistant":
            # 助手消息 - 从 steps 或 content 中提取答案
            answer = ""

            # 方式1: 从 steps 字典的 assistant_answer 字段提取（新的保存格式）
            steps = msg.get("steps", {})
            if isinstance(steps, dict) and "assistant_answer" in steps:
                answer = steps.get("assistant_answer", "")
                if answer:
                    history_lines.append(f"助手: {answer[:200]}")
                    continue

            # 方式2: 从 steps 字典中提取 final_answer（兼容旧格式）
            if isinstance(steps, dict) and "final_answer" in steps:
                answer = steps.get("final_answer", "")
                if answer:
                    history_lines.append(f"助手: {answer[:200]}")
                    continue

            # 方式3: 从 content 中提取答案
            content = msg.get("content", [])
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except:
                    answer = content[:200]
                    if answer:
                        history_lines.append(f"助手: {answer[:200]}")
                        continue
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "output_text":
                        answer = item.get("text", "")
                        if answer:
                            history_lines.append(f"助手: {answer[:200]}")
                        break

            # 方式4: 兼容旧格式 - steps 是列表
            if not answer and isinstance(steps, list):
                for step in steps:
                    if isinstance(step, dict) and step.get("type") == "final_answer":
                        answer = step.get("content", "")
                        if answer:
                            history_lines.append(f"助手: {answer[:200]}")
                        break

            # 方式5: 尝试从 msg 顶层直接提取可能的答案字段
            if not answer:
                for key in ['answer', 'text', 'response', 'message']:
                    if key in msg:
                        answer = str(msg.get(key, ""))
                        if answer:
                            history_lines.append(f"助手: {answer[:200]}")
                        break

    if not history_lines:
        return ""

    return "## 最近对话历史\n" + "\n".join(history_lines) + "\n\n"

def test_format_empty_messages():
    """测试空消息列表的处理"""
    print("=" * 80)
    print("测试 _format_chat_history 处理空消息列表")
    print("=" * 80)

    # 测试1: 空列表
    print("\n测试1: 空消息列表")
    result = _format_chat_history([])
    print(f"结果: '{result}'")
    print(f"长度: {len(result)}")

    # 测试2: 只有用户消息
    print("\n测试2: 只有用户消息")
    user_only_messages = [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "客户拜访的日程你也创建一下"}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "我下周都有哪些安排"}
            ]
        }
    ]
    result = _format_chat_history(user_only_messages)
    print(f"结果:\n{result}")

    # 测试3: 用户+助手消息
    print("\n测试3: 用户+助手消息")
    user_assistant_messages = [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "客户拜访的日程你也创建一下"}
            ]
        },
        {
            "role": "assistant",
            "content": [
                {"type": "output_text", "text": "好的，我来帮你创建客户拜访的日程。"}
            ],
            "steps": {
                "assistant_answer": "好的，我来帮你创建客户拜访的日程。"
            }
        }
    ]
    result = _format_chat_history(user_assistant_messages)
    print(f"结果:\n{result}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_format_empty_messages()
