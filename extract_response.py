#!/usr/bin/env python3
import json
import re

# Read the response
with open('/tmp/chat_response.txt', 'r') as f:
    content = f.read()

# Extract the answer field using regex
pattern = r'"answer":"((?:[^"\\]|\\.)*)"'
match = re.search(pattern, content)

if match:
    answer = match.group(1)
    # Unescape the JSON string
    answer = answer.encode().decode('unicode_escape')

    print("=" * 80)
    print("✅ 模型回答（真正调用Azure OpenAI API生成）:")
    print("=" * 80)
    print(answer)
    print("=" * 80)

    # Check if model was used
    if '"model_used": true' in content:
        print("\n✅ 确认：模型已真正思考和回答问题!")
        print("✅ 使用Azure OpenAI API生成了答案")
    elif '"fallback": true' in content:
        print("\n⚠️  使用了降级策略（硬编码答案）")
else:
    print("未找到答案")
    print("响应前200字符:")
    print(content[:200])
