import logging
import time
from datetime import datetime
from src.graph.state import ResearchState
from src.services.bedrock_client import generate_text
from src.utils.json_parser import extract_json

logger = logging.getLogger(__name__)


def planner_node(state: ResearchState) -> ResearchState:
    question = state.get("question", "")
    research_mode = state.get("research_mode", "basic")
    start = time.time()
    logger.info("planner.start", extra={"question": question[:100], "mode": research_mode})
    current_date = datetime.now().strftime("%Y-%m-%d")

    if research_mode == "basic":
        sub_q_rule = (
            "- Generate EXACTLY 2 sub-questions. Keep them direct and focused.\n"
            "- Prefer simple, high-signal queries that quickly answer the user's question."
        )
        sub_q_range = (2, 2)
    else:
        sub_q_rule = (
            "- Generate between 3 and 5 sub-questions depending on the complexity of the query.\n"
            "- Cover different angles: definitions, context, causes, examples, and recent developments.\n"
            "- Prefer more sub-questions for complex, multi-faceted topics."
        )
        sub_q_range = (3, 5)

    prompt = f"""
Return ONLY one JSON object. No markdown fences. No explanation.

Schema:
{{
  "plan": "concise research plan",
  "sub_questions": [
    "sub-question 1",
    "sub-question 2"
  ],
  "time_range": null
}}

Rules:
- Write a clear plan explaining HOW the question will be answered.
- Keep the plan between 1 and 2 sentences.
{sub_q_rule}
- Sub-questions must be directly relevant to the user's actual question.
- Make sub-questions concrete and web-searchable (under 400 characters each).
- For factual questions (e.g. "Who is the president of X?"), generate sub-questions that directly search for that fact.
- Do NOT redirect sub-questions to unrelated topics.

Time Range Rules (for "time_range" field):
- Set to "day" if the question asks about events from today or the past 24 hours.
- Set to "week" if the question asks about events from the past week.
- Set to "month" if the question asks about recent developments (past month).
- Set to "year" if the question covers the past year.
- Set to null if the question is about history, timeless concepts, definitions, or doesn't require recent data.

Examples:
- "Apa berita terbaru AI hari ini?" → time_range: "day"
- "Perkembangan AI bulan ini?" → time_range: "month"
- "Siapa presiden Indonesia?" → time_range: null
- "Bagaimana cara kerja blockchain?" → time_range: null
- "Gempa bumi terbaru 2025?" → time_range: "year"

Current Date: {current_date}
User Question:
{question}
"""

    raw = generate_text(prompt)

    try:
        parsed = extract_json(raw)
        plan = parsed.get("plan", "").strip()
        sub_questions = parsed.get("sub_questions", [])
        time_range = parsed.get("time_range")  # None or "day"/"week"/"month"/"year"

        if not plan:
            raise ValueError("Empty plan")
        min_q, max_q = sub_q_range
        if not isinstance(sub_questions, list) or not (min_q <= len(sub_questions) <= max_q):
            raise ValueError(f"Expected {min_q}-{max_q} sub_questions, got {len(sub_questions)}")

        # Validate time_range value
        valid_ranges = {"day", "week", "month", "year", None}
        if time_range not in valid_ranges:
            time_range = None

    except Exception:
        plan = f"Search for reliable and up-to-date information to answer: {question}"
        time_range = None
        if research_mode == "basic":
            sub_questions = [
                question,
                f"Key facts about: {question}",
            ]
        else:
            sub_questions = [
                question,
                f"What are the latest developments related to: {question}",
                f"Context and background of: {question}",
            ]

    logger.info("planner.done", extra={
        "sub_questions_count": len(sub_questions),
        "time_range": time_range,
        "duration_ms": int((time.time() - start) * 1000)
    })

    return {
        **state,
        "plan": plan,
        "sub_questions": sub_questions,
        "time_range": time_range,
    }
