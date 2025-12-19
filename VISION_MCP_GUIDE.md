# 视觉MCP服务器集成指南

## 概述

本项目已集成视觉MCP服务器（基于Qwen/Qwen3-VL-30B-A3B-Instruct模型），为图像输入提供完整的ReAct工作流程支持。

## 完整的ReAct工作流程

当用户提交图像分析请求时，系统会执行以下完整流程：

1. **思考（Think）** - 分析用户查询，确定是否需要工具
2. **行动（Action）** - 选择合适的工具（视觉MCP服务器或Azure OpenAI Vision）
3. **观察（Observation）** - 接收工具执行结果
4. **思考（Think Again）** - 基于观察结果，决定是否需要进一步行动
5. **可能再次行动（Possibly Act Again）** - 如果需要，循环执行工具调用
6. **最终答案（Final Answer）** - 生成综合答案

## 架构图

```
用户请求 (文本 + 图像)
        ↓
main.py 解析请求
        ↓
提取 image_url
        ↓
TrueReActAgent.run()
        ↓
迭代循环:
  ├─ Think (思考) → Azure OpenAI
  ├─ Action (行动) → 决定使用哪个工具
  ├─ Observation (观察) → 获取结果
  └─ 判断是否继续...
        ↓
生成最终答案
        ↓
返回流式响应
```

## 工具优先级

1. **MCP视觉服务器** (首选)
   - 优先尝试连接MCP服务器
   - 使用Qwen/Qwen3-VL-30B-A3B-Instruct模型
   - 高置信度结果 (0.9)

2. **Azure OpenAI Vision** (备用)
   - 如果MCP服务器不可用，自动回退
   - 使用Azure OpenAI的多模态能力
   - 高置信度结果 (0.9)

3. **模拟结果** (最终回退)
   - 如果所有工具都不可用
   - 低置信度结果 (0.3)

## 启动步骤

### 1. 启动视觉MCP服务器

```bash
# 使用npx启动视觉MCP服务器
npx -y vision-mcp-server

# 或者使用后台运行
npx -y vision-mcp-server &
```

环境变量配置（如果需要）：
```bash
export MODELSCOPE_MODEL="Qwen/Qwen3-VL-30B-A3B-Instruct"
export MODELSCOPE_TOKEN="your_token_here"
```

### 2. 启动Chat API服务器

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务器
python main.py
# 或者
./start.sh
```

### 3. 运行测试

```bash
# 运行完整的视觉ReAct测试
python test_react_vision_complete.py

# 运行简单图像测试
python test_react_image.py

# 运行所有聊天测试
python test_chat.py
```

## API示例

### 请求格式

```json
{
  "user_id": "user_123",
  "query": [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "请分析这张图像"
        },
        {
          "type": "input_image",
          "image_url": "data:image/png;base64,iVBORw0KGgo..."
        }
      ]
    }
  ]
}
```

### 响应格式

```json
{
  "code": 200,
  "message": "成功",
  "timestamp": "2025-12-18T10:30:00.000Z",
  "requestId": "req_xxx",
  "data": {
    "react_mode": true,
    "query": "请分析这张图像 [图像输入]",
    "answer": "这是最终的图像分析结果...",
    "reasoning_trace": [
      {
        "iteration": 1,
        "type": "thought",
        "content": "用户询问图像分析，需要使用视觉工具..."
      },
      {
        "iteration": 1,
        "type": "action",
        "content": "用户查询图像内容",
        "tool_name": "analyze_image",
        "tool_args": {
          "query": "请分析这张图像",
          "image_url": "data:image/png;base64,..."
        }
      },
      {
        "iteration": 1,
        "type": "observation",
        "content": {
          "success": true,
          "tool": "analyze_image",
          "result": {
            "analysis": "图像分析结果...",
            "confidence": 0.9,
            "mcp_tool_used": "vision_analyze",
            "timestamp": "2025-12-18T10:30:00.000Z"
          }
        },
        "tool_name": "analyze_image",
        "tool_result": {...}
      }
    ],
    "iterations": 1,
    "steps": [...]
  }
}
```

## 测试场景

### 场景1：简单图像分析

```python
import asyncio
import aiohttp

async def test_simple():
    data = {
        "user_id": "test",
        "query": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "描述这张图像"},
                {"type": "input_image", "image_url": "data:image/png;base64,..."}
            ]
        }]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8000/api/chat", json=data) as resp:
            result = await resp.json()
            print(result)
```

### 场景2：多轮对话 + 图像

```python
data = {
    "user_id": "test",
    "query": [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "这是第一张图像"},
                {"type": "input_image", "image_url": "data:image/png;base64,..."}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "这张图像的主要颜色是什么？"}
            ]
        }
    ]
}
```

## 调试信息

系统会输出详细的调试信息，包括：

```
=== ReAct Agent initialized with X tools ===
  - analyze_image: 分析图像内容
  - web_search: 搜索网络信息
  ...

=== MCP Server Tools (X total) ===
  - vision_analyze: 分析图像内容
  ...

[ReAct] 检测到 1 个图像输入
[图像分析] 从MCP服务器获取到 X 个工具
[图像分析] 使用工具: vision_analyze
```

## 故障排除

### 问题1：MCP服务器连接失败

**症状**: 日志显示 "警告: 无法连接MCP服务器"

**解决方案**:
1. 检查MCP服务器是否正在运行
2. 确认MCP_SERVER_URL配置正确（默认: http://localhost:3000）
3. 检查防火墙设置

### 问题2：图像分析失败

**症状**: 图像分析返回低置信度结果

**解决方案**:
1. 检查图像格式（支持data:image/*;base64,格式）
2. 确认图像大小不超过限制
3. 查看错误日志获取详细信息

### 问题3：推理轨迹不完整

**症状**: reasoning_trace为空或步骤不完整

**解决方案**:
1. 检查Azure OpenAI API密钥和配置
2. 确认API版本支持（需要支持vision的版本）
3. 查看网络连接

## 配置参数

在 `.env` 文件中配置：

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1

# MCP服务器
MCP_SERVER_URL=http://localhost:3000

# 应用
APP_HOST=0.0.0.0
APP_PORT=8000
```

## 性能优化建议

1. **MCP服务器缓存**: 启用MCP服务器工具缓存以减少初始化时间
2. **并发请求**: 使用异步处理提高并发性能
3. **图像压缩**: 对于大图像，考虑预处理和压缩
4. **超时设置**: 为不同工具设置合理的超时时间

## 扩展功能

### 添加新的视觉工具

1. 在MCP服务器中注册新工具
2. 更新 `_register_builtin_tools()` 方法
3. 添加相应的处理函数

### 自定义推理逻辑

修改 `think()` 方法中的prompt模板，调整思考过程的行为。

### 添加新的回退策略

在 `_analyze_image()` 方法中添加新的回退逻辑。

## 参考资料

- [Qwen3-VL模型文档](https://huggingface.co/Qwen/Qwen3-VL-30B-A3B-Instruct)
- [ModelScope文档](https://modelscope.cn/)
- [Azure OpenAI Vision API](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/vision)
- [MCP协议规范](https://modelcontextprotocol.io/)
