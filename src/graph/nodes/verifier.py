import logging
import time
from datetime import datetime
from src.graph.state import ResearchState
from src.services.bedrock_client import generate_text
from src.utils.json_parser import extract_json

logger = logging.getLogger(__name__)

# Mode-specific configuration
MODE_CONFIG = {
    "basic": {
        "confidence_threshold": 0.55,
        "max_retries": 1,
        "threshold_label": "0.55",
    },
    "deep": {
        "confidence_threshold": 0.70,
        "max_retries": 3,
        "threshold_label": "0.70",
    },
}


def verifier_node(state: ResearchState) -> ResearchState:
    question = state.get("question", "")
    research_mode = state.get("research_mode", "basic")
    start = time.time()
    logger.info("verifier.start", extra={"question": question[:100], "mode": research_mode})

    search_results = state.get("search_results", [])
    iteration_count = state.get("iteration_count", 0)
    current_date = datetime.now().strftime("%Y-%m-%d")

    config = MODE_CONFIG.get(research_mode, MODE_CONFIG["basic"])
    threshold_label = config["threshold_label"]
    max_retries = config["max_retries"]

    valid_results = [
        item for item in search_results
        if item.get("url") and item.get("title") != "Search failed"
    ]

    evidence_lines = []
    for idx, item in enumerate(valid_results[:8], start=1):
        evidence_lines.append(
            f"[{idx}] {item.get('title', '')}\n"
            f"URL: {item.get('url', '')}\n"
            f"Snippet: {item.get('content', '')}\n"
        )

    evidence_block = "\n".join(evidence_lines) if evidence_lines else "No valid evidence retrieved."

    prompt = f"""
You are evaluating whether retrieved evidence sufficiently answers the research question.

Return ONLY JSON:

{{
  "confidence_score": number between 0 and 1,
  "verification_notes": "short explanation",
  "needs_retry": true or false
}}

Rules:
- If evidence directly answers the question, confidence should be at least 0.85
- If evidence provides strong context that logically answers the question, confidence should be between 0.70 and 0.85
- If evidence is somewhat related but incomplete, confidence should be between 0.50 and 0.70
- If evidence is mostly irrelevant, confidence should be below 0.50
- Set needs_retry to true ONLY IF confidence_score is below {threshold_label}

Important:
- Evaluate evidence based on how well it answers the USER's specific question.
- Evidence can still be valid if it provides facts or context that imply the answer.
- Take into account the current date when evaluating questions that depend on time.

Current Date: {current_date}
Research Question:
{question}

Evidence:
{evidence_block}
"""

    raw = generate_text(prompt)

    try:
        parsed = extract_json(raw)
        confidence_score = float(parsed.get("confidence_score", 0.4))
        needs_retry = bool(parsed.get("needs_retry", True))
        verification_notes = parsed.get(
            "verification_notes",
            "Evidence quality check completed."
        )
    except Exception:
        confidence_score = 0.4 if len(valid_results) < 3 else 0.65
        needs_retry = len(valid_results) < 3
        verification_notes = "Fallback verifier used because structured parsing failed."

    # Cap retries based on mode: basic=1, deep=3
    if iteration_count >= max_retries:
        needs_retry = False
        logger.info("verifier.retry_cap_reached", extra={
            "mode": research_mode,
            "iteration_count": iteration_count,
            "max_retries": max_retries,
        })

    logger.info("verifier.done", extra={
        "confidence": confidence_score,
        "needs_retry": needs_retry,
        "mode": research_mode,
        "duration_ms": int((time.time() - start) * 1000)
    })

    return {
        **state,
        "confidence_score": max(0.0, min(1.0, confidence_score)),
        "needs_retry": needs_retry,
        "verification_notes": verification_notes,
    }
