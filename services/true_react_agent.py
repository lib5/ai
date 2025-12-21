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
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from services.azure_openai_service import AzureOpenAIService
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
        self.timestamp = datetime.utcnow().isoformat() + "Z"

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
        self.azure_service = None
        self.tools = {}  # 工具注册表
        self.max_iterations = 10
        self.multi_mcp_client = None  # 多 MCP 客户端

    async def initialize(self):
        """初始化服务"""
        self.azure_service = AzureOpenAIService(
            endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version,
            deployment_name=settings.azure_deployment_name
        )
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
                        "server": tool_info.get('server', 'unknown')
                    }

        # 添加 finish 工具（特殊处理，不需要调用服务器）
        self.tools["finish"] = {
            "description": "完成任务并返回最终答案。当你已经有足够信息回答问题时使用。",
            "parameters": {
                "answer": "最终答案（必需）"
            },
            "server": "internal"  # 标记为内部工具
        }

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
        calendar_info = f"""## 当前时间信息
当前时间：{current_date_str}
今天是星期{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}

## 日期星期对照表

### {prev_year}年{prev_month}月（{month_names[prev_month]}月）
{chr(10).join([f"{prev_month}月{day:02d}日 = 星期{['一', '二', '三', '四', '五', '六', '日'][datetime(prev_year, prev_month, day).weekday()]}" for day in range(1, calendar.monthrange(prev_year, prev_month)[1] + 1)])}

### {current_year}年{current_month}月（{month_names[current_month]}月）
{chr(10).join([f"{current_month}月{day:02d}日 = 星期{['一', '二', '三', '四', '五', '六', '日'][datetime(current_year, current_month, day).weekday()]}" for day in range(1, calendar.monthrange(current_year, current_month)[1] + 1)])}

### {next_year}年{next_month}月（{month_names[next_month]}月）
{chr(10).join([f"{next_month}月{day:02d}日 = 星期{['一', '二', '三', '四', '五', '六', '日'][datetime(next_year, next_month, day).weekday()]}" for day in range(1, calendar.monthrange(next_year, next_month)[1] + 1)])}

## 使用说明
- 所有日期计算基于当前时间：{current_date_str}
- 查找某一天是星期几：直接查看上方对照表，如"12月22日 = 星期一"
- 计算"下周一"：今天星期{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]} + 1天 = 下星期一"""

        return calendar_info

    def _build_system_prompt(self, image_urls: List[str] = None, user_metadata: Optional[Dict[str, Any]] = None) -> str:
        """构建系统提示词"""
        tools_desc = "\n".join([
            f"- {name}: {info['description']}\n  参数: {json.dumps(info['parameters'], ensure_ascii=False)}"
            for name, info in self.tools.items()
        ])

        # 构建用户信息部分
        user_info = ""
        if user_metadata:
            user_fields = []
            # 遍历metadata中的所有字段，传递给模型
            for key, value in user_metadata.items():
                if value is not None:  # 如果值不为 None（即使为空字符串也保留）
                    # 字段中文映射表
                    label_map = {
                        'id': '用户ID',
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

{user_info}## 可用工具
{tools_desc}

## 输出格式
你必须严格按照以下JSON格式输出：

{{
    "thought": "你的思考过程：分析问题，决定下一步行动",
    "action": {{
        "tool": "工具名称",
        "args": {{工具参数}}
    }}
}}

## 重要规则
1. 每次只能选择一个工具
2. 当你认为已经可以回答问题时，使用 finish 工具并提供完整答案
3. 如果工具执行失败，思考其他方案
4. 不要重复使用相同的工具和参数
5. thought 字段必须包含你的真实推理过程
6. 你可以直接使用列出的 MCP 工具来完成任务，调用格式：
   {{
       "tool": "具体的工具名称",
       "args": {{
           "query": "搜索关键词"  // 根据工具要求填写参数
       }}
   }}
7.**必须使用真实工具**：
   - 当用户请求涉及操作（创建、查询、更新、删除）时，必须调用对应的MCP工具
   - 示例：
     * 用户说"创建联系人" → 调用 `contacts_create' 工具

"""

    def _build_conversation(
        self,
        query: str,
        steps: List[ReActStep],
        image_urls: List[str] = None,
        user_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """构建对话历史"""
        messages = [
            {"role": "system", "content": self._build_system_prompt(image_urls, user_metadata)}
        ]

        # 构建用户消息（可能包含图像）
        if image_urls:
            user_content = [{"type": "text", "text": f"用户问题：{query}"}]
            for url in image_urls:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": f"用户问题：{query}"})

        # 添加历史步骤
        for step in steps:
            if step.type == "thought":
                # 思考和行动是一起的，跳过单独的thought
                continue
            elif step.type == "action":
                # 模型的行动输出
                action_output = {
                    "thought": step.content.get("thought", ""),
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

        return messages

    async def _call_model(self, messages: List[Dict]) -> Dict[str, Any]:
        """调用模型并解析输出"""
        try:
            # 打印系统提示词
            if messages and len(messages) > 0:
                system_msg = messages[0].get("content", "")
                print(f"\n{'='*80}")
                print(f"[SYSTEM PROMPT]")
                print(f"{'='*80}")
                print(f"{system_msg}")
                print(f"{'='*80}\n")

            response = await self.azure_service.chat_completion(
                messages,
                max_tokens=1000,
                temperature=0.7
            )

            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"\n{'='*80}")
            print(f"[MODEL RAW OUTPUT]")
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

            # 尝试修复常见的JSON问题
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # 尝试提取JSON对象
                import re
                json_match = re.search(r'\{.*"thought".*"action".*\}', content, re.DOTALL)
                if json_match:
                    # 尝试解析匹配到的部分
                    try:
                        parsed = json.loads(json_match.group())
                    except:
                        # 如果仍然失败，尝试手动提取
                        parsed = self._extract_action_from_text(content)
                else:
                    parsed = self._extract_action_from_text(content)

            return {
                "success": True,
                "thought": parsed.get("thought", ""),
                "action": parsed.get("action", {})
            }
        except json.JSONDecodeError as e:
            print(f"[JSON解析失败]: {e}")
            print(f"[原始内容]: {content}")
            # 尝试从非JSON响应中提取信息
            return {
                "success": False,
                "thought": content,
                "action": {"tool": "finish", "args": {"answer": content}}
            }
        except Exception as e:
            print(f"[模型调用失败]: {e}")
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

    async def _execute_tool(self, tool_name: str, args: Dict) -> Dict[str, Any]:
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
            result = await self._tool_mcp_call_tool(tool_name, args)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============== 工具实现 ==============

    async def _tool_mcp_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具（使用多 MCP 客户端）

        Args:
            tool_name: MCP 工具名称
            arguments: 工具参数

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
            # 使用多 MCP 客户端调用工具
            result = await self.multi_mcp_client.call_tool(tool_name, arguments)

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

    async def run(self, query: str, image_urls: Optional[List[str]] = None, user_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        运行ReAct循环

        真正的ReAct流程：
        1. 模型思考并决定行动
        2. 执行工具获取观察结果
        3. 将观察结果反馈给模型
        4. 重复直到模型选择finish
        """
        await self.initialize()

        steps: List[ReActStep] = []
        image_urls = image_urls or []
        final_answer = ""

        # 构建系统提示词
        system_prompt = self._build_system_prompt(image_urls, user_metadata)

        print(f"\n{'='*60}")
        print(f"[ReAct] 开始处理: {query}")
        if image_urls:
            print(f"[ReAct] 图像数量: {len(image_urls)}")
        print(f"{'='*60}")

        # 打印系统提示词
        print(f"\n{'='*80}")
        print(f"[SYSTEM PROMPT]")
        print(f"{'='*80}")
        print(f"{system_prompt}")
        print(f"{'='*80}\n")

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n--- 迭代 {iteration} ---")

            # Step 1: 构建对话并调用模型
            messages = self._build_conversation(query, steps, image_urls, user_metadata)
            model_output = await self._call_model(messages)

            thought = model_output.get("thought", "")
            action = model_output.get("action", {})
            tool_name = action.get("tool", "finish")
            tool_args = action.get("args", {})

            print(f"[THOUGHT]: {thought[:200]}...")
            print(f"[ACTION]: {tool_name} -> {tool_args}")

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
                break

            # Step 3: 执行工具
            tool_result = await self._execute_tool(tool_name, tool_args)
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

        else:
            # 达到最大迭代次数
            final_answer = "抱歉，处理超时，无法完成任务。"

        print(f"\n{'='*60}")
        print(f"[ReAct] 完成，共 {iteration} 次迭代")
        print(f"[最终答案]: {final_answer}")
        print(f"{'='*60}\n")

        return {
            "query": query,
            "answer": final_answer,
            "steps": [s.to_dict() for s in steps],
            "iterations": iteration,
            "success": True
        }


# 全局实例
true_react_agent = TrueReActAgent()
