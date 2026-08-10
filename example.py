import json
import requests
from openai import OpenAI
from typing import List, Dict, Any, Optional

# ============================================
# 1. 初始化客户端
# ============================================
client = OpenAI(
    api_key="sk-e162c7df42a347f2b23753a748878f12",  # 替换为您的 API Key
    base_url="https://api.deepseek.com"
)

# ============================================
# 2. 工具函数（实际执行的代码）
# ============================================
def get_weather_from_ip():
    """根据IP获取天气"""
    try:
        # 获取位置
        ip_data = requests.get('https://ipinfo.io/json', timeout=5).json()
        lat, lon = ip_data['loc'].split(',')
        
        # 获取天气
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto"
        }
        weather = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=5).json()
        
        return (
            f"当前温度: {weather['current']['temperature_2m']}°F, "
            f"最高: {weather['daily']['temperature_2m_max'][0]}°F, "
            f"最低: {weather['daily']['temperature_2m_min'][0]}°F"
        )
    except Exception as e:
        return f"获取天气失败: {e}"

def get_current_time():
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ============================================
# 3. 工具描述（告诉API有哪些工具可用）
# ============================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather_from_ip",
            "description": "根据用户IP获取当前位置的天气信息",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# ============================================
# 4. 工具执行器（根据名称调用对应函数）
# ============================================
def run_tool(tool_name, arguments):
    """执行工具"""
    if tool_name == "get_weather_from_ip":
        return get_weather_from_ip()
    elif tool_name == "get_current_time":
        return get_current_time()
    else:
        return f"未知工具: {tool_name}"

# ============================================
# 5. 主对话函数
# ============================================
def chat_with_max_turns(
    prompt: str,
    max_turns: int = 5,
    system_prompt: Optional[str] = None,
    verbose: bool = True
) -> str:
    """
    带 max_turns 支持的对话函数
    
    Args:
        prompt: 用户输入
        max_turns: 最大工具调用轮数
        system_prompt: 系统提示（可选）
        verbose: 是否打印详细日志
    
    Returns:
        模型的最终回答
    """
    
    # 初始化消息
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    if verbose:
        print("=" * 60)
        print(f"📤 用户: {prompt}")
        print("=" * 60)
    
    # 工具调用计数器
    turn_count = 0
    
    while turn_count < max_turns:
        turn_count += 1
        
        if verbose:
            print(f"\n🔄 第 {turn_count}/{max_turns} 轮")
        
        # 调用 API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools
        )
        
        assistant_message = response.choices[0].message
        
        # 检查是否有工具调用
        if assistant_message.tool_calls:
            if verbose:
                print(f"🔧 模型决定调用工具")
            
            # 添加助手的响应到消息历史
            messages.append(assistant_message)
            
            # 处理所有工具调用
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                if verbose:
                    print(f"   ├─ 工具: {tool_name}")
                    print(f"   ├─ 参数: {arguments}")
                
                # 执行工具
                tool_result = run_tool(tool_name, arguments)
                
                if verbose:
                    print(f"   └─ 结果: {tool_result[:50]}..." if len(tool_result) > 50 else f"   └─ 结果: {tool_result}")
                
                # 添加工具结果到消息历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
            
            # 继续循环，让模型处理工具结果
            continue
        
        # 没有工具调用，获取最终回答
        final_answer = assistant_message.content
        
        if verbose:
            print("\n" + "=" * 60)
            print("📢 最终回答:")
            print("=" * 60)
            print(final_answer)
        
        return final_answer
    
    # 达到最大轮数
    if verbose:
        print(f"\n⚠️ 达到最大轮数限制 ({max_turns})，强制结束")
    
    # 最后一次尝试获取回答
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools
    )
    return response.choices[0].message.content or "达到最大轮数限制，未能生成回答。"
def chat2(prompt: str, max_turns: int = 5) -> str:
    """简化版本"""
    return chat_with_max_turns(prompt, max_turns, verbose=True)

def chat(prompt):
    """最简单的对话函数"""
    
    # 初始化消息
    messages = [{"role": "user", "content": prompt}]
    
    # 第一次调用：让模型决定是否使用工具
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools
    )
    
    # 获取模型响应
    assistant_msg = response.choices[0].message
    
    
    # 如果模型决定调用工具
    if assistant_msg.tool_calls:
        # 添加模型响应到消息历史
        messages.append(assistant_msg)
        
        # 执行每个工具
        for tool_call in assistant_msg.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            # 执行工具
            result = run_tool(tool_name, arguments)
            print(result)
            # 添加工具结果到消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
        
        # 第二次调用：让模型根据工具结果生成最终回答
        final_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools
        )
        
        return final_response.choices[0].message.content
    
    # 如果模型直接回答
    return assistant_msg.content

# ============================================
# 6. 测试

# ============================================
if __name__ == "__main__":
    # 测试不同问题
    print("=" * 50)
    print("测试1: 查询天气")
    print("=" * 50)
    result = chat2("今天天气怎么样？",max_turns=4)
    print(result)
    """
    print("\n" + "=" * 50)
    print("测试2: 查询时间")
    print("=" * 50)
    result = chat("现在几点了？")
    print(result)
    
    print("\n" + "=" * 50)
    print("测试3: 普通问题（不调用工具）")
    print("=" * 50)
    result = chat("你好，今天心情很好")
    print(result) """