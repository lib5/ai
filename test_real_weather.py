#!/usr/bin/env python3
"""
使用真实的 OpenWeatherMap API 密钥测试天气功能
"""
import asyncio
import json
import aiohttp

# 你的 API 密钥
API_KEY = "5e3acfe278eef67a645b81c6cb811f57"

# OpenWeatherMap API 端点
BASE_URL = "https://api.openweathermap.org/data/2.5"


async def get_weather(city: str, units: str = "metric", lang: str = "zh_cn"):
    """
    获取指定城市的天气信息

    Args:
        city: 城市名称
        units: 温度单位 (metric: 摄氏度, imperial: 华氏度)
        lang: 返回语言 (zh_cn: 中文, en: 英文)

    Returns:
        天气信息
    """
    url = f"{BASE_URL}/weather"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": units,
        "lang": lang
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "success": True,
                    "data": data
                }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "error": f"HTTP {response.status}: {error_text}"
                }


async def get_weather_forecast(city: str, days: int = 5, units: str = "metric", lang: str = "zh_cn"):
    """
    获取指定城市的天气预报

    Args:
        city: 城市名称
        days: 预报天数（最多5天）
        units: 温度单位
        lang: 返回语言

    Returns:
        天气预报信息
    """
    url = f"{BASE_URL}/forecast"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": units,
        "lang": lang,
        "cnt": days * 8  # 每3小时一个数据点，一天8个
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "success": True,
                    "data": data
                }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "error": f"HTTP {response.status}: {error_text}"
                }


def format_weather_data(data: dict) -> str:
    """格式化天气数据为可读文本"""
    if "data" not in data:
        return "无数据"

    weather = data["data"]
    city_name = weather.get("name", "未知城市")
    country = weather.get("sys", {}).get("country", "")

    # 当前天气
    main = weather.get("main", {})
    temp = main.get("temp", "N/A")
    feels_like = main.get("feels_like", "N/A")
    humidity = main.get("humidity", "N/A")
    pressure = main.get("pressure", "N/A")

    # 天气描述
    weather_desc = weather.get("weather", [{}])[0].get("description", "N/A")

    # 风
    wind = weather.get("wind", {})
    wind_speed = wind.get("speed", "N/A")
    wind_deg = wind.get("deg", "N/A")

    # 云量
    clouds = weather.get("clouds", {}).get("all", "N/A")

    result = f"""
{city_name}, {country} 天气情况：

🌡️  温度：{temp}°C（体感 {feels_like}°C）
🌤️  天气：{weather_desc}
💧  湿度：{humidity}%
🌬️  风速：{wind_speed} m/s（方向 {wind_deg}°）
☁️  云量：{clouds}%
🔽  气压：{pressure} hPa
"""
    return result


async def test_real_weather():
    """测试真实天气数据"""
    print("\n" + "=" * 60)
    print("使用真实 OpenWeatherMap API 测试天气数据")
    print("=" * 60)

    # 测试城市列表
    cities = ["北京", "上海", "广州", "深圳", "杭州"]

    for city in cities:
        print(f"\n{'='*60}")
        print(f"查询 {city} 的天气信息")
        print(f"{'='*60}")

        # 获取当前天气
        print(f"\n📍 当前天气:")
        weather_result = await get_weather(city)

        if weather_result["success"]:
            formatted = format_weather_data(weather_result)
            print(formatted)
        else:
            print(f"❌ 获取天气失败: {weather_result['error']}")

        # 获取天气预报
        print(f"\n📅 天气预报:")
        forecast_result = await get_weather_forecast(city, days=3)

        if forecast_result["success"]:
            forecast_data = forecast_result["data"]
            print(f"城市: {forecast_data.get('city', {}).get('name', 'N/A')}")
            print(f"预报列表条目数: {len(forecast_data.get('list', []))}")
            print("\n前3天预报:")
            for i, item in enumerate(forecast_data.get('list', [])[:3], 1):
                dt = item.get('dt_txt', 'N/A')
                temp = item.get('main', {}).get('temp', 'N/A')
                desc = item.get('weather', [{}])[0].get('description', 'N/A')
                print(f"  {i}. {dt}: {temp}°C, {desc}")
        else:
            print(f"❌ 获取预报失败: {forecast_result['error']}")

        # 等待一下再查询下一个城市
        await asyncio.sleep(0.5)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


async def test_mcp_with_real_api():
    """测试 MCP 工具与真实 API 密钥的集成"""
    print("\n" + "=" * 60)
    print("测试 MCP 工具与真实 API 集成")
    print("=" * 60)

    # 使用 ReAct Agent 手动调用 MCP 工具（如果可用）
    try:
        from services.true_react_agent import TrueReActAgent

        agent = TrueReActAgent()
        await agent.initialize()

        print(f"\n✅ ReAct Agent 初始化成功")

        # 手动调用 MCP 工具
        print(f"\n🧪 通过 ReAct Agent 调用 MCP 工具...")
        mcp_result = await agent._tool_mcp_call_tool("get_weather", {
            "city": "北京",
            "units": "metric",
            "lang": "zh_cn"
        })

        if mcp_result.get('success'):
            print(f"✅ MCP 工具调用成功!")
            if 'result' in mcp_result:
                print(f"结果:")
                print(json.dumps(mcp_result['result'], indent=2, ensure_ascii=False))
        else:
            print(f"⚠️  MCP 工具调用失败:")
            print(f"错误: {mcp_result.get('error')}")
            print("\n💡 提示: 天气 MCP 服务器需要配置 API 密钥才能工作")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

    print("\n" + "=" * 60)


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpenWeatherMap API 测试")
    print("=" * 60)
    print(f"\nAPI 密钥: {API_KEY[:10]}...{API_KEY[-5:]}")

    # 测试 1: 直接使用 API
    await test_real_weather()

    # 测试 2: 测试 MCP 集成
    await test_mcp_with_real_api()

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
