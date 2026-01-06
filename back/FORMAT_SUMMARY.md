# 格式验证总结

## ✅ 请求格式

支持以下三种格式：

### 1. 纯文本
```json
{
  "user_id": "string",
  "query": [
    {
      "role": "user",
      "content": [
        {"type": "input_text", "text": "你好 介绍下自己"}
      ]
    }
  ]
}
```

### 2. 文本和图像分离
```json
{
  "user_id": "xxxxx",
  "query": [
    {
      "role": "user",
      "content": [
        {"type": "input_text", "text": "what is in this image?"},
        {
          "type": "input_image",
          "image_url": "data:image/jpeg;base64,{base64_image}"
        }
      ]
    }
  ]
}
```

### 3. 文本和图像在同一个item中
```json
{
  "user_id": "string",
  "query": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "你好 介绍下自己",
          "image_url": "data:image/png;base64,{base64_image}"
        }
      ]
    }
  ]
}
```

## ✅ 响应格式

所有请求都返回相同的格式：

```json
{
  "code": 200,
  "message": "成功",
  "timestamp": "2025-12-16T10:30:00.000Z",
  "requestId": "req_5f8c9a2b3d1e",
  "data": {
    "steps": [
      {
        "message_id": "uuid_1",
        "present_content": "开始处理用户 xxx 的ReAct请求",
        "tool_type": "ReActAgent",
        "parameters": "{\"user_id\": \"xxx\"}",
        "tool_status": "Start",
        "observation": null,
        "execution_duration": null
      },
      {
        "message_id": "uuid_2",
        "present_content": "解析输入内容",
        "tool_type": "InputParser",
        "parameters": "{\"query_items\": 1}",
        "tool_status": "Success",
        "observation": "查询: xxx",
        "execution_duration": 5
      },
      {
        "message_id": "uuid_3",
        "present_content": "运行ReAct推理和行动循环",
        "tool_type": "ReActRunner",
        "parameters": "{\"query\": \"xxx\"}",
        "tool_status": "Success",
        "observation": "完成1次推理-行动循环",
        "execution_duration": 100
      },
      {
        "message_id": "uuid_4",
        "present_content": "推理步骤: thought",
        "tool_type": "ReActThought",
        "parameters": "{...}",
        "tool_status": "Complete",
        "observation": "用户询问: xxx。需要分析查询内容并确定合适的行动。",
        "execution_duration": 20
      },
      {
        "message_id": "uuid_5",
        "present_content": "推理步骤: action",
        "tool_type": "ReActThought",
        "parameters": "{...}",
        "tool_status": "Complete",
        "observation": "{'tool': 'web_search', 'arguments': {...}}",
        "execution_duration": 20
      },
      {
        "message_id": "uuid_6",
        "present_content": "推理步骤: observation",
        "tool_type": "ReActThought",
        "parameters": "{...}",
        "tool_status": "Complete",
        "observation": "{'tool': 'web_search', 'result': {...}}",
        "execution_duration": 20
      },
      {
        "message_id": "uuid_7",
        "present_content": "生成最终响应",
        "tool_type": "ResponseGenerator",
        "parameters": "{\"answer_length\": xxx}",
        "tool_status": "Success",
        "observation": "响应生成完成",
        "execution_duration": 10
      },
      {
        "message_id": "uuid_8",
        "present_content": "请求处理完成",
        "tool_type": "Finish",
        "parameters": "{}",
        "tool_status": "Complete",
        "observation": null,
        "execution_duration": null
      }
    ]
  }
}
```

## ✅ 验证结果

- ✅ 请求格式：支持纯文本、文本+图像分离、文本和图像组合
- ✅ 响应格式：只返回steps数组
- ✅ 无额外字段：没有react_mode、reasoning_trace、iterations
- ✅ 完整步骤：包含ReAct推理过程的详细步骤
- ✅ 必要字段：每个step包含message_id、present_content、tool_type、parameters、tool_status、observation、execution_duration

## 测试命令

```bash
# 测试纯文本
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","query":[{"role":"user","content":[{"type":"input_text","text":"hello"}]}]}'

# 测试文本+图像
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","query":[{"role":"user","content":[{"type":"input_text","text":"what?"},{"type":"input_image","image_url":"data:image/jpeg;base64,..."}]}]}'

# 运行测试脚本
python test_final_format.py
```
