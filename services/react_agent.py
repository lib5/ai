"""
ReAct (Reasoning and Acting) Agent for chat API
Implements the ReAct pattern: Reason -> Act -> Observe -> Repeat
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime
import uuid


class Tool:
    """Tool definition for ReAct agent"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.function = function


class ReActAgent:
    """
    ReAct Agent that combines reasoning and acting in a loop

    Pattern: Thought -> Action -> Observation -> (repeat) -> Final Answer
    """

    def __init__(self, tools: Optional[List[Tool]] = None):
        self.tools = tools or []
        self.tool_registry = {tool.name: tool for tool in self.tools}
        self.max_iterations = 10

        # Print all registered tools
        print(f"\n=== ReAct Agent initialized with {len(self.tools)} tools ===")
        for tool in self.tools:
            print(f"  - {tool.name}: {tool.description}")
        print("==========================================\n")

    def add_tool(self, tool: Tool):
        """Add a tool to the agent"""
        self.tool_registry[tool.name] = tool

    async def think(self, query: str, context: Optional[List[Dict]] = None) -> str:
        """
        Generate reasoning based on query and context
        Uses Azure OpenAI to generate thoughts
        """
        from services.azure_openai_service import AzureOpenAIService
        from config import settings

        # Print available tools for debugging
        print(f"\n[THINK] Available tools for query '{query}':")
        for name, tool in self.tool_registry.items():
            print(f"  - {name}: {tool.description}")
        print()

        # Use Azure OpenAI to generate detailed reasoning and tool selection
        prompt = f"""分析以下用户查询，确定需要采取的行动:

用户查询: {query}

可用工具:
{json.dumps([{"name": name, "description": tool.description} for name, tool in self.tool_registry.items()], indent=2, ensure_ascii=False)}

请分析查询内容，思考需要使用哪个工具，并给出详细的推理过程。
特别关注：
1. 如果查询涉及天气信息，应该使用 MCP 工具
2. 如果查询需要搜索网络信息，使用 web_search
3. 如果查询涉及图像，使用 analyze_image 或 search_image
4. 如果查询询问时间，使用 get_current_time
5. 如果是简单对话，不需要工具

请生成思考过程，说明需要使用哪个工具以及原因。
"""

        messages = [
            {"role": "system", "content": "你是一个ReAct智能体，需要分析用户查询并选择合适的工具。"},
            {"role": "user", "content": prompt}
        ]

        try:
            azure_service = AzureOpenAIService(
                endpoint=settings.azure_endpoint,
                api_key=settings.azure_api_key,
                api_version=settings.azure_api_version,
                deployment_name=settings.azure_deployment_name
            )
            response = await azure_service.chat_completion(messages, max_tokens=300)
            thought = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return thought or f"需要查询: {query}"
        except Exception:
            # Fallback to simple reasoning
            return f"用户询问: {query}。需要分析查询内容并确定合适的行动。"

    async def act(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the specified tool with given arguments
        """
        # Handle special case: no tool needed
        if tool_name == "no_tool_needed":
            print(f"[ACT] Executing: no_tool_needed")
            return {
                "tool": tool_name,
                "result": {
                    "message": "无需工具，可直接回答",
                    "reason": arguments.get("reason", "unknown")
                }
            }

        if tool_name not in self.tool_registry:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        tool = self.tool_registry[tool_name]

        # Print tool execution
        print(f"\n[ACT] Executing tool: {tool_name}")
        print(f"[ACT] Description: {tool.description}")
        print(f"[ACT] Arguments: {arguments}")

        result = await tool.function(**arguments)

        print(f"[ACT] Completed tool: {tool_name}")

        return {
            "tool": tool_name,
            "result": result
        }

    async def run(
        self,
        query: str,
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Main ReAct loop: Think -> Act -> Observe -> (repeat)

        Args:
            query: User query
            max_iterations: Maximum number of reasoning-acting iterations

        Returns:
            Dict containing the final answer and trace of reasoning
        """
        max_iterations = max_iterations or self.max_iterations
        trace = []
        context = []

        for iteration in range(max_iterations):
            # Step 1: Think (Reasoning)
            thought = await self.think(query, context)
            trace.append({
                "iteration": iteration + 1,
                "type": "thought",
                "content": thought
            })

            # Step 2: Decide Action
            # Simple heuristic: if query contains "search", use search tool
            # In production, this would be more sophisticated (LLM-based)
            action = await self._decide_action(query, context, thought)
            trace.append({
                "iteration": iteration + 1,
                "type": "action",
                "content": action
            })

            # Step 3: Act (Execute tool)
            try:
                observation = await self.act(action["tool"], action["arguments"])
                trace.append({
                    "iteration": iteration + 1,
                    "type": "observation",
                    "content": observation
                })
                context.append(observation)

                # Check if we have enough information to answer
                if self._should_finish(query, context, observation):
                    break

            except Exception as e:
                trace.append({
                    "iteration": iteration + 1,
                    "type": "error",
                    "content": str(e)
                })
                break

        # Step 4: Generate Final Answer
        final_answer = await self._generate_final_answer(query, context, trace)

        return {
            "answer": final_answer,
            "trace": trace,
            "iterations": iteration + 1,  # Actual iteration count
            "success": True
        }

    async def _decide_action(
        self,
        query: str,
        context: List[Dict],
        thought: str
    ) -> Dict[str, Any]:
        """
        Decide which action to take based on query and thought
        Uses Azure OpenAI to analyze the thought and determine the best tool
        """
        from services.azure_openai_service import AzureOpenAIService
        from config import settings

        # Print decision process
        print(f"\n[ACTION] Deciding action for query: '{query}'")
        print(f"[ACTION] Thought: {thought[:200]}...")

        # Use Azure OpenAI to analyze the thought and decide the best tool
        decision_prompt = f"""基于以下思考过程，决定最佳的工具选择:

用户查询: {query}

思考过程:
{thought}

可用工具:
- web_search: 搜索网络获取信息
- get_current_time: 获取当前时间
- analyze_image: 分析图像内容
- search_image: 搜索图像
- mcp_call_tool: 调用 MCP 服务器上的工具（用于天气、模型等特殊功能）

请基于思考过程，选择最合适的工具，并提供以下JSON格式的响应：
{{
    "tool": "工具名称",
    "arguments": {{
        "query": "搜索关键词或查询内容",
        "location": "位置信息（如适用）"
    }},
    "reason": "选择此工具的原因"
}}

特别注意：
1. 如果查询涉及天气信息，应使用 mcp_call_tool 调用天气工具
2. 如果思考过程明确提到使用某个工具，请选择该工具
3. 如果是简单对话，选择 no_tool_needed
"""

        messages = [
            {"role": "system", "content": "你是一个决策智能体，需要根据思考过程选择最合适的工具。请只返回JSON格式的决策结果，不要额外的解释。"},
            {"role": "user", "content": decision_prompt}
        ]

        try:
            azure_service = AzureOpenAIService(
                endpoint=settings.azure_endpoint,
                api_key=settings.azure_api_key,
                api_version=settings.azure_api_version,
                deployment_name=settings.azure_deployment_name
            )
            response = await azure_service.chat_completion(messages, max_tokens=200)
            decision_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Try to parse the JSON decision
            try:
                # Extract JSON from the response (in case there's extra text)
                import re
                json_match = re.search(r'\{.*\}', decision_text, re.DOTALL)
                if json_match:
                    decision_json = json.loads(json_match.group())

                    tool_name = decision_json.get("tool", "web_search")
                    arguments = decision_json.get("arguments", {})

                    # Special handling for weather queries
                    if tool_name == "mcp_call_tool" and "weather" in arguments.get("tool_name", "").lower():
                        print(f"[ACTION] Selected tool: mcp_call_tool (weather query via MCP)")
                        return {
                            "tool": "mcp_call_tool",
                            "arguments": arguments
                        }

                    print(f"[ACTION] Selected tool: {tool_name} (AI decision)")
                    return {
                        "tool": tool_name,
                        "arguments": arguments
                    }
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[ACTION] Failed to parse AI decision, using fallback: {e}")

        except Exception as e:
            print(f"[ACTION] AI decision failed: {e}")

        # Fallback to rule-based decision
        query_lower = query.lower()

        # Check if query asks for weather information
        if any(word in query_lower for word in ["天气", "weather", "气温", "下雨", "晴天", "多云"]):
            print(f"[ACTION] Selected tool: mcp_call_tool (weather query - fallback)")

            # Extract location from query
            location = "北京"  # Default location
            cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "重庆"]
            for city in cities:
                if city in query:
                    location = city
                    break

            return {
                "tool": "mcp_call_tool",
                "arguments": {
                    "tool_name": "weather.get_weather",
                    "arguments": {
                        "location": location,
                        "query": query
                    }
                }
            }

        # Check if query asks for current time
        if "时间" in query_lower or "time" in query_lower:
            print(f"[ACTION] Selected tool: get_current_time (time query)")
            return {
                "tool": "get_current_time",
                "arguments": {}
            }

        # Check if query asks for an image
        if "image" in query_lower or "图片" in query_lower:
            if "search" in query_lower:
                print(f"[ACTION] Selected tool: search_image (image search)")
                return {
                    "tool": "search_image",
                    "arguments": {"query": query}
                }
            else:
                print(f"[ACTION] Selected tool: analyze_image (image analysis)")
                return {
                    "tool": "analyze_image",
                    "arguments": {"query": query}
                }

        # Check if query is a simple greeting
        if any(word in query_lower for word in [
            "你好", "hello", "hi",
            "你是谁", "who are you"
        ]) and not any(topic_word in query_lower for topic_word in [
            "fastmcp", "mcp", "介绍", "introduce", "解释", "explain",
            "时间", "time", "天气", "weather"
        ]):
            print(f"[ACTION] Selected tool: no_tool_needed (simple conversation)")
            return {
                "tool": "no_tool_needed",
                "arguments": {"query": query, "reason": "simple_conversation"}
            }

        # Default: search for information
        print(f"[ACTION] Selected tool: web_search (default for information query)")
        return {
            "tool": "web_search",
            "arguments": {"query": query}
        }

    def _should_finish(
        self,
        query: str,
        context: List[Dict],
        observation: Dict[str, Any]
    ) -> bool:
        """
        Determine if we have enough information to provide a final answer
        """
        # Simple heuristic: if we have at least one successful observation, we can finish
        return len(context) >= 1

    async def _generate_final_answer(
        self,
        query: str,
        context: List[Dict],
        trace: List[Dict]
    ) -> str:
        """
        Generate the final answer based on all observations
        """
        from services.azure_openai_service import AzureOpenAIService
        from config import settings

        # Check if we have a "no_tool_needed" observation
        for obs in trace:
            if obs['type'] == 'observation':
                content = obs['content']
                if isinstance(content, dict) and content.get('tool') == 'no_tool_needed':
                    # This is a simple conversation, call model to generate response
                    try:
                        messages = [
                            {
                                "role": "system",
                                "content": "你是一个智能的AI助手。请根据用户的问题，提供准确、有帮助的回答。如果问题是关于你的身份或能力，请简洁地介绍自己。"
                            },
                            {
                                "role": "user",
                                "content": query
                            }
                        ]

                        azure_service = AzureOpenAIService(
                            endpoint=settings.azure_endpoint,
                            api_key=settings.azure_api_key,
                            api_version=settings.azure_api_version,
                            deployment_name=settings.azure_deployment_name
                        )
                        response = await azure_service.chat_completion(
                            messages,
                            max_tokens=500,
                            temperature=0.7
                        )
                        answer = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                        if answer:
                            return answer
                        else:
                            return "抱歉，我暂时无法生成回答。"

                    except Exception as e:
                        print(f"调用模型生成答案时出错: {e}")
                        # 降级策略：简单回答
                        query_lower = query.lower()
                        if any(word in query_lower for word in ["你好", "hello", "hi", "介绍", "introduce"]):
                            return "你好！我是Claude Code，一个AI编程助手，专门帮助开发者完成各种编程任务。"
                        elif any(word in query_lower for word in ["你是谁", "who are you"]):
                            return "我是Claude Code，Anthropic开发的AI助手，专门为软件开发者提供编程支持。"
                        else:
                            return "我是Claude Code，一个AI编程助手。"

        # Compile all observations for queries that need tools
        observations_text = "\n".join([
            f"- {obs['content']}"
            for obs in trace
            if obs['type'] == 'observation'
        ])

        prompt = f"""基于以下信息回答用户查询:

用户查询: {query}

收集到的信息:
{observations_text}

请提供准确、简洁的最终答案。
"""

        messages = [
            {"role": "system", "content": "你是一个有用的AI助手，基于收集到的信息回答用户问题。"},
            {"role": "user", "content": prompt}
        ]

        try:
            azure_service = AzureOpenAIService(
                endpoint=settings.azure_endpoint,
                api_key=settings.azure_api_key,
                api_version=settings.azure_api_version,
                deployment_name=settings.azure_deployment_name
            )
            response = await azure_service.chat_completion(messages, max_tokens=500)
            answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return answer or "基于收集到的信息，我无法提供确切的答案。"
        except Exception as e:
            # Better fallback: try to generate a simple answer based on query type
            query_lower = query.lower()
            if "搜索" in query_lower or "search" in query_lower:
                return f"根据搜索结果，我找到了一些关于'{query}'的信息。搜索完成。"

            # Default fallback
            return f"基于收集到的信息: {observations_text[:200]}..."


# Built-in Tools for ReAct Agent

async def search_web(query: str) -> Dict[str, Any]:
    """Search the web for information"""
    # Placeholder for web search
    return {
        "query": query,
        "results": f"搜索结果模拟: 关于'{query}'的信息",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


async def analyze_image(image_url: str, query: str) -> Dict[str, Any]:
    """Analyze an image"""
    # Placeholder for image analysis
    return {
        "image_url": image_url,
        "analysis": f"图像分析模拟: 检测到图像内容，查询: {query}",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


async def search_image(query: str) -> Dict[str, Any]:
    """Search for images"""
    # Placeholder for image search
    return {
        "query": query,
        "images": f"图像搜索结果模拟: 找到与'{query}'相关的图像",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


async def get_current_time() -> Dict[str, Any]:
    """Get current time"""
    return {
        "current_time": datetime.utcnow().isoformat() + "Z",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a tool on the MCP server

    Args:
        tool_name: MCP tool name
        arguments: Tool arguments

    Returns:
        Tool execution result
    """
    from services.mcp_client import MCPClient
    from config import settings

    mcp_server_url = getattr(settings, 'mcp_server_url', 'http://localhost:3000')

    async with MCPClient(mcp_server_url) as client:
        try:
            result = await client.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            return {
                "tool": tool_name,
                "result": f"MCP工具调用失败: {str(e)}",
                "error": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }


# Default ReAct Agent with built-in tools
default_tools = [
    Tool(
        name="web_search",
        description="Search the web for information",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        function=search_web
    ),
    Tool(
        name="analyze_image",
        description="Analyze an image to understand its content",
        parameters={
            "type": "object",
            "properties": {
                "image_url": {"type": "string"},
                "query": {"type": "string"}
            }
        },
        function=analyze_image
    ),
    Tool(
        name="search_image",
        description="Search for images based on a query",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        function=search_image
    ),
    Tool(
        name="get_current_time",
        description="Get the current time",
        parameters={"type": "object", "properties": {}},
        function=get_current_time
    ),
    Tool(
        name="mcp_call_tool",
        description="Call a tool on the MCP server. Use for weather, models, and other MCP-provided tools.",
        parameters={
            "type": "object",
            "properties": {
                "tool_name": {"type": "string"},
                "arguments": {"type": "object"}
            }
        },
        function=call_mcp_tool
    )
]

react_agent = ReActAgent(tools=default_tools)
