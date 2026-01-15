import os
from typing import Optional

# 加载 .env 文件
try:
    
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有安装 python-dotenv，跳过加载
    pass

class Settings:
    """应用配置管理"""

    # Azure OpenAI 配置（GPT-4.1）
    azure_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    azure_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

    # OpenAI 配置（Gemini-3-Flash-Preview）
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "sk-hk69mLmsHF6FfIM8cPn2Zitfk0Jca6suzwIptZymPn6h1u6x")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://llm.onerouter.pro/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gemini-3-flash-preview")

    # MCP 配置
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "https://mcp.api-inference.modelscope.net/af62266fafca44/mcp")

    # OpenWeatherMap API 配置
    openweathermap_api_key: str = os.getenv("OPENWEATHERMAP_API_KEY", "")

    # 本地 MCP 服务配置（联系人、文件、日程管理）
    test_mcp_base_url: str = os.getenv("TEST_MCP_BASE_URL", "http://192.168.106.108:8001")
    mcp_service_token: str = os.getenv("MCP_SERVICE_TOKEN", "test-service-token")

    # Chat API 配置（用于获取聊天历史）
    chat_api_base_url: str = os.getenv("CHAT_API_BASE_URL", "http://192.168.106.108:8000")

    # 应用配置
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    # 模型选择配置
    use_model: str = os.getenv("USE_MODEL", "doubao")  # "gemini"、"gpt4.1" 或 "doubao"

    # ==============================================

    # ==============================================

    # 字节跳动豆包配置
    doubao_api_key: str = os.getenv("DOUBAO_API_KEY", "c1f41437-c76b-4aed-af78-f02b14d6d518")
    doubao_base_url: str = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/")
    doubao_model: str = os.getenv("DOUBAO_MODEL", "doubao-seed-1-8-251228")
    doubao_timeout: int = int(os.getenv("DOUBAO_TIMEOUT", "30"))

    # 阿里云百炼Qwen配置
    qianwen_api_key: str = os.getenv("QWEN_API_KEY", "sk-141e3f6730b5449fb614e2888afd6c69")
    qianwen_base_url: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    qianwen_model: str = os.getenv("QWEN_MODEL", "qwen3-vl-plus")
    qianwen_timeout: int = int(os.getenv("QWEN_TIMEOUT", "30"))

    # DeepSeek配置
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_timeout: int = int(os.getenv("DEEPSEEK_TIMEOUT", "30"))

    # OneRouter Gemini配置
    onerouter_api_key: str = os.getenv("ONEROUTER_API_KEY", "")
    onerouter_base_url: str = os.getenv("ONEROUTER_BASE_URL", "https://api.onerouter.com/v1")
    onerouter_model: str = os.getenv("ONEROUTER_MODEL", "gemini-3-flash")
    onerouter_timeout: int = int(os.getenv("ONEROUTER_TIMEOUT", "30"))

    # ==============================================
    # 速度测试通用配置
    # ==============================================
    speed_test_delay: float = float(os.getenv("SPEED_TEST_DELAY", "2.0"))
    speed_test_timeout: int = int(os.getenv("SPEED_TEST_TIMEOUT", "30"))
    speed_test_output_dir: str = os.getenv("SPEED_TEST_OUTPUT_DIR", ".")
    speed_test_prompts_file: str = os.getenv("SPEED_TEST_PROMPTS_FILE", "benchmark_prompts_20.json")

    def validate(self):
        """验证必需的配置项"""
        if not self.azure_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT 环境变量未设置")
        if not self.azure_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY 环境变量未设置")
        if not self.azure_deployment_name:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME 环境变量未设置")

# 创建全局设置实例
settings = Settings()