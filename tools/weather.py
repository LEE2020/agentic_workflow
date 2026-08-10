import requests
from .registry import registry

@registry.register
def get_weather_from_ip():
    """
    根据用户的IP地址获取当前所在位置的天气信息
    返回当前温度、最高温度和最低温度（华氏度）
    """
    try:
        # 获取IP位置
        ip_response = requests.get('https://ipinfo.io/json', timeout=5)
        ip_data = ip_response.json()
        lat, lon = ip_data['loc'].split(',')
        
        # 获取天气数据
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto"
        }
        
        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast", 
            params=params, 
            timeout=5
        )
        weather_data = weather_response.json()
        
        # 格式化返回
        return (
            f"Current: {weather_data['current']['temperature_2m']}°F, "
            f"High: {weather_data['daily']['temperature_2m_max'][0]}°F, "
            f"Low: {weather_data['daily']['temperature_2m_min'][0]}°F"
        )
    except Exception as e:
        return f"获取天气信息失败: {str(e)}"


@registry.register
def get_weather_by_city(city: str, days: int = 1):
    """
    根据城市名称获取天气信息
    :param city: 城市名称
    :param days: 预测天数（1-7天）
    """
    # 模拟数据，实际应该调用真实的天气API
    weather_data = {
        "上海": {"current": 72, "high": 78, "low": 65},
        "北京": {"current": 68, "high": 75, "low": 58},
        "广州": {"current": 82, "high": 88, "low": 75},
        "深圳": {"current": 80, "high": 86, "low": 73},
    }
    
    city_info = weather_data.get(city, {"current": 70, "high": 76, "low": 64})
    
    return (
        f"{city}天气: "
        f"当前 {city_info['current']}°F, "
        f"最高 {city_info['high']}°F, "
        f"最低 {city_info['low']}°F"
    )




