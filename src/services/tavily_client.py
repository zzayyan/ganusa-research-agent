from tavily import TavilyClient
from src.config import settings

tavily_client = TavilyClient(api_key=settings.tavily_api_key)


def search_web(query: str, max_results: int = 5):
    response = tavily_client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )
    return response.get("results", [])
