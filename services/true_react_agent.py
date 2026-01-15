"""
真正的 ReAct (Reasoning and Acting) Agent
实现 Thought -> Action -> Observation -> (repeat) 循环

核心改进：
1. 模型真正自主决策工具选择（不是硬编码规则）
2. 思考内容直接影响行动选择
3. 模型决定是否继续循环
"""

import json
import calendar
import aiohttp
import base64
import re
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta, timezone

from services.azure_openai_service import OpenAIService, AzureOpenAIService, DoubaoService
from services.multi_mcp_client import MultiMCPClient
from config import settings


class ReActStep:
    """ReAct推理步骤"""

    def __init__(
        self,
        iteration: int,
        step_type: str,  # thought, action, observation, final_answer
        content: Any,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict] = None,
        tool_result: Optional[Any] = None
    ):
        self.iteration = iteration
        self.type = step_type
        self.content = content
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.tool_result = tool_result
        self.timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "iteration": self.iteration,
            "type": self.type,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "timestamp": self.timestamp
        }
        # Only include tool_result if it's set (for action steps after tool execution)
        if self.tool_result is not None:
            result["tool_result"] = self.tool_result
        return result


class TrueReActAgent:
    """
    真正的 ReAct Agent

    核心原则：
    - 模型自主思考，自主决策
    - 工具选择由模型输出决定，不是硬编码规则
    - 循环终止由模型判断，不是固定规则
    """

    def __init__(self):
        self.openai_service = None
        self.tools = {}  # 工具注册表
        self.max_iterations = 20
        self.multi_mcp_client = None  # 多 MCP 客户端

    async def initialize(self):
        """初始化服务"""
        # 根据配置动态选择模型服务
        if settings.use_model.lower() == "gemini":
            print(f"🤖 初始化模型: Gemini-3-Flash-Preview")
            self.openai_service = OpenAIService(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model
            )
        elif settings.use_model.lower() == "gpt4.1":
            print(f"🤖 初始化模型: Azure GPT-4.1")
            self.openai_service = AzureOpenAIService(
                endpoint=settings.azure_endpoint,
                api_key=settings.azure_api_key,
                api_version=settings.azure_api_version,
                deployment_name=settings.azure_deployment_name
            )
        elif settings.use_model.lower() == "doubao":
            print(f"🤖 初始化模型: ByteDance Doubao ({settings.doubao_model})")
            self.openai_service = DoubaoService(
                api_key=settings.doubao_api_key,
                base_url=settings.doubao_base_url,
                model=settings.doubao_model,
                timeout=settings.doubao_timeout
            )
        else:
            raise ValueError(f"不支持的模型类型: {settings.use_model}")

        # 初始化多 MCP 客户端
        await self._init_multi_mcp_client()
        self._register_tools()

    async def _init_multi_mcp_client(self):
        """初始化多 MCP 客户端"""
        try:
            # 初始化多 MCP 客户端
            self.multi_mcp_client = MultiMCPClient()
            print(f"[MultiMCP] 多 MCP 客户端初始化成功")

            # 列出所有可用工具
            all_tools = await self.multi_mcp_client.list_all_tools()
            available_tools = self.multi_mcp_client.get_available_tools()

            print(f"[MultiMCP] 总共 {len(available_tools)} 个可用工具:")
            for tool_name in available_tools:
                server = self.multi_mcp_client.get_tool_server(tool_name)
                print(f"  - {tool_name} (来自 {server})")

        except Exception as e:
            print(f"[MultiMCP] 多 MCP 客户端初始化失败: {e}")
            self.multi_mcp_client = None

    def _register_tools(self):
        """注册可用工具 - 从 MultiMCPClient 获取具体工具信息"""
        self.tools = {}

        # 获取 MultiMCP 客户端中的所有工具
        if self.multi_mcp_client:
            available_tools = self.multi_mcp_client.get_available_tools()
            for tool_name in available_tools:
                # 从 MultiMCPClient 获取工具的完整信息
                tool_info = self.multi_mcp_client.get_tool_info(tool_name)
                if tool_info:
                    # 提取参数模式
                    schema = tool_info.get('schema')
                    params = {}
                    hidden_params = []  # 存储模型不可见的参数名

                    # 处理参数模式
                    if schema:
                        # 如果 schema 是对象，尝试转换为字典
                        if hasattr(schema, '__dict__') and not isinstance(schema, dict):
                            schema = vars(schema) if not isinstance(schema, dict) else schema

                        # 如果 schema 有 model_dump 方法（Pydantic 模型）
                        if hasattr(schema, 'model_dump'):
                            schema = schema.model_dump()

                        # 从 schema 中提取参数信息
                        if isinstance(schema, dict) and "properties" in schema:
                            properties = schema["properties"]
                            required = schema.get("required", [])
                            for param_name, param_info in properties.items():
                                if isinstance(param_info, dict):
                                    desc = param_info.get('description', '参数')
                                else:
                                    desc = getattr(param_info, 'description', '参数')

                                # 检查 description 是否包含"模型不可见"字样
                                is_hidden = "模型不可见" in str(desc)

                                if is_hidden:
                                    # 将隐藏参数加入列表，不在系统提示词中显示
                                    hidden_params.append(param_name)
                                    continue

                                param_desc = f"{desc}"
                                if param_name in required:
                                    param_desc += " (必需)"
                                else:
                                    param_desc += " (可选)"
                                params[param_name] = param_desc
                        else:
                            # 如果 schema 没有 'properties' 字段，使用通用参数
                            params = {
                                "arguments": "工具参数（JSON格式）"
                            }
                    else:
                        # 如果没有 schema，使用通用参数
                        params = {
                            "arguments": "工具参数（JSON格式）"
                        }

                    # 使用工具描述或默认描述
                    description = tool_info.get('description') or f"调用 {tool_name} 工具"

                    self.tools[tool_name] = {
                        "description": description,
                        "parameters": params,
                        "server": tool_info.get('server', 'unknown'),
                        "hidden_params": hidden_params  # 记录隐藏参数列表
                    }

        # 添加 finish 工具（特殊处理，不需要调用服务器）
        self.tools["finish"] = {
            "description": "完成任务并返回最终答案。当你已经有足够信息回答问题时使用。",
            "parameters": {
                "answer": "最终答案（必需）"
            },
            "server": "internal"  # 标记为内部工具
        }

    # ============== 聊天历史 HTTP 接口 ==============

    async def fetch_chat_history(self, user_id: str, page: int = 1, page_size: int = 10) -> List[Dict[str, Any]]:
        """
        从 HTTP 接口获取聊天历史

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量

        Returns:
            聊天消息列表
        """
        try:
            url = f"{settings.chat_api_base_url}/api/v1/chat/history_4_agent"
            request_data = {
                "user_id": user_id,
                "page": page,
                "page_size": page_size
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if isinstance(result, dict) and "data" in result:
                            messages = result.get("data", {}).get("messages", [])
                            print(f"[ChatHistory] 获取到 {len(messages)} 条历史消息")

                            # 打印获取到的数据详情
                            print(f"[ChatHistory] 原始响应数据:")
                            print(json.dumps(result, indent=2, ensure_ascii=False))

                            if messages:
                                print(f"\n[ChatHistory] 消息详情:")
                                for i, msg in enumerate(messages, 1):
                                    print(f"\n  消息 {i}:")
                                    print(f"    类型: {type(msg)}")
                                    if isinstance(msg, dict):
                                        print(f"    键: {list(msg.keys())}")

                                        # 打印所有字段的详细信息
                                        for key, value in msg.items():
                                            print(f"    {key}: {type(value)} = {value}")

                                            # 如果是content字段，显示详细内容
                                            if key == "content" and isinstance(value, list):
                                                print(f"      content 列表长度: {len(value)}")
                                                for j, item in enumerate(value):
                                                    print(f"        项 {j}: {type(item)} = {item}")

                                            # 如果是steps字段，显示详细信息
                                            elif key == "steps" and isinstance(value, (dict, list)):
                                                print(f"      steps 类型: {type(value)}")
                                                if isinstance(value, dict):
                                                    print(f"        steps 键: {list(value.keys())}")
                                                    for step_key, step_value in value.items():
                                                        print(f"          {step_key}: {step_value}")
                                                elif isinstance(value, list):
                                                    print(f"        steps 列表长度: {len(value)}")
                                                    for k, step_item in enumerate(value):
                                                        print(f"          项 {k}: {type(step_item)} = {step_item}")
                                    else:
                                        print(f"    值: {msg}")

                            return messages
                    else:
                        print(f"[ChatHistory] 获取失败，状态码: {response.status}")
                        return []
        except Exception as e:
            print(f"[ChatHistory] 获取历史消息异常: {str(e)}")
            return []

    async def create_chat_message(
        self,
        user_id: str,
        content: str,
        role: str = "assistant",
        steps: Dict = None,
        intent_type: str = "chat"
    ) -> Optional[str]:
        """
        通过 HTTP 接口创建聊天消息

        Args:
            user_id: 用户ID
            content: 消息内容
            role: 消息角色 (user/assistant)
            steps: 步骤信息
            intent_type: 意图类型

        Returns:
            创建的消息ID，失败返回 None
        """
        try:
            url = f"{settings.chat_api_base_url}/api/v1/chat/message"
            request_data = {
                "user_id": user_id,
                "message_type": "text",
                "role": role,
                "content": content,
                "intent_type": intent_type,
                "steps": steps or {}
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if isinstance(result, dict) and "data" in result:
                            message_id = result.get("data", {}).get("id")
                            print(f"[ChatHistory] 创建消息成功，ID: {message_id}")
                            return message_id
                    else:
                        print(f"[ChatHistory] 创建消息失败，状态码: {response.status}")
                        return None
        except Exception as e:
            print(f"[ChatHistory] 创建消息异常: {str(e)}")
            return None

    async def _save_chat_history(self, query: str, final_answer: str, steps: List[ReActStep], image_urls: List[str] = None):
        """
        保存聊天历史到数据库（已禁用）

        Args:
            query: 用户问题
            final_answer: 助手回答
            steps: 处理步骤
            image_urls: 图像URL列表
        """
        # 功能已禁用，不保存聊天历史
        pass

    def _format_chat_history(self, messages: List[Dict[str, Any]], max_messages: int = 5) -> str:
        """
        格式化聊天历史为提示词格式

        Args:
            messages: 聊天消息列表
            max_messages: 最大消息数量

        Returns:
            格式化后的历史字符串
        """
        if not messages:
            return ""

        # 取最近的消息（messages 已经按时间倒序）
        recent_messages = messages[:max_messages]
        # 反转顺序，让旧消息在前
        recent_messages = list(reversed(recent_messages))

        history_lines = []
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            if role == "user":
                # 用户消息
                content = msg.get("content", [])
                if isinstance(content, list):
                    text_items = [
                        item.get("text", "")
                        for item in content
                        if isinstance(item, dict) and item.get("type") == "input_text"
                    ]
                    text = " ".join(text_items)
                else:
                    text = str(content)
                history_lines.append(f"用户: {text[:200]}")
            elif role == "assistant":
                # 助手消息 - 从 steps 或 content 中提取答案
                answer = ""

                # 方式1: 从 steps 字典的 assistant_answer 字段提取（新的保存格式）
                steps = msg.get("steps", {})
                if isinstance(steps, dict) and "assistant_answer" in steps:
                    answer = steps.get("assistant_answer", "")
                    if answer:
                        history_lines.append(f"助手: {answer[:200]}")
                        continue

                # 方式2: 从 steps 字典中提取 final_answer（兼容旧格式）
                if isinstance(steps, dict) and "final_answer" in steps:
                    answer = steps.get("final_answer", "")
                    if answer:
                        history_lines.append(f"助手: {answer[:200]}")
                        continue

                # 方式3: 从 content 中提取答案
                content = msg.get("content", [])
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except:
                        answer = content[:200]
                        if answer:
                            history_lines.append(f"助手: {answer[:200]}")
                            continue
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "output_text":
                            answer = item.get("text", "")
                            if answer:
                                history_lines.append(f"助手: {answer[:200]}")
                            break

                # 方式4: 兼容旧格式 - steps 是列表
                if not answer and isinstance(steps, list):
                    for step in steps:
                        if isinstance(step, dict) and step.get("type") == "final_answer":
                            answer = step.get("content", "")
                            if answer:
                                history_lines.append(f"助手: {answer[:200]}")
                            break

                # 方式5: 尝试从 msg 顶层直接提取可能的答案字段
                if not answer:
                    for key in ['answer', 'text', 'response', 'message']:
                        if key in msg:
                            answer = str(msg.get(key, ""))
                            if answer:
                                history_lines.append(f"助手: {answer[:200]}")
                                break

        return ""

    def _get_calendar_info(self) -> str:
        """
        获取日历信息，包括当前时间、上个月、当前月、下个月的详细日历
        方便模型进行日期计算和星期推断
        """
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # 当前日期的详细信息（包含时分秒）
        current_date_str = now.strftime(f"%Y年%m月%d日 %H:%M:%S 星期{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}")

        # 计算上个月、当前月、下个月的年份和月份
        # 上个月
        if current_month == 1:
            prev_year = current_year - 1
            prev_month = 12
        else:
            prev_year = current_year
            prev_month = current_month - 1

        # 下个月
        if current_month == 12:
            next_year = current_year + 1
            next_month = 1
        else:
            next_year = current_year
            next_month = current_month + 1

        # 月份名称
        month_names = ['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']

        # 生成简化日历信息（只包含日期和星期）
        calendar_info = f"""## 今天当前时间信息
今天当前时间：{current_date_str}
今天是星期{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}

## 日期星期对照表

### {prev_year}年{prev_month}月（{month_names[prev_month]}月）
{chr(10).join([f"{prev_month}月{day:02d}日 = 星期{['一', '二', '三', '四', '五', '六', '日'][datetime(prev_year, prev_month, day).weekday()]}" for day in range(1, calendar.monthrange(prev_year, prev_month)[1] + 1)])}

### {current_year}年{current_month}月（{month_names[current_month]}月）
{chr(10).join([f"{current_month}月{day:02d}日 = 星期{['一', '二', '三', '四', '五', '六', '日'][datetime(current_year, current_month, day).weekday()]}" for day in range(1, calendar.monthrange(current_year, current_month)[1] + 1)])}

### {next_year}年{next_month}月（{month_names[next_month]}月）
{chr(10).join([f"{next_month}月{day:02d}日 = 星期{['一', '二', '三', '四', '五', '六', '日'][datetime(next_year, next_month, day).weekday()]}" for day in range(1, calendar.monthrange(next_year, next_month)[1] + 1)])}

## 请严格遵守我的时间计算定义
- 日期计算基于当前时间：{current_date_str}
- 查找某一天是星期几：直接查看上方对照表，如"12月22日 = 星期一"
- 下周’指的是从当前日期开始遇到的第一个周一开始到周日结束的完整周 下个月也是一样
"""

        return calendar_info

    def _build_system_prompt(self, image_urls: List[str] = None, user_metadata: Optional[Dict[str, Any]] = None) -> str:
        """构建系统提示词"""
        # 生成 OpenAI function calling 格式的工具列表
        tools_list = []
        for name, info in self.tools.items():
            # 转换参数格式
            if isinstance(info['parameters'], dict):
                # 处理参数字典
                properties = {}
                required = []
                for param_name, param_desc in info['parameters'].items():
                    # 检查是否为必需参数
                    is_required = "必需" in str(param_desc) or param_name in ['answer', 'query', 'file_path']
                    if is_required:
                        required.append(param_name)

                    # 根据描述推断类型
                    if "整数" in str(param_desc) or "number" in str(param_desc).lower():
                        param_type = "integer"
                    elif "布尔" in str(param_desc) or "bool" in str(param_desc).lower():
                        param_type = "boolean"
                    elif "列表" in str(param_desc) or "array" in str(param_desc).lower():
                        param_type = "array"
                    elif "对象" in str(param_desc) or "object" in str(param_desc).lower():
                        param_type = "object"
                    else:
                        param_type = "string"

                    properties[param_name] = {
                        "description": str(param_desc),
                        "type": param_type
                    }

                parameters = {
                    "type": "object",
                    "properties": properties
                }

                if required:
                    parameters["required"] = required
            else:
                # 通用参数格式
                parameters = {
                    "type": "object",
                    "properties": {
                        "arguments": {
                            "description": str(info['parameters']),
                            "type": "object"
                        }
                    }
                }

            tools_list.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": info['description'],
                    "parameters": parameters
                }
            })

        tools_desc = "可用工具列表:\n" + json.dumps(tools_list, ensure_ascii=False, indent=2)

        # 构建用户信息部分
        user_info = ""
        if user_metadata:
            user_fields = []
            # 遍历metadata中的所有字段，传递给模型
            for key, value in user_metadata.items():
                if value is not None:  # 如果值不为 None（即使为空字符串也保留）
                    # 过滤掉id字段，不传递给模型（仅用于服务端追踪）
                    if key == 'id':
                        continue

                    # 字段中文映射表
                    label_map = {
                        'username': '用户名',
                        'email': '邮箱',
                        'phone': '电话',
                        'city': '城市',
                        'wechat': '微信',
                        'company': '公司',
                        'birthday': '生日',
                        'industry': '行业',
                        'longitude': '经度',
                        'latitude': '纬度',
                        'address': '地址',
                        'country': '国家',
                        'location_updated_at': '位置更新时间',
                        'created_at': '创建时间',
                        'updated_at': '更新时间'
                    }
                    # 使用中文标签，如果key不在映射中则使用原key
                    label = label_map.get(key, key)
                    # 处理不同类型的值
                    display_value = value
                    if isinstance(value, str):
                        display_value = value if value else "(空)"
                    user_fields.append(f"{label}: {display_value}")

            if user_fields:
                user_info = f"## 用户信息\n" + "\n".join([f"- {field}" for field in user_fields]) + "\n\n"

        # 获取日历信息
        calendar_info = self._get_calendar_info()

        return f"""你是一个ReAct智能体。你需要通过"思考-行动-观察"循环来解决问题。

{calendar_info}

{user_info}

## 可用工具
{tools_desc}

## 输出格式
你必须严格按照以下JSON格式输出：

{{
    "show_content": "本步骤展示给用户看的文本，需要尽量精简 不要输出......",
    "action": {{
        "tool": "工具名称",
        "args": {{工具参数}}
    }}
}}

## 重要规则 严格遵守
1. 每次迭代只能选择一个工具
2. 当你认为已经可以回答问题时，使用 finish 工具并提供完整答案
3. 如果工具执行失败，考虑其他方案
4. 不要重复使用相同的工具和参数
5. 你是智能小秘书,名字叫做Moly。是一名冷静、专业的轻商务个人秘书，目标是高效把事情处理好，而不是陪聊或取悦用户。所有回复以结论和行动为先，少解释、不废话、不重复用户已知信息。信息不足时只提出一个最关键的问题，其余默认由 Moly 自主判断并推进。
6. 对于图片信息，你要提取全部文字内容做判断
7. 所以输出必须基于工具调用的结果 不能主观臆断
8. 你需要简要回答,节省用户阅读时间
9. 如果用户只输入图片 那么就必须需要你提取图像文字并根据文字意图，选择性执行工具
10. 创建日程时不要去调用查询日程工具

## 在调用工具前必须严格满足以下全部要求
1. schedules_create工具的参数"description":要求为
            "description": "日程详情 (可选) 要包含日程的大概内容 、日程的相关人员（没有就可以不加入）",
            "type": "string"

2.工具的参数(如果有)start_time 和 end_time 必须同时设置（要么都填，要么都不填）,不能同时设置 start_time/end_time 和 full_day
3. schedules_search 工具调用时 参数至少要包含一个以上的参数 如果有start_time参数必须设置end_time参数,并且end_time值默认是start_time的当天的最后时刻 ,不要使用工具描述中没有的参数
5. schedules_search使用时参数一定不能为空,优先使用query以外的参数，如果选择了除query以外的参数 就不要再使用query参数了
4. 工具调用的参数必须为前文中可用function他们各自自己的参数。
5. 用户有修改日程的意思 优先考虑schedules_update工具
6. notes参数不能有生日

严格要求
1. 优先考虑最末尾的对话消息
2. 只输出接下来一个步骤
"""
  
    def _build_conversation(
        self,
        query: str,
        steps: List[ReActStep],
        image_urls: List[str] = None,
        user_metadata: Optional[Dict[str, Any]] = None,
        chat_history: List[Dict[str, Any]] = None
    ) -> List[Dict]:
        """构建对话历史"""
        messages = [
            {"role": "system", "content": self._build_system_prompt(image_urls, user_metadata)},
            {"role": "user", "content": "以下是历史聊天记录"},
        ]

        # 添加历史聊天消息（从数据库获取的历史消息）
        if chat_history:
            # 取最近的消息，限制数量
            recent_messages = chat_history[:10]
            # 反转顺序，让旧消息在前
            recent_messages = list(reversed(recent_messages))

            for msg in recent_messages:
                role = msg.get("role", "unknown")
                if role == "user":
                    # 用户消息 - content是列表，需要转换格式
                    content = msg.get("content", [])
                    # 转换 content 格式：将 input_text 转换为 text，input_image 转换为 image_url
                    if isinstance(content, list):
                        converted_content = []
                        for item in content:
                            if isinstance(item, dict):
                                item_type = item.get("type")
                                if item_type == "input_text":
                                    converted_item = item.copy()
                                    converted_item["type"] = "text"
                                    converted_content.append(converted_item)
                                elif item_type == "input_image":
                                    converted_item = item.copy()
                                    converted_item["type"] = "image_url"
                                    converted_content.append(converted_item)
                                else:
                                    converted_content.append(item)
                            else:
                                converted_content.append(item)
                        content = converted_content
                    messages.append({"role": "user", "content": content})
                elif role == "assistant":
                    # 助手消息 - 从 steps 中提取答案
                    steps_data = msg.get("steps", {})
                    answer = ""

                    # 从 steps 列表中寻找 tool_type == "Finish" 的步骤
                    if isinstance(steps_data, list):
                        for step in steps_data:
                            if isinstance(step, dict) and step.get("tool_type") == "Finish":
                                answer = step.get("present_content", "")
                                if answer:
                                    messages.append({"role": "assistant", "content": answer})
                                break


        ## 避免把当前信息添加进去
        messages = messages[:-1]
        messages.append(
            {"role": "user", "content": "历史聊天记录结束"}
        )

        # 构建当前用户消息（可能包含图像）
        if image_urls:
            user_content = [{"type": "text", "text": f"当前用户问题：{query}"}]
            for url in image_urls:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": f"用户问题：{query}"})

        # 添加当前轮次的ReAct历史步骤
        for step in steps:
            if step.type == "thought":
                # 思考和行动是一起的，跳过单独的thought
                continue
            elif step.type == "action":
                # 模型的行动输出
                action_output = {
                    "thought": step.content.get("show_content", ""),
                    "action": {
                        "tool": step.tool_name,
                        "args": step.tool_args
                    }
                }
                messages.append({
                    "role": "assistant",
                    "content": json.dumps(action_output, ensure_ascii=False)
                })
            elif step.type == "observation":
                # 工具执行结果
                messages.append({
                    "role": "user",
                    "content": f"工具执行结果：{json.dumps(step.tool_result, ensure_ascii=False)}"
                })

        messages.append(
            {"role": "user", "content": "你的输出必须严格符合json格式"}
        )
        return messages

    async def _call_model(self, messages: List[Dict]) -> Dict[str, Any]:
        """调用模型并解析输出（最多重试3次）"""
        max_retries = 3
        retry_count = 0
        content = ""  # 初始化content变量

        while retry_count < max_retries:
            try:
                s_t = time.time()
                response = await self.openai_service.chat_completion(
                    messages,
                    max_tokens=3000,
                    temperature=0.1
                )

                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                e_t = time.time()
                print("response:",response)
                print("")

                print(f"模型耗时:{e_t-s_t}")
                print(f"\n{'='*80}")
                print(f"[MODEL OUTPUT]")
                print(f"{'='*80}")
                print(f"{content}")
                print(f"{'='*80}\n")

                # 尝试解析JSON
                # 处理可能的markdown代码块
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                content = content.strip()

                parsed = json.loads(content)

                return {
                    "success": True,
                    "thought": parsed.get("show_content", ""),
                    "action": parsed.get("action", {})
                }
            except json.JSONDecodeError as e:
                print(f"[JSON解析失败] 第 {retry_count + 1} 次尝试: {e}")
                print(f"[原始内容]: {content}")
                retry_count += 1
                if retry_count >= max_retries:
                    # 尝试从非JSON响应中提取信息
                    return {
                        "success": False,
                        "thought": content,
                        "action": {"tool": "finish", "args": {"answer": content}}
                    }
            except Exception as e:
                print(f"[模型调用失败] 第 {retry_count + 1} 次尝试: {e}")
                retry_count += 1
                if retry_count >= max_retries:
                    return {
                        "success": False,
                        "thought": f"模型调用出错: {str(e)}",
                        "action": {"tool": "finish", "args": {"answer": f"抱歉，处理过程中出现错误: {str(e)}"}}
                    }

    def _extract_action_from_text(self, text: str) -> Dict[str, Any]:
        """从非标准JSON文本中提取action信息"""
        import re

        # 尝试提取thought
        thought = ""
        thought_match = re.search(r'"thought"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
        if thought_match:
            thought = thought_match.group(1).replace('\\"', '"').replace('\\n', '\n')

        # 尝试提取tool
        tool = "finish"
        tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', text)
        if tool_match:
            tool = tool_match.group(1)

        # 尝试提取answer (如果是finish工具)
        args = {}
        if tool == "finish":
            answer_match = re.search(r'"answer"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
            if answer_match:
                args["answer"] = answer_match.group(1).replace('\\"', '"').replace('\\n', '\n')
            else:
                # 使用整个thought作为answer
                args["answer"] = thought if thought else text[:500]
        else:
            # 尝试提取query参数
            query_match = re.search(r'"query"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
            if query_match:
                args["query"] = query_match.group(1)

        return {
            "thought": thought,
            "action": {
                "tool": tool,
                "args": args
            }
        }

    async def _execute_tool(self, tool_name: str, args: Dict, user_id: Optional[str] = None) -> Dict[str, Any]:
        """执行工具"""
        if tool_name not in self.tools:
            return {"success": False, "error": f"未知工具: {tool_name}"}

        tool = self.tools[tool_name]
        server = tool.get("server")

        # finish 工具是内部工具，不需要调用服务器
        if server == "internal" or tool_name == "finish":
            return {"success": True, "result": args}

        # 调用 MCP 工具
        try:
            result = await self._tool_mcp_call_tool(tool_name, args, user_id)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============== 工具实现 ==============

    async def _tool_mcp_call_tool(self, tool_name: str, arguments: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        调用 MCP 工具（使用多 MCP 客户端）

        Args:
            tool_name: MCP 工具名称
            arguments: 工具参数
            user_id: 当前用户ID（避免实例变量污染）

        Returns:
            工具执行结果
        """
        if not self.multi_mcp_client:
            return {
                "success": False,
                "error": "多 MCP 客户端未初始化",
                "tool_name": tool_name,
                "arguments": arguments
            }

        try:
            # 获取工具信息，包括隐藏参数列表
            tool_info = self.tools.get(tool_name, {})
            hidden_params = tool_info.get('hidden_params', [])

            # 复制参数以避免修改原始参数
            final_arguments = arguments.copy()

            # 添加隐藏参数（从工具的 schema 中自动获取或从当前上下文获取）
            for param_name in hidden_params:
                if param_name not in final_arguments:
                    # 根据参数名设置默认值
                    if param_name == 'user_id':
                        # 从传入的 user_id 获取
                        if user_id:
                            final_arguments[param_name] = user_id
                    elif param_name == 'id':
                        # ID 参数通常需要生成或从其他来源获取，这里暂不自动设置
                        pass
                    else:
                        # 其他隐藏参数可以根据需要设置默认值
                        pass

            # 使用多 MCP 客户端调用工具
            result = await self.multi_mcp_client.call_tool(tool_name, final_arguments)

            if result.get('success'):
                print(f"[MultiMCP] 工具 '{tool_name}' 调用成功 (来自 {result.get('server', 'unknown')})")
            else:
                print(f"[MultiMCP ERROR] 工具 '{tool_name}' 调用失败: {result.get('error', 'unknown error')}")

            return result

        except Exception as e:
            error_msg = f"调用 MCP 工具 '{tool_name}' 失败: {str(e)}"
            print(f"[MultiMCP ERROR] {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "tool_name": tool_name,
                "arguments": arguments
            }

    # ============== 主循环 ==============

    async def run(self, query: str, image_urls: Optional[List[str]] = None, user_metadata: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        运行ReAct循环（流式版本）

        真正的ReAct流程：
        1. 模型思考并决定行动
        2. 执行工具获取观察结果
        3. 将观察结果反馈给模型
        4. 重复直到模型选择finish

        每完成一步就立即yield，不等待所有步骤完成
        """
        # ========== 时间统计开始 ==========
        request_start_time = time.time()
        chat_history_time = 0
        system_prompt_times = []
        model_call_times = []
        tool_execution_times = []
        current_iteration = 0
        # ========== 时间统计开始 ==========

        # 检查是否已初始化
        if self.openai_service is None:
            yield {
                "type": "error",
                "error": "ReAct Agent 未初始化，请先调用 initialize() 方法"
            }
            return

        # 设置当前用户ID（从 user_metadata 中提取）
        current_user_id = None
        if user_metadata and isinstance(user_metadata, dict):
            current_user_id = user_metadata.get('id')

        # ========== 聊天历史处理 ==========
        chat_history_start_time = time.time()
        # 获取聊天历史（需要在构建对话之前）
        # 设置较大的page_size以获取足够的历史消息
        chat_history = []
        if current_user_id:
            try:
                chat_history = await self.fetch_chat_history(current_user_id, page=1, page_size=20)
            except Exception as e:
                print(f"[ChatHistory] 获取历史失败: {str(e)}")
                chat_history = []
        chat_history_end_time = time.time()
        chat_history_time = (chat_history_end_time - chat_history_start_time) * 1000
        # ========== 聊天历史处理 ==========

        steps: List[ReActStep] = []
        image_urls = image_urls or []
        final_answer = ""

        print(f"\n{'='*60}")
        print(f"[ReAct] 开始处理: {query}")
        if image_urls:
            print(f"[ReAct] 图像数量: {len(image_urls)}")
        print(f"{'='*60}")

        # 打印系统提示词（确保完整输出到server.log）
        system_prompt = self._build_system_prompt(image_urls, user_metadata)
        print(f"\n{'='*80}")
        print(f"[SYSTEM PROMPT]")
        print(f"{'='*80}")
        print(f"{system_prompt}")
        print(f"{'='*80}\n")

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n--- 迭代 {iteration} ---", flush=True)
            current_iteration = iteration

            # Step 1: 构建对话并调用模型
            # 统计系统提示词构建时间（包含在构建对话过程中）
            system_prompt_start_time = time.time()
            messages = self._build_conversation(query, steps, image_urls, user_metadata, chat_history)
            system_prompt_end_time = time.time()
            system_prompt_times.append((system_prompt_end_time - system_prompt_start_time) * 1000)

            print("message信息：\n", flush=True)

            # 将完整message信息写入调试文件
            try:
                with open('/home/libo/chatapi/debug_messages.log', 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"迭代 {iteration} - message信息\n")
                    f.write(f"{'='*80}\n")
                    f.write(json.dumps(messages, ensure_ascii=False, indent=2))
                    f.write("\n\n")
            except Exception as e:
                print(f"写入message信息失败: {e}")

            # 打印message信息到server.log（结构完整，content可截断）
            try:
                # 深度复制messages以避免修改原始数据
                messages_to_print = json.loads(json.dumps(messages))

                # 对content字段进行截断处理（保留结构）
                for msg in messages_to_print:
                    if 'content' in msg and isinstance(msg['content'], list):
                        for content_item in msg['content']:
                            if isinstance(content_item, dict) and 'text' in content_item:
                                text = content_item['text']
                                if isinstance(text, str) and len(text) > 2000:
                                    content_item['text'] = text[:2000] + "...[内容已截断]"
                            elif isinstance(content_item, dict) and 'image_url' in content_item:
                                # 图像URL也进行截断
                                image_url = content_item['image_url']
                                if isinstance(image_url, dict) and 'url' in image_url:
                                    url = image_url['url']
                                    if isinstance(url, str) and len(url) > 100:
                                        image_url['url'] = url[:100] + "...[URL已截断]"

                # 打印处理后的messages（结构完整但内容可能截断）
                print(json.dumps(messages_to_print, ensure_ascii=False, indent=2))
                print(f"\n... [message的content内容可以截断但message的结构不能省略] ...\n")
            except Exception as e:
                print(f"打印message信息失败: {e}")

            # ========== 模型调用 ==========
            model_call_start_time = time.time()
            model_output = await self._call_model(messages)
            model_call_end_time = time.time()
            model_call_duration = (model_call_end_time - model_call_start_time) * 1000
            model_call_times.append(model_call_duration)
            # ========== 模型调用 ==========

            thought = model_output.get("thought", "")
            action = model_output.get("action", {})
            tool_name = action.get("tool", "finish")
            tool_args = action.get("args", {})

            print(f"[THOUGHT]: {thought[:200]}...", flush=True)
            print(f"[ACTION]: {tool_name} -> {tool_args}", flush=True)

            # 记录思考和行动步骤
            action_step = ReActStep(
                iteration=iteration,
                step_type="action",
                content={"thought": thought, "action": action},
                tool_name=tool_name,
                tool_args=tool_args
            )
            steps.append(action_step)

            # Step 2: 检查是否完成
            if tool_name == "finish":
                final_answer = tool_args.get("answer", "")
                print(f"[FINISH]: {final_answer[:200]}...")

                # 为finish工具创建观察步骤（虽然内部工具不需要执行，但需要记录）
                tool_result = {"success": True, "result": {"answer": final_answer}}
                action_step.tool_result = tool_result

                # 记录观察步骤
                obs_step = ReActStep(
                    iteration=iteration,
                    step_type="observation",
                    content=tool_result,
                    tool_name=tool_name,
                    tool_result=tool_result
                )
                steps.append(obs_step)

                # === 特殊处理：finish工具不输出start事件，直接输出final_answer ===
                # ========== 计算总时间并写入日志 ==========
                request_end_time = time.time()
                total_request_time = (request_end_time - request_start_time) * 1000
                total_model_time = sum(model_call_times)
                total_tool_time = sum(tool_execution_times)

                # 写入时间统计日志
                self._write_time_log({
                    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                    "user_id": current_user_id or "unknown",
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "iterations": iteration,
                    "chat_history_time_ms": round(chat_history_time, 2),
                    "system_prompt_times_ms": [round(t, 2) for t in system_prompt_times],
                    "model_call_times_ms": [round(t, 2) for t in model_call_times],
                    "total_model_time_ms": round(total_model_time, 2),
                    "tool_execution_times_ms": [round(t, 2) for t in tool_execution_times],
                    "total_tool_time_ms": round(total_tool_time, 2),
                    "total_request_time_ms": round(total_request_time, 2),
                    "success": True
                }, pretty_format=True)
                # ========== 计算总时间并写入日志 ==========

                yield {
                    "query": query,
                    "answer": final_answer,
                    "steps": [s.to_dict() for s in steps],
                    "iterations": iteration,
                    "success": True,
                    "type": "final_answer"
                }
                return

            # === 对于非finish工具，在step开始时立即yield start事件 ===
            yield {
                "iteration": iteration,
                "type": "start",
                "action": action_step.to_dict()
            }

            # Step 3: 执行工具
            # ========== 工具执行 ==========
            tool_execution_start_time = time.time()
            tool_result = await self._execute_tool(tool_name, tool_args, current_user_id)
            tool_execution_end_time = time.time()
            tool_execution_duration = (tool_execution_end_time - tool_execution_start_time) * 1000
            tool_execution_times.append(tool_execution_duration)
            # ========== 工具执行 ==========

            print(f"[OBSERVATION]: {json.dumps(tool_result, ensure_ascii=False)[:200]}...")

            # 将tool_result添加到action步骤中，这样main.py可以获取到
            action_step.tool_result = tool_result

            # 记录观察步骤
            obs_step = ReActStep(
                iteration=iteration,
                step_type="observation",
                content=tool_result,
                tool_name=tool_name,
                tool_result=tool_result
            )
            steps.append(obs_step)

            # === 工具执行结束时yield结果 ===
            yield {
                "iteration": iteration,
                "type": "result",
                "action": action_step.to_dict(),
                "observation": obs_step.to_dict()
            }

        else:
            # 达到最大迭代次数
            final_answer = "抱歉，处理超时，无法完成任务。"

            print(f"\n{'='*60}")
            print(f"[ReAct] 完成，共 {iteration} 次迭代")
            print(f"[最终答案]: {final_answer}")
            print(f"{'='*60}\n")

            # ========== 计算总时间并写入日志（超时情况）==========
            request_end_time = time.time()
            total_request_time = (request_end_time - request_start_time) * 1000
            total_model_time = sum(model_call_times)
            total_tool_time = sum(tool_execution_times)

            # 写入时间统计日志
            self._write_time_log({
                "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "user_id": current_user_id or "unknown",
                "query": query[:100] + "..." if len(query) > 100 else query,
                "iterations": iteration,
                "chat_history_time_ms": round(chat_history_time, 2),
                "system_prompt_times_ms": [round(t, 2) for t in system_prompt_times],
                "model_call_times_ms": [round(t, 2) for t in model_call_times],
                "total_model_time_ms": round(total_model_time, 2),
                "tool_execution_times_ms": [round(t, 2) for t in tool_execution_times],
                "total_tool_time_ms": round(total_tool_time, 2),
                "total_request_time_ms": round(total_request_time, 2),
                "success": False,
                "timeout": True
            })
            # ========== 计算总时间并写入日志（超时情况）==========

            # 流式输出：超时结果
            yield {
                "query": query,
                "answer": final_answer,
                "steps": [s.to_dict() for s in steps],
                "iterations": iteration,
                "success": False,
                "type": "final_answer"
            }
            return

    def _write_time_log(self, time_stats: Dict[str, Any], pretty_format: bool = False):
        """
        写入时间统计日志到文件

        Args:
            time_stats: 时间统计数据字典
            pretty_format: 是否使用美观格式（每个字段独占一行）
        """
        try:
            log_file_path = '/home/libo/chatapi/server_time.log'
            with open(log_file_path, 'a', encoding='utf-8') as f:
                if pretty_format:
                    # 美观格式：每个字段独占一行
                    f.write('{\n')
                    for i, (key, value) in enumerate(time_stats.items()):
                        if i == len(time_stats) - 1:
                            f.write(f'  "{key}": {json.dumps(value, ensure_ascii=False)}\n')
                        else:
                            f.write(f'  "{key}": {json.dumps(value, ensure_ascii=False)},\n')
                    f.write('}\n\n')
                else:
                    # 紧凑格式：一行显示
                    f.write(json.dumps(time_stats, ensure_ascii=False) + '\n\n')
        except Exception as e:
            print(f"写入时间统计日志失败: {e}")

#接下来集成http接口 实现创建messages和获取历史的功能

# 全局实例
true_react_agent = TrueReActAgent()



















