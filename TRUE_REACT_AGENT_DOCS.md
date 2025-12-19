"""
TrueReAct Agent 完整代码注释版
===============================

这个文件实现了真正的 ReAct (Reasoning and Acting) Agent
实现 Thought -> Action -> Observation -> (repeat) 循环

核心改进：
1. 模型真正自主决策工具选择（不是硬编码规则）
2. 思考内容直接影响行动选择
3. 模型决定是否继续循环
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入 Azure OpenAI 服务
from services.azure_openai_service import AzureOpenAIService
# 导入 MCP 客户端
from services.mcp_client import ModelscopeMCPClient, FastMCPClient
# 导入多 MCP 客户端
from services.multi_mcp_client import MultiMCPClient
# 导入配置
from config import settings


class ReActStep:
    """ReAct推理步骤

    这个类表示 ReAct 推理过程中的一个单独步骤。
    ReAct 循环包含三种主要步骤：thought（思考）、action（行动）、observation（观察）

    属性:
        iteration: 迭代轮次，表示这是第几轮推理循环
        step_type: 步骤类型，可以是 'thought', 'action', 'observation', 'final_answer'
        content: 步骤的内容，格式根据类型而定
        tool_name: 工具名称（仅在 action 和 observation 类型中使用）
        tool_args: 工具参数（仅在 action 类型中使用）
        tool_result: 工具执行结果（仅在 observation 类型中使用）
        timestamp: 时间戳，记录步骤创建时间
    """

    def __init__(
        self,
        iteration: int,
        step_type: str,  # thought, action, observation, final_answer
        content: Any,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict] = None,
        tool_result: Optional[Any] = None
    ):
        """初始化 ReAct 步骤

        Args:
            iteration: 迭代轮次编号，从 1 开始
            step_type: 步骤类型
                - 'thought': 模型思考过程
                - 'action': 模型采取的行动（调用工具）
                - 'observation': 工具执行后的观察结果
                - 'final_answer': 最终答案
            content: 步骤内容，格式随类型变化
            tool_name: 工具名称（action/observation 类型使用）
            tool_args: 工具参数（action 类型使用）
            tool_result: 工具执行结果（observation 类型使用）
        """
        self.iteration = iteration
        self.type = step_type
        self.content = content
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.tool_result = tool_result
        self.timestamp = datetime.utcnow().isoformat() + "Z"  # UTC 时间戳，格式化为 ISO 8601

    def to_dict(self) -> Dict[str, Any]:
        """将步骤转换为字典格式

        用于序列化和返回给调用者。

        Returns:
            包含步骤所有信息的字典
        """
        result = {
            "iteration": self.iteration,
            "type": self.type,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "timestamp": self.timestamp
        }
        # Only include tool_result if it's set (for action steps after tool execution)
        # 只有在设置了 tool_result 时才包含（action 步骤执行工具后）
        if self.tool_result is not None:
            result["tool_result"] = self.tool_result
        return result


class TrueReActAgent:
    """
    真正的 ReAct Agent

    这个类是整个 ReAct 系统的核心。它实现了完整的 ReAct（推理与行动）循环，
    让模型能够自主思考、自主决策、自主选择和使用工具。

    核心原则：
    - 模型自主思考，自主决策
    - 工具选择由模型输出决定，不是硬编码规则
    - 循环终止由模型判断，不是固定规则

    主要工作流程：
    1. 初始化 Azure OpenAI 服务和 MCP 客户端
    2. 注册可用工具（从 MultiMCPClient 获取）
    3. 循环执行 ReAct 步骤：
       a) 构建对话历史（系统提示 + 用户问题 + 历史步骤）
       b) 调用模型获得思考和行动
       c) 如果选择 finish 工具，则结束循环
       d) 否则执行工具获得观察结果
       e) 将观察结果加入历史，重复循环
    4. 返回完整的推理轨迹和最终答案

    属性:
        azure_service: Azure OpenAI 服务实例，用于调用 GPT 模型
        tools: 工具注册表，存储所有可用工具及其处理器
        max_iterations: 最大迭代次数，防止无限循环
        multi_mcp_client: 多 MCP 客户端，用于调用外部工具
    """

    def __init__(self):
        """初始化 TrueReAct Agent

        设置初始状态，但不初始化服务（延迟到 run() 方法中）
        这样可以避免在导入时就连接外部服务。
        """
        self.azure_service = None
        self.tools = {}  # 工具注册表，格式: {tool_name: {description, parameters, handler}}
        self.max_iterations = 10  # 最大迭代次数，建议 3-10 之间
        self.multi_mcp_client = None  # 多 MCP 客户端，延迟初始化

    async def initialize(self):
        """初始化服务

        这是延迟初始化的实现。只有在真正需要时才初始化服务，
        避免在类创建时就连接外部依赖。

        执行步骤：
        1. 创建 Azure OpenAI 服务实例
        2. 初始化 MultiMCPClient（用于调用外部工具）
        3. 注册所有可用工具到工具表
        """
        # 初始化 Azure OpenAI 服务
        # 使用配置中的参数创建服务实例
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
        """初始化多 MCP 客户端

        MultiMCPClient 是一个特殊的客户端，可以同时管理多个 MCP 服务器，
        并提供统一的工具调用接口。这让我们可以：
        1. 连接到多个 MCP 服务器
        2. 自动发现所有可用工具
        3. 统一调用不同来源的工具

        错误处理：
        如果初始化失败（网络错误、配置错误等），
        会捕获异常并将 multi_mcp_client 设置为 None，
        这样后续的工具调用会返回友好的错误信息。
        """
        try:
            # 初始化多 MCP 客户端
            self.multi_mcp_client = MultiMCPClient()
            print(f"[MultiMCP] 多 MCP 客户端初始化成功")

            # 列出所有可用工具
            all_tools = await self.multi_mcp_client.list_all_tools()
            available_tools = self.multi_mcp_client.get_available_tools()

            print(f"[MultiMCP] 总共 {len(available_tools)} 个可用工具:")
            for tool_name in available_tools:
                # 获取工具来源服务器名称
                server = self.multi_mcp_client.get_tool_server(tool_name)
                print(f"  - {tool_name} (来自 {server})")

        except Exception as e:
            print(f"[MultiMCP] 多 MCP 客户端初始化失败: {e}")
            self.multi_mcp_client = None  # 失败时设置为 None

    def _register_tools(self):
        """注册可用工具 - 从 MultiMCPClient 获取具体工具

        这个方法从 MultiMCPClient 中获取所有可用工具，并将它们注册到 self.tools 中。
        工具注册表是 ReAct Agent 工作的基础，它告诉模型有哪些工具可以使用。

        注册过程：
        1. 从 MultiMCPClient 获取所有可用工具列表
        2. 为每个工具设置参数描述（根据工具名称智能判断）
        3. 创建工具处理器（调用 MultiMCPClient 的 call_tool 方法）
        4. 将工具信息存储到 self.tools 字典

        工具参数描述的智能设置：
        - bing_search: 搜索查询，使用 query 和 count 参数
        - fetch_webpage: 获取网页，使用 result_id 参数
        - 其他工具: 使用通用的 query 和 arguments 参数

        特殊工具 'finish'：
        这是一个内置的特殊工具，表示任务完成。
        它不需要处理器，因为它是逻辑操作（终止循环）而不是外部调用。
        """
        self.tools = {}

        # 获取 MultiMCP 客户端中的所有工具
        if self.multi_mcp_client:
            available_tools = self.multi_mcp_client.get_available_tools()
            for tool_name in available_tools:
                # 根据工具名称设置不同的参数描述
                # 这样可以帮助模型更好地理解每个工具的用途
                if "bing_search" in tool_name.lower():
                    params = {
                        "query": "搜索查询关键词",
                        "count": "返回结果数量（可选，默认5）"
                    }
                elif "fetch_webpage" in tool_name.lower():
                    params = {
                        "result_id": "从搜索结果中获取的 result_id"
                    }
                else:
                    # 其他工具使用通用参数
                    params = {
                        "query": "查询参数",
                        "arguments": "附加参数（可选）"
                    }

                # 注册工具信息
                self.tools[tool_name] = {
                    "description": f"调用 {tool_name} 工具",
                    "parameters": params,
                    "handler": self._create_tool_handler(tool_name)  # 创建处理器
                }

        # 添加 finish 工具
        # finish 是一个特殊的内置工具，用于表示任务完成
        # 当模型认为已经有足够信息回答问题时，会调用此工具
        self.tools["finish"] = {
            "description": "完成任务并返回最终答案。当你已经有足够信息回答问题时使用。",
            "parameters": {
                "answer": "最终答案"
            },
            "handler": None  # 特殊工具，不需要handler，因为它是逻辑操作
        }

    def _create_tool_handler(self, tool_name: str):
        """为指定工具创建处理器

        这是一个工厂函数，为每个 MCP 工具创建一个异步处理器。
        处理器的作用是将工具调用请求转发给 MultiMCPClient。

        Args:
            tool_name: 工具名称

        Returns:
            一个异步函数，可以调用指定工具

        示例:
            handler = _create_tool_handler("bing_search")
            result = await handler(query="Python教程")
        """
        async def handler(**args):
            # 将调用转发给 _tool_mcp_call_tool 方法
            return await self._tool_mcp_call_tool(tool_name, args)
        return handler

    def _build_system_prompt(self, image_urls: List[str] = None) -> str:
        """构建系统提示词

        系统提示词是发送给模型的第一条消息，它定义了：
        1. 智能体的角色和行为方式
        2. 所有可用工具的详细描述
        3. 输出格式要求
        4. 重要的规则和注意事项

        提示词的组成：
        - 角色定义：你是一个ReAct智能体...
        - 工具列表：每个工具的名称、描述和参数格式化为 JSON
        - 输出格式：必须严格按照 JSON 格式输出
        - 规则：每次只能选择一个工具、何时使用 finish 工具等

        Args:
            image_urls: 图像 URL 列表（可选）

        Returns:
            完整的系统提示词字符串

        提示词格式示例:
        你是一个ReAct智能体。你需要通过"思考-行动-观察"循环来解决问题。

        ## 可用工具
        - bing_search: 调用 bing_search 工具
          参数: {"query": "搜索查询关键词", "count": "返回结果数量（可选，默认5）"}
        - finish: 完成任务并返回最终答案...

        ## 输出格式
        你必须严格按照以下JSON格式输出：
        {
            "thought": "你的思考过程",
            "action": {
                "tool": "工具名称",
                "args": {工具参数}
            }
        }
        """
        tools_desc = "\n".join([
            f"- {name}: {info['description']}\n  参数: {json.dumps(info['parameters'], ensure_ascii=False)}"
            for name, info in self.tools.items()
        ])

        return f"""你是一个ReAct智能体。你需要通过"思考-行动-观察"循环来解决问题。

## 可用工具
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

"""

    def _build_conversation(
        self,
        query: str,
        steps: List[ReActStep],
        image_urls: List[str] = None
    ) -> List[Dict]:
        """构建对话历史

        为了让模型理解当前的任务和之前的进展，
        需要构建一个对话历史，包含：
        1. 系统提示词（定义角色和工具）
        2. 用户问题（可能包含图像）
        3. 历史步骤（之前的思考、行动、观察）

        对话历史的格式符合 Azure OpenAI 的消息格式：
        - role: "system" - 系统提示
        - role: "user" - 用户输入
        - role: "assistant" - 模型输出

        Args:
            query: 用户查询文本
            steps: 之前的 ReAct 步骤列表
            image_urls: 图像 URL 列表（可选）

        Returns:
            符合 OpenAI 格式的消息列表

        示例输出:
        [
            {"role": "system", "content": "你是一个ReAct智能体..."},
            {"role": "user", "content": "用户问题：搜索Python教程"},
            {"role": "assistant", "content": "{\"thought\": \"用户询问...\", \"action\": {...}}"},
            {"role": "user", "content": "工具执行结果：{...}"}
        ]
        """
        messages = [
            {"role": "system", "content": self._build_system_prompt(image_urls)}
        ]

        # 构建用户消息（可能包含图像）
        if image_urls:
            # 包含图像的多模态消息
            user_content = [{"type": "text", "text": f"用户问题：{query}"}]
            for url in image_urls:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            messages.append({"role": "user", "content": user_content})
        else:
            # 纯文本消息
            messages.append({"role": "user", "content": f"用户问题：{query}"})

        # 添加历史步骤
        for step in steps:
            if step.type == "thought":
                # 思考和行动是一起的，跳过单独的thought
                # 因为模型输出的是 action，包含 thought 字段
                continue
            elif step.type == "action":
                # 模型的行动输出，包含 thought 和 action
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
                # 工具执行结果，需要反馈给模型
                messages.append({
                    "role": "user",
                    "content": f"工具执行结果：{json.dumps(step.tool_result, ensure_ascii=False)}"
                })

        return messages

    async def _call_model(self, messages: List[Dict]) -> Dict[str, Any]:
        """调用模型并解析输出

        这是与 Azure OpenAI 交互的核心方法。
        它负责：
        1. 发送消息给模型
        2. 接收模型响应
        3. 解析 JSON 输出
        4. 处理各种错误情况

        错误处理策略：
        - JSON 解析失败：尝试正则表达式提取
        - 模型调用异常：返回错误信息并使用 finish 工具
        - 部分解析成功：返回部分结果

        Args:
            messages: 符合 OpenAI 格式的消息列表

        Returns:
            包含以下字段的字典：
            - success: 是否成功
            - thought: 模型思考内容
            - action: 模型选择的行动

        示例返回:
        {
            "success": True,
            "thought": "用户询问Python编程，我需要搜索相关信息",
            "action": {"tool": "bing_search", "args": {"query": "Python编程"}}
        }
        """
        try:
            # 打印系统提示词（调试用）
            if messages and len(messages) > 0:
                system_msg = messages[0].get("content", "")
                print(f"\n{'='*80}")
                print(f"[SYSTEM PROMPT]")
                print(f"{'='*80}")
                print(f"{system_msg}")
                print(f"{'='*80}\n")

            # 调用 Azure OpenAI 服务
            response = await self.azure_service.chat_completion(
                messages,
                max_tokens=1000,  # 最大返回 token 数
                temperature=0.7   # 创造性参数，0.7 是平衡值
            )

            # 提取模型响应的内容
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"\n{'='*80}")
            print(f"[MODEL RAW OUTPUT]")
            print(f"{'='*80}")
            print(f"{content}")
            print(f"{'='*80}\n")

            # 尝试解析JSON
            # 处理可能的markdown代码块
            # 模型可能用 ```json 或 ``` 包裹 JSON
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
                # 使用正则表达式搜索包含 "thought" 和 "action" 的 JSON 对象
                json_match = re.search(r'\{.*"thought".*"action".*\}', content, re.DOTALL)
                if json_match:
                    # 尝试解析匹配到的部分
                    try:
                        parsed = json.loads(json_match.group())
                    except:
                        # 如果仍然失败，使用文本提取方法
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
        """从非标准JSON文本中提取action信息

        当模型输出不是标准 JSON 格式时，这个方法尝试从文本中提取关键信息。
        它使用正则表达式搜索特定模式：
        1. "thought" 字段的内容
        2. "tool" 字段的值
        3. 参数内容（query 或 answer）

        这种容错处理提高了系统的鲁棒性，即使模型输出格式不完全正确也能处理。

        Args:
            text: 模型返回的原始文本

        Returns:
            包含提取信息的字典，格式为标准 action 输出

        示例:
            输入: 'thought: "用户询问..." action: {tool: "finish", args: {answer: "..."}}'
            输出: {
                "thought": "用户询问...",
                "action": {"tool": "finish", "args": {"answer": "..."}}
            }
        """
        import re

        # 尝试提取thought
        # 匹配 "thought": "内容" 模式，支持转义字符
        thought = ""
        thought_match = re.search(r'"thought"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
        if thought_match:
            thought = thought_match.group(1).replace('\\"', '"').replace('\\n', '\n')

        # 尝试提取tool
        # 匹配 "tool": "工具名" 模式
        tool = "finish"  # 默认使用 finish 工具
        tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', text)
        if tool_match:
            tool = tool_match.group(1)

        # 尝试提取answer (如果是finish工具)
        args = {}
        if tool == "finish":
            # 提取答案内容
            answer_match = re.search(r'"answer"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
            if answer_match:
                args["answer"] = answer_match.group(1).replace('\\"', '"').replace('\\n', '\n')
            else:
                # 如果没有找到 answer，使用整个 thought 作为答案
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
        """执行工具

        根据工具名称从工具注册表中查找并调用相应的工具。
        每个工具都有自己的处理器（handler），处理器负责实际的工具调用。

        错误处理：
        - 未知工具：返回错误信息
        - finish 工具：直接返回（不需要执行）
        - 工具异常：捕获并返回错误信息

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            包含执行结果的字典：
            - success: 是否成功
            - result: 成功时返回工具结果
            - error: 失败时返回错误信息

        示例:
            result = await _execute_tool("bing_search", {"query": "Python"})
            # 返回: {"success": True, "result": {...}}
        """
        if tool_name not in self.tools:
            return {"success": False, "error": f"未知工具: {tool_name}"}

        tool = self.tools[tool_name]
        handler = tool.get("handler")

        if handler is None:
            # finish 工具不需要执行，它表示任务完成
            return {"success": True, "result": args}

        try:
            result = await handler(**args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============== 工具实现 ==============

    async def _tool_mcp_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 MCP 工具（使用多 MCP 客户端）

        这是 MCP 工具的通用调用接口。
        MultiMCPClient 提供了统一的接口来调用不同来源的 MCP 工具，
        让我们可以：
        1. 同时连接多个 MCP 服务器
        2. 自动路由请求到正确的服务器
        3. 统一处理不同工具的响应格式

        Args:
            tool_name: MCP 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果，格式为：
            - success: 是否成功
            - result: 成功时返回工具输出
            - server: 来源服务器名称
            - error: 失败时返回错误信息

        错误处理：
        - 多 MCP 客户端未初始化：返回友好错误信息
        - 工具调用失败：捕获异常并记录日志
        - 网络错误：自动重试（如果实现）

        示例:
            result = await _tool_mcp_call_tool(
                "bing_search",
                {"query": "Python教程", "count": 5}
            )
            # 返回:
            # {
            #     "success": True,
            #     "result": {"web_results": [...]},
            #     "server": "bing-mcp"
            # }
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

    async def run(self, query: str, image_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        运行ReAct循环

        这是 TrueReActAgent 的核心方法，实现了完整的 ReAct（推理与行动）循环。

        真正的ReAct流程：
        1. 模型思考并决定行动
        2. 执行工具获取观察结果
        3. 将观察结果反馈给模型
        4. 重复直到模型选择finish

        整个流程的伪代码：
        ```
        steps = []
        for i in range(1, max_iterations + 1):
            # 1. 思考
            thought = think(query, steps)

            # 2. 行动
            action = decide_action(thought)

            # 3. 观察
            if action.tool == "finish":
                break
            observation = execute_tool(action.tool, action.args)

            # 4. 记录步骤
            steps.append(action, observation)
        ```

        Args:
            query: 用户查询文本
            image_urls: 可选的图像URL列表

        Returns:
            包含完整推理结果的字典：
            - query: 原始查询
            - answer: 最终答案
            - steps: 所有步骤的字典列表
            - iterations: 迭代次数
            - success: 是否成功完成

        示例返回:
        {
            "query": "搜索Python教程",
            "answer": "Python是一种高级编程语言...",
            "steps": [
                {
                    "iteration": 1,
                    "type": "action",
                    "content": {"thought": "用户询问...", "action": {...}},
                    "tool_name": "bing_search",
                    "tool_args": {"query": "Python教程"},
                    "tool_result": {"success": True, "result": {...}},
                    "timestamp": "2025-12-19T10:30:00.000Z"
                },
                ...
            ],
            "iterations": 2,
            "success": True
        }
        """
        # 初始化服务（ OpenAI +Azure MCP 客户端 + 工具注册）
        await self.initialize()

        # 初始化变量
        steps: List[ReActStep] = []  # 存储所有步骤
        image_urls = image_urls or []  # 默认为空列表
        final_answer = ""  # 最终答案

        # 打印开始信息
        print(f"\n{'='*60}")
        print(f"[ReAct] 开始处理: {query}")
        if image_urls:
            print(f"[ReAct] 图像数量: {len(image_urls)}")
        print(f"{'='*60}")

        # 主循环：最多执行 max_iterations 次
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n--- 迭代 {iteration} ---")

            # ========== 第1步：构建对话并调用模型 ==========
            messages = self._build_conversation(query, steps, image_urls)
            model_output = await self._call_model(messages)

            # 解析模型输出
            thought = model_output.get("thought", "")
            action = model_output.get("action", {})
            tool_name = action.get("tool", "finish")
            tool_args = action.get("args", {})

            # 打印当前步骤
            print(f"[THOUGHT]: {thought[:200]}...")
            print(f"[ACTION]: {tool_name} -> {tool_args}")

            # ========== 第2步：记录思考和行动步骤 ==========
            action_step = ReActStep(
                iteration=iteration,
                step_type="action",
                content={"thought": thought, "action": action},
                tool_name=tool_name,
                tool_args=tool_args
            )
            steps.append(action_step)

            # ========== 第3步：检查是否完成 ==========
            # 如果模型选择 "finish" 工具，表示任务完成
            if tool_name == "finish":
                final_answer = tool_args.get("answer", "")
                print(f"[FINISH]: {final_answer[:200]}...")
                break  # 退出循环

            # ========== 第4步：执行工具 ==========
            tool_result = await self._execute_tool(tool_name, tool_args)
            print(f"[OBSERVATION]: {json.dumps(tool_result, ensure_ascii=False)[:200]}...")

            # 将tool_result添加到action步骤中，这样main.py可以获取到
            # 这是为了在流式输出时能够显示工具执行结果
            action_step.tool_result = tool_result

            # ========== 第5步：记录观察步骤 ==========
            obs_step = ReActStep(
                iteration=iteration,
                step_type="observation",
                content=tool_result,
                tool_name=tool_name,
                tool_result=tool_result
            )
            steps.append(obs_step)

            # 循环继续，下次迭代会将观察结果反馈给模型

        else:
            # 如果循环正常结束（未执行 break），说明达到最大迭代次数
            final_answer = "抱歉，处理超时，无法完成任务。"

        # 打印完成信息
        print(f"\n{'='*60}")
        print(f"[ReAct] 完成，共 {iteration} 次迭代")
        print(f"[最终答案]: {final_answer}")
        print(f"{'='*60}\n")

        # 返回完整的推理结果
        return {
            "query": query,
            "answer": final_answer,
            "steps": [s.to_dict() for s in steps],
            "iterations": iteration,
            "success": True
        }


# 全局实例
# 创建 TrueReActAgent 的全局实例，供其他模块直接使用
# 这样可以避免重复创建实例，提高性能
true_react_agent = TrueReActAgent()
