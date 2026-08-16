import json
import re

import research_tools

# list of preferred domains for Tavily results
TOP_DOMAINS = {
    # General reference / institutions / publishers
    "wikipedia.org", "nature.com", "science.org", "sciencemag.org", "cell.com",
    "mit.edu", "stanford.edu", "harvard.edu", "nasa.gov", "noaa.gov", "europa.eu",

    # CS/AI venues & indexes
    "arxiv.org", "acm.org", "ieee.org", "neurips.cc", "icml.cc", "openreview.net",

    # Other reputable outlets
    "elifesciences.org", "pnas.org", "jmlr.org", "springer.com", "sciencedirect.com",

    # Extra domains (case-specific additions)
    "pbs.org", "nova.edu", "nvcc.edu", "cccco.edu",

    # Well known programming sites
    "codecademy.com", "datacamp.com",

    # Scholarly registries used by local research tools
    "doi.org", "crossref.org", "openalex.org",
}


def print_html(content: str, title: str = "") -> None:
    """Notebook helper stand-in: print a titled block in the terminal."""
    heading = re.sub(r"<[^>]+>", "", title).strip()
    if heading:
        print("\n" + heading)
        print("-" * len(heading))
    print(content)
    print()


def _format_hits(source: str, hits) -> list[str]:
    lines = []
    if not isinstance(hits, list):
        return [f"- ({source}) {hits}"]
    for item in hits:
        if not isinstance(item, dict) or item.get("error"):
            lines.append(f"- ({source}) error: {item}")
            continue
        title = item.get("title") or item.get("display_name") or "Untitled"
        url = item.get("url") or item.get("doi") or item.get("oa_url") or ""
        venue = item.get("venue") or item.get("publisher") or ""
        extra = f" — {venue}" if venue else ""
        if url:
            lines.append(f"- ({source}) {title}{extra}: {url}")
        else:
            lines.append(f"- ({source}) {title}{extra}")
    return lines


def find_references(task: str, max_results: int = 3) -> str:
    """Collect a few papers/overviews with URLs from local research tools."""
    sections = [f"## References for: {task}\n"]

    searches = [
        ("arXiv", research_tools.arxiv_search_tool),
        ("OpenAlex", research_tools.openalex_search_tool),
        ("Crossref", research_tools.crossref_search_tool),
        ("Tavily", research_tools.tavily_search_tool),
    ]
    for name, func in searches:
        try:
            hits = func(query=task, max_results=max_results)
        except TypeError:
            try:
                hits = func(task, max_results)
            except Exception as e:
                hits = [{"error": str(e)}]
        except Exception as e:
            hits = [{"error": str(e)}]
        sections.append(f"### {name}\n")
        sections.extend(_format_hits(name, hits))
        sections.append("")

    return "\n".join(sections)


def evaluate_tavily_results(TOP_DOMAINS, raw: str, min_ratio=0.4):
    """
    Evaluate whether plain-text research results mostly come from preferred domains.

    Args:
        TOP_DOMAINS (set[str]): Set of preferred domains (e.g., 'arxiv.org', 'nature.com').
        raw (str): Plain text or Markdown containing URLs.
        min_ratio (float): Minimum preferred ratio required to pass (e.g., 0.4 = 40%).

    Returns:
        tuple[bool, str]: (flag, markdown_report)
            flag -> True if PASS, False if FAIL
            markdown_report -> Markdown-formatted summary of the evaluation
    """

    url_pattern = re.compile(r"https?://[^\s\]\)>\}]+", flags=re.IGNORECASE)
    urls = url_pattern.findall(raw)

    if not urls:
        return False, """### Evaluation — Tavily Preferred Domains
No URLs detected in the provided text.
Please include links in your research results.
"""

    total = len(urls)
    preferred_count = 0
    details = []

    for url in urls:
        domain = url.split("/")[2]
        preferred = any(td in domain for td in TOP_DOMAINS)
        if preferred:
            preferred_count += 1
        details.append(f"- {url} → {'✅ PREFERRED' if preferred else '❌ NOT PREFERRED'}")

    ratio = preferred_count / total if total > 0 else 0.0
    flag = ratio >= min_ratio

    report = f"""
### Evaluation — Tavily Preferred Domains
- Total results: {total}
- Preferred results: {preferred_count}
- Ratio: {ratio:.2%}
- Threshold: {min_ratio:.0%}
- Status: {"✅ PASS" if flag else "❌ FAIL"}

**Details:**
{chr(10).join(details)}
"""
    return flag, report


if __name__ == "__main__":
    topic = "recent developments in multi-objects tracking"
    min_ratio = 0.5

    print_html(
        json.dumps(sorted(list(TOP_DOMAINS)), indent=2),
        title="<h3>Sample Preferred Domains</h3>",
    )

    research_output = find_references(topic)
    print_html(research_output, title=f"<h3>Research Results on {topic}</h3>")

    flag, eval_md = evaluate_tavily_results(TOP_DOMAINS, research_output, min_ratio=min_ratio)
    print_html("<pre>" + eval_md + "</pre>", title="<h3>Evaluation Summary</h3>")
    print("PASS" if flag else "FAIL")
