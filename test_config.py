#!/usr/bin/env python3
"""
测试配置文件加载
"""
import asyncio
from config import settings


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("配置文件加载测试")
    print("=" * 60)

    # Azure OpenAI 配置
    print("\n📋 Azure OpenAI 配置:")
    print(f"   端点: {settings.azure_endpoint}")
    print(f"   API 密钥: {settings.azure_api_key[:10]}...{settings.azure_api_key[-5:]}")
    print(f"   API 版本: {settings.azure_api_version}")
    print(f"   部署名称: {settings.azure_deployment_name}")

    # MCP 配置
    print("\n📋 MCP 配置:")
    print(f"   服务器 URL: {settings.mcp_server_url}")

    # OpenWeatherMap API 配置
    print("\n📋 OpenWeatherMap API 配置:")
    if settings.openweathermap_api_key:
        print(f"   API 密钥: {settings.openweathermap_api_key[:10]}...{settings.openweathermap_api_key[-5:]}")
        print(f"   ✅ API 密钥已配置")
    else:
        print(f"   ❌ API 密钥未配置")

    # 应用配置
    print("\n📋 应用配置:")
    print(f"   主机: {settings.app_host}")
    print(f"   端口: {settings.app_port}")

    print("\n" + "=" * 60)
    print("配置加载完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
