# TrueReActAgent 技术文档

## 概述

`TrueReActAgent` 是一个完整的 ReAct（Reasoning and Acting）智能体实现，实现了 Thought → Action → Observation → Repeat 的推理循环模式。该智能体让模型能够自主思考、自主决策工具选择、自主决定循环终止，而非使用硬编码规则。

**核心特性：**
- ✅ 模型真正自主决策（不是预编程规则）
- ✅ 动态工具注册（从运行时获取）
- ✅ 多模态支持（文本 + 图像）
- ✅ 完整推理轨迹记录
- ✅ 容错和恢复机制

---

## 核心类：TrueReActAgent

### 主要职责

1. **管理 ReAct 推理循环**
2. **动态发现和注册工具**
3. **与 Azure OpenAI API 交互**
4. **调用 MCP 工具获取外部信息**
5. **追踪和记录完整推理过程**

### 关键属性

- `azure_service`: AzureOpenAIService - Azure OpenAI API 客户端
- `tools`: Dict - 工具注册表 {工具名: 工具信息}
- `max_iterations`: int - 最大迭代次数（默认10）
- `multi_mcp_client`: MultiMCPClient - 多 MCP 服务器客户端

---

## 主函数详解

### `run(query, image_urls=None, user_metadata=None) -> Dict[str, Any]`

**作用**：执行完整的 ReAct 推理循环

**这是整个智能体的核心入口方法**，实现了完整的思考-行动-观察循环。

#### 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | str | 用户查询文本 |
| `image_urls` | Optional[List[str]] | 可选的图像URL列表（base64编码） |
| `user_metadata` | Optional[Dict[str, Any]] | 可选的用户元数据（个性化信息） |

#### 返回值

```python
{
    "query": str,              # 原始用户查询
    "answer": str,             # 最终答案
    "steps": List[Dict],       # 所有推理步骤的字典列表
    "iterations": int,         # 实际迭代次数
    "success": bool            # 是否成功完成
}
```

#### 步骤分解

**第1步：初始化服务**
```python
await self.initialize()
```
- 初始化 Azure OpenAI 服务
- 初始化 MultiMCP 客户端
- 注册可用工具

**第2步：构建系统提示词**
```python
system_prompt = self._build_system_prompt(image_urls, user_metadata)
```
- 生成包含工具描述的提示词
- 集成用户个性化信息
- 定义输出格式要求

**第3步：ReAct 循环（最多10次）**

每次迭代包含：

1. **构建对话历史**
   ```python
   messages = self._build_conversation(query, steps, image_urls, user_metadata)
   ```

2. **调用模型**
   ```python
   model_output = await self._call_model(messages)
   ```

3. **解析输出**
   ```python
   thought = model_output.get("thought", "")
   action = model_output.get("action", {})
   tool_name = action.get("tool", "finish")
   ```

4. **记录行动**
   ```python
   action_step = ReActStep(...)
   steps.append(action_step)
   ```

5. **检查是否完成**
   ```python
   if tool_name == "finish":
       final_answer = tool_args.get("answer", "")
       break
   ```

6. **执行工具**
   ```python
   tool_result = await self._execute_tool(tool_name, tool_args)
   ```

7. **记录观察结果**
   ```python
   obs_step = ReActStep(...)
   steps.append(obs_step)
   ```

**第4步：返回结果**
```python
return {
    "query": query,
    "answer": final_answer,
    "steps": [s.to_dict() for s in steps],
    "iterations": iteration,
    "success": True
}
```

---

## 核心方法详解

### 初始化相关

#### `__init__()`
- **功能**：初始化智能体实例
- **输入**：无
- **输出**：无
- **作用**：设置默认属性，延迟初始化服务

#### `async initialize()`
- **功能**：初始化所有必要服务
- **输入**：无
- **输出**：无
- **作用**：
  1. 创建 AzureOpenAIService 实例
  2. 初始化 MultiMCPClient
  3. 注册可用工具

#### `async _init_multi_mcp_client()`
- **功能**：初始化多 MCP 客户端
- **输入**：无
- **输出**：无
- **作用**：
  1. 创建 MultiMCPClient 实例
  2. 列出所有可用工具
  3. 打印工具列表（便于调试）

### 工具管理

#### `_register_tools()`
- **功能**：注册可用工具（从 MultiMCPClient 动态获取）
- **输入**：无
- **输出**：无
- **作用**：
  1. 从 MultiMCPClient 获取工具列表
  2. 解析每个工具的参数模式（schema）
  3. 提取必填/可选参数信息
  4. 生成工具描述和参数说明
  5. 保存到 `self.tools` 字典
  6. 注册特殊工具 `finish`

**工具信息结构：**
```python
{
    "description": "工具描述",
    "parameters": {
        "参数名": "参数描述（是否必填）"
    },
    "server": "服务器名称"
}
```

### 提示词构建

#### `_build_system_prompt(image_urls=None, user_metadata=None) -> str`
- **功能**：构建系统提示词
- **输入**：
  - `image_urls`: 可选，图像URL列表
  - `user_metadata`: 可选，用户元数据
- **输出**：完整的系统提示词字符串
- **作用**：
  1. 生成工具描述列表
  2. 集成用户信息（用户名、城市、行业等）
  3. 定义输出格式（JSON：thought + action）
  4. 提供使用规则和示例

#### `_build_conversation(query, steps, image_urls=None, user_metadata=None) -> List[Dict]`
- **功能**：构建对话历史（供模型调用）
- **输入**：
  - `query`: 用户查询
  - `steps`: 历史推理步骤
  - `image_urls`: 可选，图像URL列表
  - `user_metadata`: 可选，用户元数据
- **输出**：符合 Azure OpenAI 格式的消息列表
- **作用**：
  1. 创建 system 消息（系统提示词）
  2. 构建用户消息（可能包含图像）
  3. 添加历史步骤（action + observation）
  4. 返回格式化的消息列表

### 模型交互

#### `async _call_model(messages) -> Dict[str, Any]`
- **功能**：调用 Azure OpenAI 模型并解析输出
- **输入**：`messages` - 对话消息列表
- **输出**：包含 `success`、`thought`、`action` 的字典
- **作用**：
  1. 发送消息给 Azure OpenAI
  2. 接收模型响应
  3. 打印系统提示词和原始输出（调试）
  4. 解析 JSON（处理 markdown 代码块）
  5. 容错处理（正则表达式提取）
  6. 返回解析结果

**错误处理策略：**
- JSON解析失败 → 尝试正则表达式提取
- 仍失败 → 使用文本提取方法
- 模型调用异常 → 返回错误并使用 finish 工具

#### `_extract_action_from_text(text) -> Dict[str, Any]`
- **功能**：从非标准JSON文本中提取 action 信息
- **输入**：`text` - 模型原始输出文本
- **输出**：包含 thought 和 action 的字典
- **作用**：使用正则表达式提取关键信息
  - 提取 `"thought"` 字段
  - 提取 `"tool"` 字段
  - 提取参数（`answer` 或 `query`）

### 工具执行

#### `async _execute_tool(tool_name, args) -> Dict[str, Any]`
- **功能**：执行指定工具
- **输入**：
  - `tool_name`: 工具名称
  - `args`: 工具参数
- **输出**：工具执行结果字典
- **作用**：
  1. 检查工具是否已注册
  2. 特殊处理 `finish` 工具（直接返回）
  3. 调用实际工具处理器
  4. 返回结果或错误信息

#### `async _tool_mcp_call_tool(tool_name, arguments) -> Dict[str, Any]`
- **功能**：通过 MultiMCPClient 调用 MCP 工具
- **输入**：
  - `tool_name`: MCP 工具名称
  - `arguments`: 工具参数
- **输出**：工具执行结果
- **作用**：
  1. 检查 MCP 客户端是否初始化
  2. 调用 MultiMCPClient.call_tool()
  3. 打印成功/失败信息
  4. 返回结果（包含来源服务器信息）

### 辅助类

#### ReActStep 类
- **作用**：表示 ReAct 推理过程中的一个步骤
- **属性**：
  - `iteration`: 迭代轮次
  - `type`: 步骤类型（"thought"、"action"、"observation"、"final_answer"）
  - `content`: 步骤内容
  - `tool_name`: 工具名称
  - `tool_args`: 工具参数
  - `tool_result`: 工具结果
  - `timestamp`: 时间戳
- **方法**：`to_dict()` - 转换为字典格式

---

## 完整使用示例

### 基本文本查询

```python
from services.true_react_agent import true_react_agent

# 文本查询
result = await true_react_agent.run("搜索关于Python编程的信息")
print(result["answer"])
```

### 多模态查询（文本 + 图像）

```python
result = await true_react_agent.run(
    query="这张图片里有什么？",
    image_urls=["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."]
)
```

### 带用户元数据

```python
result = await true_react_agent.run(
    query="推荐一些北京的餐厅",
    user_metadata={
        "username": "张三",
        "city": "北京",
        "industry": "IT",
        "company": "某科技公司"
    }
)
```

### 输出示例

```python
{
    "query": "搜索关于Python编程的信息",
    "answer": "Python是一种高级编程语言...",
    "steps": [
        {
            "iteration": 1,
            "type": "action",
            "content": {
                "thought": "用户询问Python编程信息，我需要搜索相关内容",
                "action": {
                    "tool": "bing_search",
                    "args": {"query": "Python编程"}
                }
            },
            "tool_name": "bing_search",
            "tool_args": {"query": "Python编程"},
            "timestamp": "2025-12-19T10:30:00.000Z"
        },
        {
            "iteration": 1,
            "type": "observation",
            "content": {
                "success": True,
                "result": {...},
                "server": "bing-mcp"
            },
            "tool_name": "bing_search",
            "tool_result": {...},
            "timestamp": "2025-12-19T10:30:01.000Z"
        }
    ],
    "iterations": 1,
    "success": True
}
```

---

## 内部工作流程

### ReAct 循环流程图

```
开始
  ↓
初始化服务
  ↓
构建系统提示词
  ↓
┌─────────────────┐
│  迭代循环 (1-10)  │
│                │
│  1. 构建对话    │
│  2. 调用模型    │
│  3. 解析输出    │
│  4. 记录行动    │
│                │
│  5. 是finish? ──→ 是 ──→ 结束
│       ↓ 否
│  6. 执行工具
│  7. 记录观察
│       ↓
└─────────────────┘
```

### 工具调用流程

```
模型输出工具调用
  ↓
_check: 工具是否注册？
  ↓ 是
_check: 是finish工具？
  ↓ 是 → 直接返回（逻辑操作）
  ↓ 否
_call: MultiMCPClient.call_tool()
  ↓
服务器返回结果
  ↓
返回 {success, result/error}
```

---

## 依赖关系

### 内部依赖
- **AzureOpenAIService** (`services.azure_openai_service`): Azure OpenAI API 客户端
- **MultiMCPClient** (`services.multi_mcp_client`): 多 MCP 服务器管理
- **Settings** (`config`): 配置管理

### 外部依赖
- **aiohttp**: 异步 HTTP 客户端
- **json**: JSON 解析
- **datetime**: 时间戳生成
- **typing**: 类型注解

---

## 关键设计原则

1. **真正自主性**
   - 模型完全自主决策工具选择
   - 模型决定是否继续循环
   - 不是基于硬编码规则

2. **动态工具发现**
   - 工具列表从运行时获取
   - 自动发现 MCP 服务器工具
   - 不需要硬编码工具列表

3. **完整追踪**
   - 每个步骤都有详细记录
   - 包含时间戳和完整上下文
   - 便于调试和审计

4. **容错性**
   - JSON解析失败时有多种回退策略
   - 工具调用失败时有错误恢复
   - 网络错误有友好提示

5. **调试友好**
   - 大量打印输出
   - 显示系统提示词
   - 显示模型原始输出
   - 显示每个步骤的详细信息

---

## 注意事项

### 使用前必须
1. ✅ 调用 `await initialize()`（在 `run()` 方法中自动调用）
2. ✅ 确保 Azure OpenAI 配置正确
3. ✅ 确保 MCP 服务器可访问

### 输入限制
- `query`: 字符串，不能为空
- `image_urls`: 必须是 base64 编码的 data URL 格式
- `max_iterations`: 默认10，防止无限循环

### 特殊工具
- **`finish`** 工具：表示任务完成，特殊处理，不需要实际执行
- **工具参数**：根据工具的 schema 动态解析，自动标识必填/可选

### 错误处理
- MCP 客户端未初始化 → 返回友好错误
- 工具调用失败 → 捕获异常并返回
- 模型输出格式错误 → 尝试多种解析策略

---

## 扩展指南

### 添加新工具

1. 在 MCP 服务器中注册工具
2. 确保 MultiMCPClient 能发现该工具
3. **无需修改 TrueReActAgent**（自动发现）

### 修改系统提示词

编辑 `_build_system_prompt()` 方法中的模板字符串：
```python
return f"""你是一个ReAct智能体。你需要通过"思考-行动-观察"循环来解决问题。

{user_info}## 可用工具
{tools_desc}

## 输出格式
{{
    "thought": "你的思考过程：分析问题，决定下一步行动",
    "action": {{
        "tool": "工具名称",
        "args": {{工具参数}}
    }}
}}

## 重要规则
...
"""
```

### 调整推理行为

- **修改最大迭代次数**：
  ```python
  self.max_iterations = 20  # 默认是10
  ```

- **调整模型参数**：
  ```python
  # 在 _call_model() 方法中
  response = await self.azure_service.chat_completion(
      messages,
      max_tokens=2000,  # 增加 max_tokens
      temperature=0.3   # 降低 temperature 使输出更稳定
  )
  ```

- **修改工具参数解析**：
  编辑 `_register_tools()` 方法中的参数解析逻辑

---

## 总结

`TrueReActAgent` 实现了一个完整的、真正自主的 ReAct 智能体，其核心是 `run()` 方法。

**主要流程：**
1. 初始化服务（Azure OpenAI + MCP 客户端）
2. 动态注册工具
3. 循环执行思考-行动-观察
4. 记录完整推理轨迹
5. 返回结果

**关键特点：**
- ✅ 自主决策（不是硬编码）
- ✅ 动态工具发现
- ✅ 多模态支持
- ✅ 完整追踪
- ✅ 容错恢复
- ✅ 调试友好

该实现强调了模型的真正自主性，让模型根据思考过程自由选择行动，更接近人类的推理方式。
