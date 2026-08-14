import ast
import cmath
import decimal
import fractions
import io
import json
import math
import os
import statistics
from contextlib import redirect_stdout
from typing import Optional

from openai import OpenAI

from tools.registry import ToolRegistry

# ============================================
# 1. 初始化客户端
# ============================================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or "",
    base_url="https://api.deepseek.com",
)

# ============================================
# 2. 受限代码执行（只做数值计算）
# ============================================
ALLOWED_MODULES = {
    "math": math,
    "statistics": statistics,
    "cmath": cmath,
    "decimal": decimal,
    "fractions": fractions,
}

SAFE_BUILTINS = {
    "abs": abs,
    "round": round,
    "pow": pow,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "sorted": sorted,
    "reversed": reversed,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "int": int,
    "float": float,
    "complex": complex,
    "bool": bool,
    "str": str,
    "print": print,
    "repr": repr,
    "isinstance": isinstance,
    "True": True,
    "False": False,
    "None": None,
}


def _safe_import(name, *args, **kwargs):
    if name in ALLOWED_MODULES:
        return ALLOWED_MODULES[name]
    raise ImportError(
        f"不允许导入 {name}。仅支持: {', '.join(sorted(ALLOWED_MODULES))}"
    )


SAFE_BUILTINS["__import__"] = _safe_import


def _validate_code(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            else:
                names = [node.module.split(".")[0]] if node.module else []
            for name in names:
                if name not in ALLOWED_MODULES:
                    raise ValueError(f"不允许导入 {name}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in {"os", "sys", "subprocess", "pathlib", "socket", "shutil"}:
                raise ValueError("不允许访问系统模块")


def _run_code(code: str) -> str:
    _validate_code(code)
    namespace = {
        "__builtins__": SAFE_BUILTINS,
        **ALLOWED_MODULES,
    }
    stdout = io.StringIO()
    tree = ast.parse(code)
    last_value = None

    with redirect_stdout(stdout):
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            body, last = tree.body[:-1], tree.body[-1]
            if body:
                exec(compile(ast.Module(body, type_ignores=[]), "<tool>", "exec"), namespace)
            last_value = eval(
                compile(ast.Expression(last.value), "<tool>", "eval"),
                namespace,
            )
        else:
            exec(compile(tree, "<tool>", "exec"), namespace)
            last_value = namespace.get("result")

    printed = stdout.getvalue().strip()
    parts = []
    if printed:
        parts.append(printed)
    if last_value is not None:
        parts.append(str(last_value))
    return "\n".join(parts) if parts else "代码已执行，无返回值"


registry = ToolRegistry()


@registry.register
def run_python_code(code: str) -> str:
    """执行 Python 代码完成数值计算。可使用 math/statistics/cmath/decimal/fractions。
    把要计算的表达式写在最后一行，或赋值给 result，或 print 输出。
    不能访问文件、网络或操作系统。"""
    try:
        return _run_code(code)
    except Exception as e:
        return f"执行失败: {type(e).__name__}: {e}"


tools = registry.get_tools()


def run_tool(tool_name, arguments):
    return str(registry.execute(tool_name, arguments))


# ============================================
# 3. 主对话函数
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
                    print(f"   ├─ 代码:\n{arguments.get('code', arguments)}")

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
    return chat_with_max_turns(
        prompt,
        max_turns,
        system_prompt=(
            "你是数值计算助手。凡是涉及计算，必须调用 run_python_code 执行代码，"
            "不要心算。代码最后一行写表达式，或 print 结果。"
        ),
        verbose=True,
    )


# ============================================
# 4. 测试
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("测试1: 用代码计算 2 的平方")
    print("=" * 50)
    print(chat2("请计算 2 的平方", max_turns=3))

    print("\n" + "=" * 50)
    print("测试2: 稍复杂的数值计算")
    print("=" * 50)
    print(chat2("请用代码计算 sqrt(2) + sin(pi/2)，保留 6 位小数", max_turns=3))
