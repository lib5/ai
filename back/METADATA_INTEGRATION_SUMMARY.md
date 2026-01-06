# Metadata 集成总结

## 概述

已成功将 metadata 信息集成到项目中，包括：
1. 新的输入参数格式
2. metadata 信息自动加入系统提示词
3. 完整的测试用例

## 修改的文件

### 1. `/home/libo/chatapi/main.py`

#### 新增的模型类：
```python
class UserMetadata(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    wechat: Optional[str] = None
    company: Optional[str] = None
    birthday: Optional[str] = None
    industry: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    address: Optional[str] = None
    country: Optional[str] = None
    location_updated_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

#### 修改的 ChatRequest 模型：
```python
class ChatRequest(BaseModel):
    user_id: str
    query: List[QueryItem]
    metadata: Optional[Dict[str, Any]] = None  # 新增字段
```

#### handle_react_chat 函数修改：
- 提取 metadata 中的 user 信息
- 将 user_metadata 传递给 true_react_agent.run()

### 2. `/home/libo/chatapi/services/true_react_agent.py`

#### 修改的方法：

**run() 方法签名：**
```python
async def run(
    self,
    query: str,
    image_urls: Optional[List[str]] = None,
    user_metadata: Optional[Dict[str, Any]] = None  # 新增参数
) -> Dict[str, Any]:
```

**_() 方法：build_system_prompt**
- 添加了 user_metadata 参数
- 在系统提示词中自动添加用户信息部分：

```python
## 用户信息
- 用户名: test_user
- 城市: 上海
- 行业: 互联网
- 公司: 新测试公司
- 国家: 中国
- 地址: 北京市朝阳区望京街道望京SOHO塔3号楼
- 邮箱: test@example.com
- 电话: 13900139000
```

**_build_conversation() 方法：**
- 添加了 user_metadata 参数
- 传递给 _build_system_prompt()

### 3. `/home/libo/chatapi/test_chat.py`

为所有测试方法添加了 metadata：
- `test_text_only()` - 北京用户
- `test_text_and_image()` - 上海用户
- `test_multiple_queries()` - 广州用户
- `test_streaming_response()` - 深圳用户
- `test_mcp_tools()` - 杭州用户

#### 新增测试方法：
```python
async def test_with_metadata(self, base64_image: str = None) -> Dict[str, Any]:
    """测试带metadata的完整请求格式"""
```

### 4. `/home/libo/chatapi/test_with_metadata.py` (新建)

独立的测试脚本，演示如何使用新的输入格式：
- 测试纯文本输入带metadata
- 测试文本+图像输入带metadata
- 完整的请求/响应示例

## 输入参数格式

### 新的输入格式：

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
          "image_url": "data:image/jpeg;base64,..."
        }
      ]
    }
  ],
  "metadata": {
    "user": {
      "id": "ac66c8b6-b138-4c67-8688-f165f46d730f",
      "username": "test_user_2e3b6b0f",
      "email": "test_29bd727c@example.com",
      "phone": "13900139000",
      "city": "上海",
      "wechat": "test_wechat",
      "company": "新测试公司",
      "birthday": "1990-01-01T00:00:00",
      "industry": "互联网",
      "longitude": 116.397128,
      "latitude": 39.916527,
      "address": "北京市朝阳区望京街道望京SOHO塔3号楼",
      "country": "中国",
      "location_updated_at": "2025-12-18T09:50:53.615000",
      "created_at": "2025-12-18T09:50:53.442000",
      "updated_at": "2025-12-18T09:50:53.615000"
    }
  }
}
```

## 系统提示词中的用户信息

当提供 metadata 时，系统提示词会自动包含用户信息，例如：

```
你是一个ReAct智能体。你需要通过"思考-行动-观察"循环来解决问题。

## 用户信息
- 用户名: test_user_2e3b6b0f
- 城市: 上海
- 行业: 互联网
- 公司: 新测试公司
- 国家: 中国
- 地址: 北京市朝阳区望京街道望京SOHO塔3号楼
- 邮箱: test_29bd727c@example.com
- 电话: 13900139000

## 可用工具
...
```

## 测试方法

### 运行所有测试：
```bash
python test_chat.py
```

### 运行新的metadata测试：
```bash
python test_with_metadata.py
```

### 指定服务器地址：
```bash
python test_with_metadata.py http://your-server:8000
```

## 兼容性

- ✅ 向后兼容：metadata 是可选字段，不提供时不会影响现有功能
- ✅ 所有现有测试都已更新，包含 metadata
- ✅ 新功能可以通过 test_with_metadata.py 独立测试

## 注意事项

1. metadata 是可选的，不提供时系统正常工作
2. 只有在 metadata.user 存在时才会添加到系统提示词
3. 用户信息可以帮助AI提供更个性化的回答
4. 敏感信息（如邮箱、电话）会包含在系统提示词中，请注意隐私保护

## 下一步计划

- 可以考虑在配置中设置是否包含敏感信息
- 可以根据用户信息定制不同的回答风格
- 可以添加用户偏好设置到 metadata 中
