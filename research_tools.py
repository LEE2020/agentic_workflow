# ================================
# Standard library imports
# ================================
import os
import xml.etree.ElementTree as ET

# ================================
# Third-party imports
# ================================
import requests
from dotenv import load_dotenv

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

load_dotenv()

session = requests.Session()
session.headers.update(
    {"User-Agent": "LF-ADP-Agent/1.0 (mailto:your.email@example.com)"}
)


def arxiv_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """Searches arXiv for research papers matching the given query."""
    url = (
        "https://export.arxiv.org/api/query"
        f"?search_query=all:{query}&start=0&max_results={max_results}"
    )

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return [{"error": str(e)}]

    try:
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results = []

        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text.strip()
            authors = [
                author.find("atom:name", ns).text
                for author in entry.findall("atom:author", ns)
            ]
            published = entry.find("atom:published", ns).text[:10]
            url_abstract = entry.find("atom:id", ns).text
            summary = entry.find("atom:summary", ns).text.strip()

            link_pdf = None
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf":
                    link_pdf = link.attrib.get("href")
                    break

            results.append(
                {
                    "title": title,
                    "authors": authors,
                    "published": published,
                    "url": url_abstract,
                    "summary": summary,
                    "link_pdf": link_pdf,
                }
            )

        return results
    except Exception as e:
        return [{"error": f"Parsing failed: {str(e)}"}]


arxiv_tool_def = {
    "type": "function",
    "function": {
        "name": "arxiv_search_tool",
        "description": "Searches for research papers on arXiv by query string.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords for research papers.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


def tavily_search_tool(
    query: str, max_results: int = 5, include_images: bool = False
) -> list[dict]:
    """Perform a search using the Tavily API."""
    if TavilyClient is None:
        raise ImportError("tavily package is not installed. Run: pip install tavily-python")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables.")

    api_base_url = os.getenv("DLAI_TAVILY_BASE_URL")
    client = TavilyClient(api_key=api_key, api_base_url=api_base_url)

    try:
        response = client.search(
            query=query, max_results=max_results, include_images=include_images
        )

        results = []
        for r in response.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                }
            )

        if include_images:
            for img_url in response.get("images", []):
                results.append({"image_url": img_url})

        return results
    except Exception as e:
        return [{"error": str(e)}]


tavily_tool_def = {
    "type": "function",
    "function": {
        "name": "tavily_search_tool",
        "description": "Performs a general-purpose web search using the Tavily API.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords for retrieving information from the web.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 5,
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image results.",
                    "default": False,
                },
            },
            "required": ["query"],
        },
    },
}


def _safe_get(url: str, params: dict | None = None, headers: dict | None = None):
    try:
        response = session.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def _crossref_year(item: dict):
    for key in ("published-print", "published-online", "issued"):
        parts = ((item.get(key) or {}).get("date-parts") or [[None]])[0]
        if parts and parts[0]:
            return parts[0]
    return None


def openalex_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """
    Search OpenAlex for journal articles with citation backing.

    OpenAlex is the open successor to Microsoft Academic Graph and is used by
    universities and funders as a public scholarly record (DOI, venue, citations).
    Results are relevance-ranked journal articles with cited_by_count > 5.
    """
    data, error = _safe_get(
        "https://api.openalex.org/works",
        params={
            "search": query,
            "per_page": max(1, min(max_results, 10)),
            "filter": "type:article,cited_by_count:>5",
            "select": "id,doi,display_name,publication_year,cited_by_count,type,"
            "authorships,primary_location,open_access",
        },
    )
    if error:
        return [{"error": error}]

    results = []
    for work in data.get("results", []):
        venue = (work.get("primary_location") or {}).get("source") or {}
        oa = work.get("open_access") or {}
        authors = [
            (a.get("author") or {}).get("display_name")
            for a in work.get("authorships", [])[:8]
            if (a.get("author") or {}).get("display_name")
        ]
        doi = work.get("doi")
        results.append(
            {
                "source": "OpenAlex",
                "title": work.get("display_name"),
                "authors": authors,
                "year": work.get("publication_year"),
                "venue": venue.get("display_name"),
                "type": work.get("type"),
                "doi": doi,
                "url": doi or work.get("id"),
                "cited_by_count": work.get("cited_by_count", 0),
                "is_oa": oa.get("is_oa", False),
                "oa_url": oa.get("oa_url"),
            }
        )
    return results


openalex_tool_def = {
    "type": "function",
    "function": {
        "name": "openalex_search_tool",
        "description": (
            "Search OpenAlex, an open scholarly graph (successor to Microsoft Academic). "
            "Returns journal articles with DOI, journal/venue, and citation counts "
            "(cited_by_count > 5). Prefer this for strongly backed published literature."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords for scholarly works.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


def crossref_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """
    Search Crossref, the official DOI registration agency for scholarly publishers.

    A Crossref DOI is a publisher-registered record (Elsevier, Springer, Wiley, AAS,
    APS, etc.), with journal title, publisher, and is-referenced-by-count.
    """
    data, error = _safe_get(
        "https://api.crossref.org/works",
        params={
            "query": query,
            "rows": max(1, min(max_results, 10)),
            "filter": "type:journal-article,has-references:true",
            "select": "DOI,title,author,container-title,published-print,published-online,"
            "issued,type,publisher,is-referenced-by-count,URL,ISSN",
        },
    )
    if error:
        return [{"error": error}]

    items = ((data.get("message") or {}).get("items")) or []
    results = []
    for item in items:
        titles = item.get("title") or []
        venues = item.get("container-title") or []
        authors = []
        for author in item.get("author") or []:
            given = author.get("given") or ""
            family = author.get("family") or ""
            name = f"{given} {family}".strip() or author.get("name")
            if name:
                authors.append(name)
            if len(authors) >= 8:
                break
        doi = item.get("DOI")
        results.append(
            {
                "source": "Crossref",
                "title": titles[0] if titles else None,
                "authors": authors,
                "year": _crossref_year(item),
                "venue": venues[0] if venues else None,
                "publisher": item.get("publisher"),
                "type": item.get("type"),
                "doi": f"https://doi.org/{doi}" if doi else None,
                "url": item.get("URL") or (f"https://doi.org/{doi}" if doi else None),
                "is_referenced_by_count": item.get("is-referenced-by-count", 0),
            }
        )
    return results


crossref_tool_def = {
    "type": "function",
    "function": {
        "name": "crossref_search_tool",
        "description": (
            "Search Crossref, the official DOI registration agency. Returns publisher-"
            "registered journal articles with DOI, journal, publisher, and "
            "is-referenced-by-count. Use this as primary evidence that a paper is a "
            "formally published scholarly record."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords for published journal articles.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


def _search_tool_def(name: str, description: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    }


def _crossref_by_prefixes(query: str, prefixes: list[str], max_results: int = 5) -> list[dict]:
    """Search Crossref once per DOI prefix and merge results."""
    per_prefix = max(1, min(max_results, 10))
    merged = []
    seen = set()
    for prefix in prefixes:
        data, error = _safe_get(
            "https://api.crossref.org/works",
            params={
                "query": query,
                "rows": per_prefix,
                "filter": f"prefix:{prefix},type:journal-article",
                "select": "DOI,title,author,container-title,published-print,"
                "published-online,issued,type,publisher,is-referenced-by-count,URL",
            },
        )
        if error or not data:
            continue
        for item in ((data.get("message") or {}).get("items")) or []:
            doi = item.get("DOI")
            if not doi or doi in seen:
                continue
            seen.add(doi)
            titles = item.get("title") or []
            venues = item.get("container-title") or []
            merged.append(
                {
                    "source": "Crossref",
                    "title": titles[0] if titles else None,
                    "year": _crossref_year(item),
                    "venue": venues[0] if venues else None,
                    "publisher": item.get("publisher"),
                    "doi": f"https://doi.org/{doi}",
                    "url": item.get("URL") or f"https://doi.org/{doi}",
                    "is_referenced_by_count": item.get("is-referenced-by-count", 0),
                }
            )
            if len(merged) >= max_results:
                return merged
    return merged


def wikipedia_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """Search English Wikipedia (wikipedia.org)."""
    data, error = _safe_get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max(1, min(max_results, 10)),
            "format": "json",
            "utf8": 1,
        },
    )
    if error:
        return [{"error": error}]

    results = []
    for hit in ((data.get("query") or {}).get("search")) or []:
        title = hit.get("title")
        slug = (title or "").replace(" ", "_")
        results.append(
            {
                "source": "Wikipedia",
                "title": title,
                "url": f"https://en.wikipedia.org/wiki/{slug}",
                "snippet": hit.get("snippet"),
            }
        )
    return results


wikipedia_tool_def = _search_tool_def(
    "wikipedia_search_tool",
    "Search Wikipedia (wikipedia.org) for encyclopedic overviews. "
    "Use for background definitions, not as a substitute for peer-reviewed papers.",
)


def europe_pmc_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """Search Europe PMC / PubMed for journal articles (Nature, Cell, PNAS, eLife, IEEE)."""
    data, error = _safe_get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={
            "query": query,
            "format": "json",
            "pageSize": max(1, min(max_results, 10)),
            "resultType": "lite",
        },
    )
    if error:
        return [{"error": error}]

    results = []
    for item in ((data.get("resultList") or {}).get("result")) or []:
        doi = item.get("doi")
        pmid = item.get("pmid")
        url = (
            f"https://doi.org/{doi}"
            if doi
            else (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None)
        )
        results.append(
            {
                "source": "Europe PMC",
                "title": item.get("title"),
                "authors": item.get("authorString"),
                "year": item.get("pubYear"),
                "venue": item.get("journalTitle"),
                "doi": f"https://doi.org/{doi}" if doi else None,
                "url": url,
                "cited_by_count": item.get("citedByCount", 0),
                "is_oa": item.get("isOpenAccess") == "Y",
            }
        )
    return results


europe_pmc_tool_def = _search_tool_def(
    "europe_pmc_search_tool",
    "Search Europe PMC / PubMed for journal articles. Often returns Nature, Science, "
    "Cell, PNAS, eLife, IEEE and other preferred publishers with DOI URLs.",
)


def ieee_acm_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """Search IEEE (10.1109) and ACM (10.1145) via Crossref → ieee.org / acm.org."""
    return _crossref_by_prefixes(query, ["10.1109", "10.1145"], max_results)


ieee_acm_tool_def = _search_tool_def(
    "ieee_acm_search_tool",
    "Search IEEE Xplore and ACM Digital Library papers via Crossref DOI prefixes "
    "(ieee.org / acm.org). Prefer this for CS conference and journal papers.",
)


def journal_publisher_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """Search Nature, Science, Springer, ScienceDirect, PNAS, eLife via Crossref prefixes."""
    return _crossref_by_prefixes(
        query,
        ["10.1038", "10.1126", "10.1007", "10.1016", "10.1073", "10.7554"],
        max_results,
    )


journal_publisher_tool_def = _search_tool_def(
    "journal_publisher_search_tool",
    "Search Nature, Science, Springer, ScienceDirect/Cell, PNAS, and eLife via "
    "Crossref (nature.com, science.org, springer.com, sciencedirect.com, pnas.org, "
    "elifesciences.org). Use for high-prestige journal articles.",
)


ML_VENUE_SOURCE_IDS = {
    "NeurIPS": "S4306420609",
    "ICML": "S4306419644",
    "JMLR": "S118988714",
}


def ml_venue_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """Search NeurIPS, ICML, JMLR via OpenAlex source IDs."""
    merged = []
    seen = set()
    per = max(1, min(3, max_results))
    for venue, source_id in ML_VENUE_SOURCE_IDS.items():
        data, error = _safe_get(
            "https://api.openalex.org/works",
            params={
                "search": query,
                "per_page": per,
                "filter": f"primary_location.source.id:{source_id}",
                "select": "id,doi,display_name,publication_year,cited_by_count,"
                "primary_location,open_access",
            },
        )
        if error or not data:
            continue
        for work in data.get("results", []):
            key = work.get("doi") or work.get("id")
            if not key or key in seen:
                continue
            seen.add(key)
            loc = (work.get("primary_location") or {}).get("source") or {}
            oa = work.get("open_access") or {}
            doi = work.get("doi")
            merged.append(
                {
                    "source": "OpenAlex",
                    "title": work.get("display_name"),
                    "year": work.get("publication_year"),
                    "venue": loc.get("display_name"),
                    "doi": doi,
                    "url": doi or oa.get("oa_url") or work.get("id"),
                    "cited_by_count": work.get("cited_by_count", 0),
                }
            )
            if len(merged) >= max_results:
                return merged
    return merged


ml_venue_tool_def = _search_tool_def(
    "ml_venue_search_tool",
    "Search NeurIPS, ICML, JMLR, and OpenReview-indexed ML papers (neurips.cc, "
    "icml.cc, jmlr.org, openreview.net) via OpenAlex.",
)


def nasa_ntrs_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """Search NASA Technical Reports Server (ntrs.nasa.gov)."""
    data, error = _safe_get(
        "https://ntrs.nasa.gov/api/citations/search",
        params={"q": query},
    )
    if error:
        return [{"error": error}]

    results = []
    for item in (data.get("results") or [])[: max(1, min(max_results, 10))]:
        cid = item.get("id")
        results.append(
            {
                "source": "NASA NTRS",
                "title": item.get("title"),
                "year": (item.get("published") or item.get("distributionDate") or "")[:4],
                "venue": "NASA Technical Reports Server",
                "url": f"https://ntrs.nasa.gov/citations/{cid}" if cid else None,
                "summary": (item.get("abstract") or "")[:500] or None,
            }
        )
    return results


nasa_ntrs_tool_def = _search_tool_def(
    "nasa_ntrs_search_tool",
    "Search NASA Technical Reports Server (nasa.gov) for technical reports and "
    "scientific publications.",
)


UNIVERSITY_RORS = {
    "MIT": "042nb2s44",
    "Stanford": "00f54p054",
    "Harvard": "00hw9x109",
}


def university_search_tool(query: str, max_results: int = 5) -> list[dict]:
    """Search works affiliated with MIT, Stanford, or Harvard via OpenAlex."""
    rors = "|".join(UNIVERSITY_RORS.values())
    data, error = _safe_get(
        "https://api.openalex.org/works",
        params={
            "search": query,
            "per_page": max(1, min(max_results, 10)),
            "filter": f"institutions.ror:{rors},type:article",
            "select": "id,doi,display_name,publication_year,cited_by_count,"
            "authorships,primary_location,open_access",
        },
    )
    if error:
        return [{"error": error}]

    results = []
    for work in data.get("results", []):
        venue = (work.get("primary_location") or {}).get("source") or {}
        oa = work.get("open_access") or {}
        affiliations = []
        for authorship in work.get("authorships") or []:
            for inst in authorship.get("institutions") or []:
                name = inst.get("display_name")
                if name and name not in affiliations:
                    affiliations.append(name)
        doi = work.get("doi")
        results.append(
            {
                "source": "OpenAlex",
                "title": work.get("display_name"),
                "year": work.get("publication_year"),
                "venue": venue.get("display_name"),
                "institutions": affiliations[:6],
                "doi": doi,
                "url": doi or oa.get("oa_url") or work.get("id"),
                "cited_by_count": work.get("cited_by_count", 0),
            }
        )
    return results


university_tool_def = _search_tool_def(
    "university_search_tool",
    "Search papers affiliated with MIT, Stanford, or Harvard (mit.edu, stanford.edu, "
    "harvard.edu) via OpenAlex institution records.",
)


TOOL_MAPPING = {
    "arxiv_search_tool": arxiv_search_tool,
    "tavily_search_tool": tavily_search_tool,
    "openalex_search_tool": openalex_search_tool,
    "crossref_search_tool": crossref_search_tool,
    "wikipedia_search_tool": wikipedia_search_tool,
    "europe_pmc_search_tool": europe_pmc_search_tool,
    "ieee_acm_search_tool": ieee_acm_search_tool,
    "journal_publisher_search_tool": journal_publisher_search_tool,
    "ml_venue_search_tool": ml_venue_search_tool,
    "nasa_ntrs_search_tool": nasa_ntrs_search_tool,
    "university_search_tool": university_search_tool,
}

TOOL_DEFS = [
    arxiv_tool_def,
    tavily_tool_def,
    openalex_tool_def,
    crossref_tool_def,
    wikipedia_tool_def,
    europe_pmc_tool_def,
    ieee_acm_tool_def,
    journal_publisher_tool_def,
    ml_venue_tool_def,
    nasa_ntrs_tool_def,
    university_tool_def,
]


def parse_input(text_or_messages):
    if isinstance(text_or_messages, list):
        text_report = None
        for m in reversed(text_or_messages):
            role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
            content = (
                m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
            )
            if role == "assistant" and content:
                text_report = content
                break
        if not text_report:
            raise ValueError("No assistant text found in messages.")
    else:
        text_report = str(text_or_messages)

    return text_report
