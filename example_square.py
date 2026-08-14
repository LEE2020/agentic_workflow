import json
import os
from typing import Optional

from openai import OpenAI

from tools.registry import ToolRegistry

# ============================================
# 1. 初始化客户端
# ============================================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or "sk-xxx",
    base_url="https://api.deepseek.com",
)

# ============================================
# 2. 工具函数（实际执行的代码）
# ============================================
registry = ToolRegistry()


@registry.register
def square(n: float) -> str:
    """计算一个数的平方。"""
    result = n * n
    return str(result)


tools = registry.get_tools()

# ============================================
# 3. 工具执行器
# ============================================
def run_tool(tool_name, arguments):
    """执行工具"""
    return str(registry.execute(tool_name, arguments))


# ============================================
# 4. 主对话函数
# ============================================
def chat_with_max_turns(
    prompt: str,
    max_turns: int = 5,
    system_prompt: Optional[str] = None,
    verbose: bool = True,
) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    if verbose:
        print("=" * 60)
        print(f"📤 用户: {prompt}")
        print("=" * 60)

    turn_count = 0
    while turn_count < max_turns:
        turn_count += 1
        if verbose:
            print(f"\n🔄 第 {turn_count}/{max_turns} 轮")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
        )
        assistant_message = response.choices[0].message

        if assistant_message.tool_calls:
            if verbose:
                print("🔧 模型决定调用工具")
            messages.append(assistant_message)

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                if verbose:
                    print(f"   ├─ 工具: {tool_name}")
                    print(f"   ├─ 参数: {arguments}")

                tool_result = run_tool(tool_name, arguments)
                if verbose:
                    print(f"   └─ 结果: {tool_result}")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    }
                )
            continue

        final_answer = assistant_message.content
        if verbose:
            print("\n" + "=" * 60)
            print("📢 最终回答:")
            print("=" * 60)
            print(final_answer)
        return final_answer

    if verbose:
        print(f"\n⚠️ 达到最大轮数限制 ({max_turns})，强制结束")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
    )
    return response.choices[0].message.content or "达到最大轮数限制，未能生成回答。"


def chat2(prompt: str, max_turns: int = 5) -> str:
    return chat_with_max_turns(prompt, max_turns, verbose=True)


# ============================================
# 5. 测试
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("测试: 计算 2 的平方")
    print("=" * 50)
    result = chat2("请计算 2 的平方", max_turns=3)
    print(result)
