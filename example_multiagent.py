import ast
import json
import re
from datetime import datetime

from openai import OpenAI

import research_tools
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEFAULT_MODEL

CLIENT = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

TOOL_MAPPING = research_tools.TOOL_MAPPING


def clean_json_block(raw: str) -> str:
    """Clean JSON/Python that may come wrapped with Markdown fences."""
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json|python)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


def planner_agent(topic: str, model: str = DEFAULT_MODEL) -> list[str]:
    """
    Generates a plan as a Python list of steps (strings) for a research workflow.
    """
    user_prompt = f"""
    You are a planning agent responsible for organizing a research workflow with multiple intelligent agents.

    🧠 Available agents:
    - A research agent who can search the web, Wikipedia, and arXiv.
    - A writer agent who can draft research summaries.
    - An editor agent who can reflect and revise the drafts.

    🎯 Your job is to write a clear, step-by-step research plan **as a valid Python list**, where each step is a string.
    Each step should be atomic, executable, and must rely only on the capabilities of the above agents.

    🚫 DO NOT include irrelevant tasks like "create CSV", "set up a repo", "install packages", etc.
    ✅ DO include real research-related tasks (e.g., search, summarize, draft, revise).
    ✅ DO assume tool use is available.
    ✅ DO NOT include explanation text — return ONLY the Python list.
    ✅ The final step should be to generate a Markdown document containing the complete research report.

    Topic: "{topic}"
    """
    messages = [{"role": "user", "content": user_prompt}]

    response = CLIENT.chat.completions.create(
        model=model,
        messages=messages,
        temperature=1,
    )

    steps_str = clean_json_block(response.choices[0].message.content)
    steps = ast.literal_eval(steps_str)
    if not isinstance(steps, list):
        raise ValueError("Planner did not return a Python list.")
    return [str(step) for step in steps]


def research_agent(task: str, model: str = DEFAULT_MODEL, return_messages: bool = False):
    """
    Executes a research task using arXiv, Tavily, and Wikipedia tools.
    Returns either the assistant text, or (text, messages) if return_messages=True.
    """
    print("==================================")
    print("🔍 Research Agent")
    print("==================================")

    current_time = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""You are a research assistant.
You can use arxiv_search_tool, tavily_search_tool, and wikipedia_search_tool.
Today is {current_time}.
Complete this task with citations and full URLs:
{task}
"""
    messages = [{"role": "user", "content": prompt}]
    tools = [
        research_tools.arxiv_tool_def,
        research_tools.tavily_tool_def,
        research_tools.wikipedia_tool_def,
    ]

    content = ""
    for _ in range(6):
        response = CLIENT.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            content = msg.content or ""
            break

        for call in msg.tool_calls:
            tool_name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            print(f"🛠️ {tool_name}({args})")
            try:
                result = TOOL_MAPPING[tool_name](**args)
            except Exception as e:
                result = {"error": str(e)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": tool_name,
                    "content": json.dumps(result, default=str),
                }
            )

    print("✅ Output:\n", content)
    return (content, messages) if return_messages else content


def writer_agent(task: str, model: str = DEFAULT_MODEL) -> str:
    """Executes writing tasks, such as drafting, expanding, or summarizing text."""
    print("==================================")
    print("✍️ Writer Agent")
    print("==================================")

    system_prompt = (
        "You are a writing agent specialized in generating well-structured "
        "academic or technical content."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    response = CLIENT.chat.completions.create(
        model=model,
        messages=messages,
        temperature=1.0,
    )
    return response.choices[0].message.content


def editor_agent(task: str, model: str = DEFAULT_MODEL) -> str:
    """Executes editorial tasks such as reflection, critique, or revision."""
    print("==================================")
    print("🧠 Editor Agent")
    print("==================================")

    system_prompt = (
        "You are an editor agent specialized in reflecting on, critiquing, "
        "or improving existing drafts."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    response = CLIENT.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content


agent_registry = {
    "research_agent": research_agent,
    "editor_agent": editor_agent,
    "writer_agent": writer_agent,
}


def executor_agent(topic, model: str = DEFAULT_MODEL, limit_steps: bool = True):
    plan_steps = planner_agent(topic, model=model)
    max_steps = 4

    if limit_steps:
        plan_steps = plan_steps[: min(len(plan_steps), max_steps)]

    history = []

    print("==================================")
    print("🎯 Executor Agent")
    print("==================================")

    for i, step in enumerate(plan_steps):
        agent_decision_prompt = f"""
        You are an execution manager for a multi-agent research team.

        Given the following instruction, identify which agent should perform it and extract the clean task.

        Return only a valid JSON object with two keys:
        - "agent": one of ["research_agent", "editor_agent", "writer_agent"]
        - "task": a string with the instruction that the agent should follow

        Only respond with a valid JSON object. Do not include explanations or markdown formatting.

        Instruction: "{step}"
        """
        response = CLIENT.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": agent_decision_prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        agent_info = json.loads(clean_json_block(raw_content))

        agent_name = agent_info["agent"]
        task = agent_info["task"]

        context = "\n".join(
            [
                f"Step {j + 1} executed by {a}:\n{r}"
                for j, (s, a, r) in enumerate(history)
            ]
        )
        enriched_task = f"""
        You are {agent_name}.

        Here is the context of what has been done so far:
        {context}

        Your next task is:
        {task}
        """

        print(f"\n🛠️ Executing with agent: `{agent_name}` on task: {task}")

        if agent_name in agent_registry:
            output = agent_registry[agent_name](enriched_task)
            history.append((step, agent_name, output))
        else:
            output = f"⚠️ Unknown agent: {agent_name}"
            history.append((step, agent_name, output))

        print(f"✅ Output:\n{output}")

    return history


if __name__ == "__main__":
    executor_history = executor_agent(
        "The ensemble Kalman filter for time series forecasting",
        limit_steps=True,
    )
    md = (executor_history[-1][-1] or "").strip("`")
    print("\n=== Final Markdown ===\n")
    print(md)
