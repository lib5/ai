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

    # Azure OpenAI 配置
    azure_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    azure_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

    # MCP 配置
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "https://mcp.api-inference.modelscope.net/af62266fafca44/mcp")

    # OpenWeatherMap API 配置
    openweathermap_api_key: str = os.getenv("OPENWEATHERMAP_API_KEY", "")

    # 本地 MCP 服务配置（联系人、文件、日程管理）
    test_mcp_base_url: str = os.getenv("TEST_MCP_BASE_URL", "http://192.168.106.108:8001")
    mcp_service_token: str = os.getenv("MCP_SERVICE_TOKEN", "test-service-token")

    # 应用配置
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

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