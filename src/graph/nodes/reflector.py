import logging
import time
from datetime import datetime
from src.graph.state import ResearchState
from src.services.bedrock_client import generate_text
from src.utils.json_parser import extract_json

logger = logging.getLogger(__name__)


def reflector_node(state: ResearchState) -> ResearchState:
    question = state.get("question", "")
    start = time.time()
    logger.info("reflector.start", extra={"question": question[:100]})
    verification_notes = state.get("verification_notes", "")
    iteration_count = state.get("iteration_count", 0)
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
Return ONLY one JSON object. No markdown fences. No explanation.

Schema:
{{
  "reflection_notes": "short reason for retry",
  "sub_questions": [
    "improved sub-question 1",
    "improved sub-question 2"
  ]
}}

Rules:
- Rewrite the sub-questions so they are more directly relevant to the user's original question.
- Generate between 2 and 4 sub-questions depending on the complexity of the query.
- Prefer fewer sub-questions for simple or factual questions.
- Make them concrete, web-searchable, and focused on finding the actual answer.
- Use the verifier notes to understand what was missing and correct the search strategy.

Current Date: {current_date}
User question:
{question}

Verifier notes:
{verification_notes}
"""

    raw = generate_text(prompt)

    try:
        parsed = extract_json(raw)
        reflection_notes = parsed.get("reflection_notes", "Search strategy refined.")
        new_sub_questions = parsed.get("sub_questions", [])

        if not isinstance(new_sub_questions, list) or not (2 <= len(new_sub_questions) <= 4):
            raise ValueError("Invalid sub_questions")
    except Exception:
        reflection_notes = "Retrying with more targeted sub-questions."
        new_sub_questions = [
            question,
            f"What are the latest facts and context related to: {question}",
        ]

    logger.info("reflector.done", extra={
        "sub_questions_count": len(new_sub_questions),
        "duration_ms": int((time.time() - start) * 1000)
    })

    return {
        **state,
        "reflection_notes": reflection_notes,
        "sub_questions": new_sub_questions,
        "iteration_count": iteration_count + 1,
    }
