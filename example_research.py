import json
import os
import webbrowser
# ================================
# Third-party imports
# ================================
from dotenv import load_dotenv
from openai import OpenAI

import research_tools


# ================================
# Environment setup
# ================================
load_dotenv()  # Load environment variables from .env file

# DeepSeek is OpenAI-compatible; use deepseek-chat instead of gpt-4o.
CLIENT = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or "",
    base_url="https://api.deepseek.com"
)

TOOL_MAPPING = research_tools.TOOL_MAPPING

DEFAULT_MODEL = "deepseek-chat"



# GRADED FUNCTION: generate_research_report_with_tools
def generate_research_report_with_tools(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Generates a research report using OpenAI's tool-calling with arXiv, Tavily,
    OpenAlex, and Crossref tools.

    Args:
        prompt (str): The user prompt.
        model (str): OpenAI model name.

    Returns:
        str: Final assistant research report text.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a research assistant that writes detailed, accurate, properly sourced reports.\n\n"
                "Prefer sources with strong scholarly backing:\n"
                "- Crossref: official DOI registry; publisher-registered journal articles.\n"
                "- OpenAlex: journal articles with DOI, venue, and citation counts (>5).\n"
                "- arXiv: latest preprints; pair with Crossref/OpenAlex when a DOI/venue exists.\n"
                "- Tavily: general web context only, not a substitute for scholarly citations.\n"
                "When citing, include venue, year, DOI/URL, and citation count when available. "
                "Prefer highly cited, peer-reviewed papers over unreviewed web pages.\n"
                "Use tools when appropriate. Do NOT omit citations. Include full URLs. "
                "Use an academic tone and labeled sections. "
                "Do not include placeholder text such as '(citation needed)'."
            )
        },
        {"role": "user", "content": prompt}
    ]

    # List of available tools
    tools = research_tools.TOOL_DEFS

    # Maximum number of turns
    max_turns = 10
    final_text = ""

    # Iterate for max_turns iterations
    for _ in range(max_turns):

        ### START CODE HERE ###

        # Chat with the LLM via the client and set the correct arguments. Hint: Their names match names of variables already defined.
        # Make sure to let the LLM choose tools automatically. Hint: Look at the docs provided earlier!
        response = CLIENT.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=1,
        ) 

        ### END CODE HERE ###

        # Get the response from the LLM and append to messages
        msg = response.choices[0].message 
        messages.append(msg) 

        # Stop when the assistant returns a final answer (no tool calls)
        if not msg.tool_calls:      
            final_text = msg.content
            print("✅ Final answer:")
            print(final_text)
            break

        # Execute tool calls and append results
        for call in msg.tool_calls:
            tool_name = call.function.name
            args = json.loads(call.function.arguments)
            print(f"🛠️ {tool_name}({args})")

            try:
                tool_func = TOOL_MAPPING[tool_name]
                result = tool_func(**args)
            except Exception as e:
                result = {"error": str(e)}

            ### START CODE HERE ###

            # Keep track of tool use in a new message
            new_msg = {
                # Set role to "tool" (plain string) to signal a tool was used
                "role": "tool",
                # As stated in the markdown when inspecting the ChatCompletionMessage object
                # every call has an attribute called id
                "tool_call_id": call.id,
                # The name of the tool was already defined above, use that variable
                "name": tool_name,
                # Pass the result of calling the tool to json.dumps
                "content": json.dumps(result)
            }

            ### END CODE HERE ###

            # Append to messages
            messages.append(new_msg)

    return final_text

# GRADED FUNCTION: reflection_and_rewrite
def reflection_and_rewrite(report, model: str = DEFAULT_MODEL, temperature: float = 0.3) -> dict:
    """
    Generates a structured reflection AND a revised research report.
    Accepts raw text OR the messages list returned by generate_research_report_with_tools.

    Returns:
        dict with keys:
          - "reflection": structured reflection text
          - "revised_report": improved version of the input report
    """

    # Input can be plain text or a list of messages, this function detects and parses accordingly
    report = research_tools.parse_input(report)

    ### START CODE HERE ###

    # Define the prompt. A multi-line f-string is typically used for this.
    # Remember it should ask the model to output ONLY valid JSON with this structure:
    # {{ "reflection": "<text>", "revised_report": "<text>" }}
    user_prompt = f"""Review and rewrite the following research report.

Return ONLY valid JSON with exactly this structure and no extra text, markdown, or code fences:
{{ "reflection": "<text>", "revised_report": "<text>" }}

reflection: a structured critique covering strengths, limitations, and concrete suggestions.
revised_report: a complete improved version of the report, with citations and full URLs where possible.

Report:
{report}
"""

    # Get a response from the LLM
    response = CLIENT.chat.completions.create(
        # Pass in the model
        model=model,
        messages=[
            # System prompt is already defined
            {"role": "system", "content": "You are an academic reviewer and editor."},
            # Add user prompt
            {"role": "user", "content": user_prompt},
        ],
        # Set the temperature equal to the temperature parameter passed to the function
        temperature=temperature,
        response_format={"type": "json_object"},
    )

    ### END CODE HERE ###

    # Extract output
    llm_output = response.choices[0].message.content.strip()

    # Check if output is valid JSON
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError:
        raise Exception("The output of the LLM was not valid JSON. Adjust your prompt.")

    return {
        "reflection": str(data.get("reflection", "")).strip(),
        "revised_report": str(data.get("revised_report", "")).strip(),
    }

# GRADED FUNCTION: convert_report_to_html

def convert_report_to_html(report, model: str = DEFAULT_MODEL, temperature: float = 0.5) -> str:
    """
    Converts a plaintext research report into a styled HTML page using OpenAI.
    Accepts raw text OR the messages list from the tool-calling step.
    """

    # Input can be plain text or a list of messages, this function detects and parses accordingly
    report = research_tools.parse_input(report)

    # System prompt is already provided
    system_prompt = "You convert plaintext reports into full clean HTML documents."

    ### START CODE HERE ###
    
    # Build the user prompt instructing the model to return ONLY valid HTML
    user_prompt = f"""Convert the following research report into a complete, styled HTML document.

Return ONLY valid HTML. Do not wrap it in markdown, code fences, or commentary.
Use semantic tags (h1/h2/h3, p, ul/ol, a), include inline CSS for readability, and preserve citations/links.

Report:
{report}
"""

    # Call the LLM by interacting with the CLIENT.
    # Remember to set the correct values for the model, messages (system and user prompts) and temperature
    response = CLIENT.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )

    ### END CODE HERE ###

    # Extract the HTML from the assistant message
    html = response.choices[0].message.content.strip()
    if html.startswith("```"):
        html = html.split("\n", 1)[-1]
        if html.endswith("```"):
            html = html[: html.rfind("```")].rstrip()

    return html


def save_and_open_html(html: str, path: str = "research_report.html") -> str:
    """Write the full HTML to disk and open it in the default browser."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open("file://" + os.path.abspath(path))
    return os.path.abspath(path)


if __name__ == "__main__":
    # 1) Research with tools
    prompt_ = "计算机视觉"
    preliminary_report = generate_research_report_with_tools(prompt_)
    print("=== Research Report (preliminary) ===\n")
    print(preliminary_report)

    # 2) Reflection on the report (use the final TEXT to avoid ambiguity)
    reflection_text = reflection_and_rewrite(preliminary_report)   # <-- pass text, not messages
    print("=== Reflection on Report ===\n")
    print(reflection_text['reflection'], "\n")
    print("=== Revised Report ===\n")
    print(reflection_text['revised_report'], "\n")


    # 3) Convert the report to HTML (use the TEXT and correct function name)
    html = convert_report_to_html(reflection_text['revised_report'])

    html_path = save_and_open_html(html)
    print("=== Generated HTML saved ===\n")
    print(html_path)