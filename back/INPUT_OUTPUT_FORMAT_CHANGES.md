# 输入输出格式修改总结

## 修改概述

根据要求，修改了项目的输入输出格式，使其支持三种输入模式并采用流式步骤输出。

## 输入格式

支持三种输入模式：

### 1. 仅文本输入
```json
{
  "user_id": "user_123",
  "query": [
    {
      "role": "user",
      "content": [
        {"type": "input_text", "text": "你好，请介绍一下你自己"}
      ]
    }
  ]
}
```

### 2. 仅图像输入
```json
{
  "user_id": "user_456",
  "query": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_image",
          "image_url": "data:image/jpeg;base64,..."
        }
      ]
    }
  ]
}
```

### 3. 文本+图像输入
```json
{
  "user_id": "user_789",
  "query": [
    {
      "role": "user",
      "content": [
        {"type": "input_text", "text": "这是什么图像？"},
        {
          "type": "input_image",
          "image_url": "data:image/jpeg;base64,..."
        }
      ]
    }
  ]
}
```

## 输出格式

### 流式步骤输出

每次输出一个完整的 JSON 响应，包含一个步骤：

#### 工具调用步骤 (Start)
```json
{
  "code": 200,
  "message": "成功",
  "timestamp": "2025-12-18T09:17:44.594742Z",
  "requestId": "req_559b0ddb2b8c",
  "data": {
    "steps": [
      {
        "message_id": "uuid",
        "present_content": "模型思考：...",
        "tool_type": "Tool_finish",
        "parameters": "{}",
        "tool_status": "Start"
      }
    ]
  }
}
```

#### 工具调用步骤 (Success)
```json
{
  "code": 200,
  "message": "成功",
  "requestId": "req_559b0ddb2b8c",
  "data": {
    "steps": [
      {
        "message_id": "uuid",
        "present_content": "执行工具: finish",
        "tool_type": "Tool_finish",
        "parameters": "{}",
        "tool_status": "Success",
        "observation": "执行结果",
        "execution_duration": 50
      }
    ]
  }
}
```

#### 最终答案步骤 (Finish)
```json
{
  "code": 200,
  "message": "成功",
  "requestId": "req_559b0ddb2b8c",
  "data": {
    "steps": [
      {
        "message_id": "uuid",
        "present_content": "你好！我是一个基于人工智能的助手...",
        "tool_type": "Finish",
        "parameters": "{}",
        "tool_status": "Complete"
      }
    ]
  }
}
```

## 修改的文件

### 1. services/streaming_service.py
- 添加了 `datetime` 导入
- 新增 `generate_step_by_step_stream()` 方法
- 该方法逐个输出步骤，每次输出一个完整的响应格式

### 2. main.py
- 重写了 `handle_react_chat()` 函数
  - 支持三种输入模式检测（仅文本、仅图像、文本+图像）
  - 验证输入必须包含文本或图像
  - 将 ReAct 步骤转换为 Start/Success 格式
  - 使用新的流式输出方法
- 简化了 `chat_endpoint()` 函数
  - 移除了 steps 参数
  - 移除了重复的错误处理

## 测试结果

运行 `python3 test_new_format.py` 的结果：

✅ **测试 1: 仅文本输入** - 3 个步骤
- Start: Tool_finish
- Success: Tool_finish
- Complete: Finish

✅ **测试 2: 仅图像输入** - 5 个步骤
- Start: Tool_analyze_image
- Success: Tool_analyze_image
- Start: Tool_finish
- Success: Tool_finish
- Complete: Finish

✅ **测试 3: 文本+图像输入** - 5 个步骤
- Start: Tool_analyze_image
- Success: Tool_analyze_image
- Start: Tool_finish
- Success: Tool_finish
- Complete: Finish

## 使用方法

### 启动服务器
```bash
cd /home/libo/chatapi
python3 main.py
```

### 运行测试
```bash
cd /home/libo/chatapi
python3 test_new_format.py
```

## 关键改进

1. **输入灵活性**: 支持三种输入模式，适应不同场景
2. **流式输出**: 每次输出一个完整步骤，实时性好
3. **步骤清晰**: 工具调用分为 Start 和 Success 两个步骤，流程清晰
4. **错误处理**: 统一的错误处理机制
5. **代码简化**: 移除了不必要的重复代码

## 注意事项

- 服务器默认运行在 `http://localhost:8000`
- 健康检查端点: `GET /health`
- 聊天端点: `POST /api/chat`
- 流式输出使用换行符分隔的 JSON 格式
- 每个步骤都是一个完整的 HTTP 响应
