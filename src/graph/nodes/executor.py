import logging
import time
import hashlib
from src.graph.state import ResearchState
from src.services.tavily_client import search_web

logger = logging.getLogger(__name__)

def _content_fingerprint(text: str, chunk_size: int = 200) -> str:
    """Generate a fingerprint from the first N chars for near-duplicate detection."""
    normalized = " ".join(text.lower().split())[:chunk_size]
    return hashlib.md5(normalized.encode()).hexdigest()


# Search config for ReAct deep mode executor
EXECUTOR_SEARCH_CONFIG = {
    "basic": {
        "search_depth": "basic",
        "max_results": 4,
        "include_raw_content": False,
    },
    "advanced": {
        "search_depth": "advanced",
        "max_results": 6,
        "include_raw_content": True,
    },
}

MIN_SCORE = 0.35  # More permissive — reasoner will decide if evidence is good enough


def executor_node(state: ResearchState) -> ResearchState:
    pending_action = state.get("pending_action", {})
    accumulated_evidence = state.get("accumulated_evidence", [])
    react_trace = state.get("react_trace", [])
    react_step = state.get("react_step", 0)

    action = pending_action.get("action", "finish")
    action_input = pending_action.get("action_input", {})
    time_range = pending_action.get("time_range")

    start = time.time()
    logger.info("executor.start", extra={
        "step": react_step,
        "action": action,
    })

    observation = "No action taken."

    if action == "search":
        query = action_input.get("query", "")
        depth = action_input.get("search_depth", "advanced")
        search_config = EXECUTOR_SEARCH_CONFIG.get(depth, EXECUTOR_SEARCH_CONFIG["advanced"])

        try:
            raw_results = search_web(
                query=query,
                max_results=search_config["max_results"],
                search_depth=search_config["search_depth"],
                include_raw_content=search_config["include_raw_content"],
                time_range=time_range,
            )

            # Deduplicate against already accumulated evidence
            existing_urls = {e.get("url") for e in accumulated_evidence}
            existing_fingerprints = {
                _content_fingerprint(e.get("content", "")) 
                for e in accumulated_evidence
            }

            new_results = []
            for item in raw_results:
                url = item.get("url", "")
                content = item.get("content", "")
                score = item.get("score") or 0
                fp = _content_fingerprint(content)

                if (
                    url
                    and url not in existing_urls
                    and fp not in existing_fingerprints
                    and len(content.strip()) > 10
                    and score >= MIN_SCORE
                ):
                    existing_urls.add(url)
                    existing_fingerprints.add(fp)
                    new_results.append({
                        "sub_question": query,
                        "title": item.get("title", "Untitled"),
                        "url": url,
                        "content": content,
                        "raw_content": item.get("raw_content", ""),
                        "score": score,
                        "status": "success",
                        "react_step": react_step,
                    })

            accumulated_evidence = accumulated_evidence + new_results
            observation = (
                f"Search for '{query}' returned {len(new_results)} new results "
                f"(total evidence: {len(accumulated_evidence)} sources)."
            )

            logger.info("executor.search_done", extra={
                "query": query,
                "new_results": len(new_results),
                "total_evidence": len(accumulated_evidence),
                "duration_ms": int((time.time() - start) * 1000),
            })

        except Exception as e:
            observation = f"Search for '{query}' failed: {str(e)}"
            logger.error("executor.search_failed", extra={"error": str(e), "query": query})

    # Backfill observation into the last trace entry (which was written by reasoner)
    updated_trace = list(react_trace)
    if updated_trace and updated_trace[-1].get("observation") is None:
        last_entry = dict(updated_trace[-1])
        last_entry["observation"] = observation
        if action == "search" and 'new_results' in locals() and isinstance(new_results, list):
             # Only keep title and url to minimize payload size
             last_entry["results"] = [{"title": r["title"], "url": r["url"]} for r in new_results]
        updated_trace[-1] = last_entry

    logger.info("executor.done", extra={
        "step": react_step,
        "duration_ms": int((time.time() - start) * 1000),
    })

    return {
        **state,
        "accumulated_evidence": accumulated_evidence,
        "react_trace": updated_trace,
        "react_step": react_step + 1,  # increment AFTER execution
    }
