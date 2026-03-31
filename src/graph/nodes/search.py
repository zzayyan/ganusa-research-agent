from src.graph.state import ResearchState
from src.services.tavily_client import search_web

def search_node(state: ResearchState) -> ResearchState:
    sub_questions = state.get("sub_questions", [])
    aggregated_results = []

    for sub_q in sub_questions:
        try:
            results = search_web(sub_q, max_results=6)

            filtered = [
                item for item in results 
                if item.get("url") and item.get("content") and len(item.get("content").strip()) > 10
            ]

            for item in filtered[:3]:
                aggregated_results.append({
                    "sub_question": sub_q,
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", None),
                    "status": "success",
                })

        except Exception as e:
            aggregated_results.append({
                "sub_question": sub_q,
                "title": "Search failed",
                "url": "",
                "content": str(e),
                "score": None,
                "status": "failed",
            })

    return {
        **state,
        "search_results": aggregated_results,
    }
