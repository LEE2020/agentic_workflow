import re

from eval_component import TOP_DOMAINS, evaluate_tavily_results, print_html
from example_research import (
    convert_report_to_html,
    generate_research_report_with_tools,
    reflection_and_rewrite,
    save_and_open_html,
)

MIN_RATIO = 0.5
MAX_SEARCH_ATTEMPTS = 3


def _preferred_ratio(raw: str) -> float:
    urls = re.findall(r"https?://[^\s\]\)>\}]+", raw or "", flags=re.IGNORECASE)
    if not urls:
        return 0.0
    preferred = 0
    for url in urls:
        domain = url.split("/")[2]
        if any(td in domain for td in TOP_DOMAINS):
            preferred += 1
    return preferred / len(urls)


def _retry_prompt(topic: str, attempt: int, eval_md: str) -> str:
    domains = ", ".join(sorted(TOP_DOMAINS))
    return (
        f"{topic}\n\n"
        f"Previous attempt {attempt} failed URL quality evaluation "
        f"(preferred-domain ratio <= {MIN_RATIO:.0%}). Search again.\n"
        "Requirements:\n"
        "- Include full URLs for every cited source.\n"
        f"- Prefer these domains: {domains}\n"
        "- Avoid blogs, forums, and unknown sites.\n"
        "- Prioritize arXiv, DOI, IEEE, ACM, Nature, and university pages.\n\n"
        f"Evaluation feedback:\n{eval_md}"
    )


def research_until_url_quality_passes(topic: str, min_ratio: float = MIN_RATIO) -> str:
    """Generate a research report; re-search if preferred URL ratio is <= 50%."""
    prompt = topic
    report = ""
    for attempt in range(1, MAX_SEARCH_ATTEMPTS + 1):
        print(f"\n=== Research attempt {attempt}/{MAX_SEARCH_ATTEMPTS} ===\n")
        report = generate_research_report_with_tools(prompt)
        _, eval_md = evaluate_tavily_results(
            TOP_DOMAINS, report, min_ratio=min_ratio + 1e-9
        )
        ratio = _preferred_ratio(report)
        print_html(eval_md, title=f"<h3>URL Evaluation (attempt {attempt})</h3>")

        if ratio > min_ratio:
            print(f"✅ Preferred-domain ratio {ratio:.2%} > {min_ratio:.0%}, keep this report.")
            return report

        print(f"❌ Preferred-domain ratio {ratio:.2%} <= {min_ratio:.0%}, re-search.")
        if attempt < MAX_SEARCH_ATTEMPTS:
            prompt = _retry_prompt(topic, attempt, eval_md)

    print(f"⚠️ Reached {MAX_SEARCH_ATTEMPTS} attempts, using the last report.")
    return report


if __name__ == "__main__":
    prompt_ = "多目标追踪最新进展（中英文）"
    preliminary_report = research_until_url_quality_passes(prompt_, min_ratio=MIN_RATIO)
    print("=== Research Report (preliminary) ===\n")
    print(preliminary_report)

    reflection_text = reflection_and_rewrite(preliminary_report)
    print("=== Reflection on Report ===\n")
    print(reflection_text["reflection"], "\n")
    print("=== Revised Report ===\n")
    print(reflection_text["revised_report"], "\n")

    html = convert_report_to_html(reflection_text["revised_report"])
    html_path = save_and_open_html(html, path="research_report_with_eval.html")
    print("=== Generated HTML saved ===\n")
    print(html_path)
