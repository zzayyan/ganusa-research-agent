from tavily import TavilyClient
from src.config import settings

tavily_client = TavilyClient(api_key=settings.tavily_api_key)


def search_web(
    query: str,
    max_results: int = 5,
    search_depth: str = "advanced",
    include_raw_content: bool = False,
    time_range: str = None,
) -> list:
    kwargs = {
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": include_raw_content,
    }

    # chunks_per_source only available in advanced depth
    if search_depth == "advanced":
        kwargs["chunks_per_source"] = 3

    # Time filter — only set when planner detects time-sensitive query
    if time_range:
        kwargs["time_range"] = time_range

    response = tavily_client.search(**kwargs)
    return response.get("results", [])
