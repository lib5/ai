#!/usr/bin/env python3
import json
import re

# Read the response file
with open('/tmp/chat_response.txt', 'r') as f:
    content = f.read()

# Extract the answer field
match = re.search(r'"answer":\s*"([^"]*(?:\\.[^"]*)*)"', content)
if match:
    answer = match.group(1)
    # Unescape the JSON string
    answer = answer.encode().decode('unicode_escape')
    print("模型回答:")
    print("=" * 80)
    print(answer)
    print("=" * 80)
else:
    print("未找到答案字段")
