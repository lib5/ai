#!/usr/bin/env python3
"""
天气服务 - 使用 OpenWeatherMap API 获取天气数据
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from config import settings

# OpenWeatherMap API 端点
BASE_URL = "https://api.openweathermap.org/data/2.5"


class WeatherService:
    """天气服务类"""

    def __init__(self):
        """初始化天气服务"""
        if not settings.openweathermap_api_key:
            raise ValueError("OpenWeatherMap API 密钥未配置")

        self.api_key = settings.openweathermap_api_key
        self.base_url = BASE_URL

    async def get_weather(self, city: str, units: str = "metric", lang: str = "zh_cn") -> Dict[str, Any]:
        """
        获取指定城市的天气信息

        Args:
            city: 城市名称
            units: 温度单位 (metric: 摄氏度, imperial: 华氏度)
            lang: 返回语言 (zh_cn: 中文, en: 英文)

        Returns:
            天气信息字典
        """
        url = f"{self.base_url}/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": units,
            "lang": lang
        }

        try:
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
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_weather_forecast(self, city: str, days: int = 5, units: str = "metric", lang: str = "zh_cn") -> Dict[str, Any]:
        """
        获取指定城市的天气预报

        Args:
            city: 城市名称
            days: 预报天数（最多5天）
            units: 温度单位
            lang: 返回语言

        Returns:
            天气预报信息字典
        """
        url = f"{self.base_url}/forecast"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": units,
            "lang": lang,
            "cnt": min(days * 8, 40)  # 最多5天，每3小时一个数据点
        }

        try:
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
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def format_weather_data(self, data: Dict[str, Any]) -> str:
        """
        格式化天气数据为可读文本

        Args:
            data: 天气数据

        Returns:
            格式化的天气信息
        """
        if "data" not in data or not data["success"]:
            return "无法获取天气数据"

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


async def test_weather_service():
    """测试天气服务"""
    print("\n" + "=" * 60)
    print("天气服务测试")
    print("=" * 60)

    try:
        weather_service = WeatherService()
        print("✅ 天气服务初始化成功")

        # 测试城市
        cities = ["北京", "上海", "广州"]

        for city in cities:
            print(f"\n{'='*60}")
            print(f"查询 {city} 的天气")
            print(f"{'='*60}")

            # 获取当前天气
            weather_result = await weather_service.get_weather(city)

            if weather_result["success"]:
                formatted = weather_service.format_weather_data(weather_result)
                print(formatted)
            else:
                print(f"❌ 获取天气失败: {weather_result['error']}")

            # 等待一下再查询下一个城市
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

    print("\n" + "=" * 60)


def main():
    """主函数"""
    asyncio.run(test_weather_service())


if __name__ == "__main__":
    main()
