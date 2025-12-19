# 输入输出格式示例

## 输入示例

### 仅文本输入
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "query": [
      {
        "role": "user",
        "content": [
          {"type": "input_text", "text": "你好，请介绍一下你自己"}
        ]
      }
    ]
  }'
```

### 仅图像输入
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_456",
    "query": [
      {
        "role": "user",
        "content": [
          {
            "type": "input_image",
            "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEBLAEsAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/wA=="
          }
        ]
      }
    ]
  }'
```

### 文本+图像输入
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_789",
    "query": [
      {
        "role": "user",
        "content": [
          {"type": "input_text", "text": "这是什么图像？"},
          {
            "type": "input_image",
            "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEBLAEsAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/wA=="
          }
        ]
      }
    ]
  }'
```

## 输出示例

### 流式响应（每次一个步骤）

#### 步骤 1: Start - 工具调用准备
```json
{"code":200,"message":"成功","timestamp":"2025-12-18T09:17:44.594742Z","requestId":"req_62ad79765b7b","data":{"steps":[{"message_id":"70f0891f-02e4-45d9-9c1a-b445f23d240d","present_content":"模型思考：用户希望了解我的身份和功能，这是一个简单的信息介绍问题，我可以直接回答。","tool_type":"Tool_finish","parameters":"{}","tool_status":"Start"}]}}
```

#### 步骤 2: Success - 工具执行结果
```json
{"code":200,"message":"成功","requestId":"req_62ad79765b7b","data":{"steps":[{"message_id":"64287a11-175a-43d2-b11a-37a5c5f1a612","present_content":"执行工具: finish","tool_type":"Tool_finish","parameters":"{}","tool_status":"Success","observation":"None","execution_duration":50}]}}
```

#### 步骤 3: Complete - 最终答案
```json
{"code":200,"message":"成功","requestId":"req_62ad79765b7b","data":{"steps":[{"message_id":"321ed7c3-9a36-450b-8f51-5d048c4ed77c","present_content":"你好！我是一个AI智能助手，能够理解和回答你的问题。我具备知识检索、信息分析、图片理解等多种功能，可以帮助你解决各类问题。","tool_type":"Finish","parameters":"{}","tool_status":"Complete"}]}}
```

## 字段说明

### 请求字段
- `user_id`: 用户ID（字符串）
- `query`: 查询内容数组
  - `role`: 角色（固定为"user"）
  - `content`: 内容数组
    - `type`: 内容类型（"input_text"或"input_image"）
    - `text`: 文本内容（当type="input_text"时）
    - `image_url`: 图像URL（当type="input_image"时）

### 响应字段
- `code`: HTTP状态码（200表示成功）
- `message`: 响应消息（"成功"表示成功）
- `timestamp`: 时间戳（ISO8601格式，仅第一个步骤包含）
- `requestId`: 请求ID（唯一标识符）
- `data`: 数据对象
  - `steps`: 步骤数组
    - `message_id`: 消息ID（UUID）
    - `present_content`: 显示内容（用户可见）
    - `tool_type`: 工具类型
      - "Tool_xxx": 工具调用（xxx为工具名）
      - "Finish": 最终答案
    - `parameters`: 工具参数（JSON字符串）
    - `tool_status`: 工具状态
      - "Start": 工具调用开始
      - "Success": 工具执行成功
      - "Complete": 最终完成
      - "Error": 执行错误
    - `observation`: 观察结果（工具执行后的结果，可选）
    - `execution_duration`: 执行时长（毫秒，可选）

## 工作流程

1. **输入验证**: 检查是否提供了文本或图像
2. **ReAct循环**: 运行推理和行动循环
3. **步骤生成**: 为每个工具调用生成Start和Success步骤
4. **流式输出**: 逐个输出步骤，每次一个完整的JSON响应
5. **最终答案**: 输出Finish步骤，包含最终答案

## 运行测试

```bash
cd /home/libo/chatapi
python3 test_new_format.py
```

测试包括：
- ✅ 仅文本输入测试
- ✅ 仅图像输入测试
- ✅ 文本+图像输入测试

每个测试都会显示完整的流式输出过程。
