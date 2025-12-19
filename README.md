# 聊天接口 - Azure OpenAI GPT-4.1

这是一个使用 FastAPI 实现的聊天接口，支持文本和图像输入，通过 Azure OpenAI GPT-4.1 模型进行处理，并返回流式 JSON 响应。

## 功能特性

- ✅ 支持文本和图像混合输入
- ✅ Azure OpenAI GPT-4.1 模型集成
- ✅ 流式 JSON 输出
- ✅ 详细的处理步骤记录
- ✅ 异步处理
- ✅ MCP 客户端支持
- ✅ ModelScope MCP 服务测试

## 项目结构

```
chatapi/
├── main.py                    # FastAPI 主应用
├── config.py                  # 配置管理
├── requirements.txt           # Python 依赖
├── .env.example              # 环境变量示例
├── start.sh                  # 启动脚本
├── test_chat.py              # 测试脚本
├── mock_mcp_server.py         # MCP 模拟服务器
├── README.md                 # 说明文档
└── services/                  # 服务模块
    ├── azure_openai_service.py  # Azure OpenAI 服务
    ├── streaming_service.py     # 流式服务
    └── mcp_client.py            # MCP 客户端
```

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
MCP_SERVER_URL=http://localhost:3000
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 3. 启动服务

使用启动脚本：

```bash
chmod +x start.sh
./start.sh
```

或直接运行：

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动

### 4. 启动 MCP 模拟服务器（可选）

```bash
python mock_mcp_server.py --port 3000
```

## API 使用

### 聊天接口

**端点:** `POST /api/chat`

**请求体:**

```json
{
  "user_id": "user_123",
  "query": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "这是什么图像？"
        },
        {
          "type": "input_image",
          "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
        }
      ]
    }
  ]
}
```

**响应体:**

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
        "present_content": "开始处理用户 user_123 的请求",
        "tool_type": "System",
        "parameters": "{\"user_id\": \"user_123\"}",
        "tool_status": "Start"
      },
      {
        "message_id": "uuid_2",
        "present_content": "解析输入内容，包括文本和图像",
        "tool_type": "InputParser",
        "parameters": "{\"query_items\": 1}",
        "tool_status": "Success",
        "observation": "成功解析 1 个查询项",
        "execution_duration": 10
      }
    ]
  }
}
```

### 健康检查

**端点:** `GET /health`

**响应:**

```json
{
  "status": "healthy",
  "timestamp": "2025-12-16T10:30:00.000Z"
}
```

## 测试

运行测试脚本：

```bash
python test_chat.py
```

或指定服务器地址：

```bash
python test_chat.py http://your-server:8000
```

测试包括：

1. 纯文本输入测试
2. 文本和图像混合输入测试
3. 多个查询测试
4. 流式响应测试
5. 健康检查测试
6. MCP 客户端测试

## 流式响应

API 支持流式 JSON 输出，可以通过以下方式接收：

```python
import aiohttp
import asyncio

async def test_streaming():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/chat",
            json=request_data
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line:
                    print(line)

asyncio.run(test_streaming())
```

## MCP 客户端使用

```python
from services.mcp_client import ModelscopeMCPClient

async def use_mcp():
    async with ModelscopeMCPClient("http://localhost:3000") as client:
        # 搜索模型
        models = await client.search_model("computer vision")

        # 获取模型信息
        model_info = await client.get_model_info("AI-ModelScope/resnet50")

        # 测试流式处理
        result = await client.test_streaming({"test": "data"})

asyncio.run(use_mcp())
```

## 配置说明

### Azure OpenAI 配置

- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 资源的端点 URL
- `AZURE_OPENAI_API_KEY`: API 密钥
- `AZURE_OPENAI_API_VERSION`: API 版本（默认：2024-02-15-preview）
- `AZURE_OPENAI_DEPLOYMENT_NAME`: 部署名称（默认：gpt-4.1）

### 应用配置

- `APP_HOST`: 绑定主机（默认：0.0.0.0）
- `APP_PORT`: 监听端口（默认：8000）
- `MCP_SERVER_URL`: MCP 服务器地址（默认：http://localhost:3000）

## 技术细节

### 异步处理

所有 API 和内部函数都支持异步操作，使用 `async/await` 语法。

### 流式输出

使用 FastAPI 的 `StreamingResponse` 实现流式 JSON 输出。

### 图像处理

支持 base64 编码的图像输入，格式：`data:image/{format};base64,{base64_data}`

### 错误处理

API 返回标准化的错误响应格式：

```json
{
  "code": 500,
  "message": "处理请求时发生错误",
  "timestamp": "2025-12-16T10:30:00.000Z",
  "requestId": "req_xxx",
  "data": {
    "steps": [...]
  }
}
```

## 许可证

MIT License