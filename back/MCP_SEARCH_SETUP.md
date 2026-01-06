# 中文必应搜索 MCP 服务器配置指南

## 当前状态

✅ **已配置 MCP 服务器地址**：`https://mcp.api-inference.modelscope.net/af62266fafca44/mcp`

✅ **代码已集成**：系统会尝试调用 MCP 搜索工具，失败时自动回退到模拟数据

⚠️ **当前使用模拟数据**：由于 anyio 版本兼容性问题，系统暂时使用模拟搜索结果

## 如何启用真实搜索

### 方法一：使用虚拟环境（推荐）

```bash
# 1. 创建虚拟环境
python3 -m venv venv_mcp
source venv_mcp/bin/activate

# 2. 安装依赖
pip install fastmcp>=2.14.0

# 3. 运行应用
python3 main.py
```

### 方法二：升级依赖（可能破坏兼容性）

```bash
pip install --upgrade anyio>=4.7.0
pip install --upgrade fastmcp>=2.14.0
```

⚠️ **注意**：升级 anyio 可能会破坏与 FastAPI 0.104.1 的兼容性

## MCP 服务器配置

您的 MCP 服务器已配置在 `config.py` 中：

```python
# 默认配置
mcp_server_url: str = "https://mcp.api-inference.modelscope.net/af62266fafca44/mcp"
```

## 验证搜索功能

运行测试以验证搜索是否正常工作：

```bash
# 测试搜索功能
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "query": [
      {
        "role": "user",
        "content": [
          {
            "type": "input_text",
            "text": "今天北京海淀区的天气怎么样"
          }
        ]
      }
    ]
  }'
```

## 搜索结果说明

- **真实搜索**：结果包含 `"source": "bing-cn-search-mcp"`
- **模拟搜索**：结果包含 `"source": "simulated_search"` 和 `"note": "这是模拟数据"`

## 查看服务器日志

搜索时查看控制台输出：
- `[MultiMCP] 使用搜索工具: xxx` - 使用真实 MCP 搜索
- `[INFO] 使用模拟搜索数据` - 使用模拟数据

## 故障排除

### 1. 连接失败
如果看到 "cannot specify both default and default_factory" 错误：
```bash
# 临时修复（系统级）
sed -i '171s/] = \[\]/]/' /usr/local/lib/python3.12/dist-packages/fastmcp/settings.py
```

### 2. 工具列表失败
如果看到 "function object is not subscriptable" 错误：
- 这是 anyio 版本兼容性问题
- 使用虚拟环境或等待 FastAPI 升级

### 3. 搜索超时
MCP 服务器响应时间可能较长，系统会自动处理超时

## 未来优化

1. **升级到 FastAPI 0.110+**：完全兼容 anyio 4.x
2. **添加搜索缓存**：避免重复查询
3. **添加搜索结果格式化**：更好的中文搜索结果展示
4. **支持多个搜索源**：可配置多个 MCP 搜索服务器
