from concurrent.futures import ThreadPoolExecutor, as_completed
from src.graph.state import ResearchState
from src.services.tavily_client import search_web
import logging
import time

logger = logging.getLogger(__name__)

# Search parameters per mode
SEARCH_CONFIG = {
    "basic": {
        "search_depth": "basic",
        "max_results": 3,
        "include_raw_content": False,
        "results_per_query": 3,
    },
    "deep": {
        "search_depth": "advanced",
        "max_results": 6,
        "include_raw_content": True,
        "results_per_query": 4,
    },
}

# Minimum Tavily relevance score to keep a result
# basic: more selective (fewer retries), deep: more inclusive (verifier will filter later)
MIN_SCORE = {
    "basic": 0.5,
    "deep": 0.4,
}


def _search_one(sub_q: str, config: dict) -> tuple:
    """Execute one sub-question search. Returns (sub_q, results, error)."""
    try:
        results = search_web(
            query=sub_q,
            max_results=config["max_results"],
            search_depth=config["search_depth"],
            include_raw_content=config["include_raw_content"],
            time_range=config.get("time_range"),
        )
        return sub_q, results, None
    except Exception as e:
        return sub_q, [], str(e)


def search_node(state: ResearchState) -> ResearchState:
    sub_questions = state.get("sub_questions", [])
    research_mode = state.get("research_mode", "basic")
    time_range = state.get("time_range")  # set by planner if time-sensitive

    config = {
        **SEARCH_CONFIG.get(research_mode, SEARCH_CONFIG["basic"]),
        "time_range": time_range,
    }
    min_score = MIN_SCORE.get(research_mode, 0.5)

    start = time.time()
    logger.info("search.start", extra={
        "sub_questions_count": len(sub_questions),
        "mode": research_mode,
        "search_depth": config["search_depth"],
        "time_range": time_range,
        "min_score": min_score,
    })

    # ── Parallel search execution ─────────────────────────
    max_workers = min(len(sub_questions), 5)
    results_map: dict[str, tuple] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_search_one, sub_q, config): sub_q
            for sub_q in sub_questions
        }
        for future in as_completed(futures):
            sub_q = futures[future]
            try:
                s_q, results, error = future.result()
                results_map[s_q] = (results, error)
            except Exception as e:
                results_map[sub_q] = ([], str(e))

    # ── Aggregate in original order, deduplicate, filter by score ─
    aggregated_results = []
    seen_urls: set = set()

    for sub_q in sub_questions:
        results, error = results_map.get(sub_q, ([], "Future not resolved"))

        if error and not results:
            aggregated_results.append({
                "sub_question": sub_q,
                "title": "Search failed",
                "url": "",
                "content": error,
                "raw_content": "",
                "score": None,
                "status": "failed",
            })
            continue

        # Filter: dedup + min content length + score threshold
        filtered = [
            item for item in results
            if item.get("url")
            and item.get("content")
            and len(item.get("content", "").strip()) > 10
            and item["url"] not in seen_urls
            and (item.get("score") or 0) >= min_score
        ]

        kept = 0
        for item in filtered:
            if kept >= config["results_per_query"]:
                break
            seen_urls.add(item["url"])
            aggregated_results.append({
                "sub_question": sub_q,
                "title": item.get("title", "Untitled"),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "raw_content": item.get("raw_content", ""),
                "score": item.get("score"),
                "status": "success",
            })
            kept += 1

    logger.info("search.done", extra={
        "results_count": len(aggregated_results),
        "unique_urls": len(seen_urls),
        "duration_ms": int((time.time() - start) * 1000),
    })

    return {
        **state,
        "search_results": aggregated_results,
    }
