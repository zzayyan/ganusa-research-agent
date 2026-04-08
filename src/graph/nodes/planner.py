import logging
import time
from datetime import datetime
from src.graph.state import ResearchState
from src.services.llm_router import generate_text
from src.utils.json_parser import extract_json

logger = logging.getLogger(__name__)


# ── Deep mode: minimal planner (plan + time_range only) ─────────────────────
_DEEP_PROMPT = """\
Return ONLY one JSON object. No markdown fences. No explanation.

Schema:
{{
  "plan": "concise research plan (1-2 sentences)",
  "time_range": null
}}

Rules:
- Write a clear plan explaining the research strategy for the question.
- Do NOT generate sub-questions — the ReAct agent will form its own queries iteratively.
- Keep the plan between 1 and 2 sentences.

Time Range Rules (for "time_range" field):
- Set to "day"   if the question asks about events from today or the past 24 hours.
- Set to "week"  if the question asks about events from the past week.
- Set to "month" if the question asks about recent developments (past month).
- Set to "year"  if the question covers the past year.
- Set to null    if the question is about history, timeless concepts, definitions, or doesn't require recent data.

Examples:
- "Apa berita terbaru AI hari ini?" → time_range: "day"
- "Perkembangan AI bulan ini?"      → time_range: "month"
- "Siapa presiden Indonesia?"        → time_range: null
- "Bagaimana cara kerja blockchain?" → time_range: null
- "Gempa bumi terbaru 2025?"         → time_range: "year"

Current Date: {current_date}
User Question:
{question}
"""

# ── Basic mode: full planner with sub-questions ──────────────────────────────
_BASIC_PROMPT = """\
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
- Generate EXACTLY 2 sub-questions. Keep them direct and focused.
- Prefer simple, high-signal queries that quickly answer the user's question.
- Sub-questions must be directly relevant to the user's actual question.
- Make sub-questions concrete and web-searchable (under 400 characters each).
- For factual questions (e.g. "Who is the president of X?"), generate sub-questions that directly search for that fact.
- Do NOT redirect sub-questions to unrelated topics.

Time Range Rules (for "time_range" field):
- Set to "day"   if the question asks about events from today or the past 24 hours.
- Set to "week"  if the question asks about events from the past week.
- Set to "month" if the question asks about recent developments (past month).
- Set to "year"  if the question covers the past year.
- Set to null    if the question is about history, timeless concepts, definitions, or doesn't require recent data.

Examples:
- "Apa berita terbaru AI hari ini?" → time_range: "day"
- "Perkembangan AI bulan ini?"      → time_range: "month"
- "Siapa presiden Indonesia?"        → time_range: null
- "Bagaimana cara kerja blockchain?" → time_range: null
- "Gempa bumi terbaru 2025?"         → time_range: "year"

Current Date: {current_date}
User Question:
{question}
"""


def planner_node(state: ResearchState) -> ResearchState:
    question = state.get("question", "")
    research_mode = state.get("research_mode", "basic")
    model = state.get("model")
    start = time.time()
    logger.info("planner.start", extra={"question": question[:100], "mode": research_mode})
    current_date = datetime.now().strftime("%Y-%m-%d")

    # ── Select prompt & parse strategy per mode ──────────────────────────────
    is_deep = research_mode == "deep"
    prompt_template = _DEEP_PROMPT if is_deep else _BASIC_PROMPT
    prompt = prompt_template.format(current_date=current_date, question=question)

    raw = generate_text(prompt, model_id=model)

    try:
        parsed = extract_json(raw)
        plan = parsed.get("plan", "").strip()
        time_range = parsed.get("time_range")

        if not plan:
            raise ValueError("Empty plan")

        valid_ranges = {"day", "week", "month", "year", None}
        if time_range not in valid_ranges:
            time_range = None

        if is_deep:
            # Deep mode: sub_questions intentionally empty — ReAct will build its own queries
            sub_questions = []
        else:
            sub_questions = parsed.get("sub_questions", [])
            if not isinstance(sub_questions, list) or len(sub_questions) != 2:
                raise ValueError(f"Expected exactly 2 sub_questions, got {len(sub_questions)}")

    except Exception:
        plan = f"Search for reliable and up-to-date information to answer: {question}"
        time_range = None
        if is_deep:
            sub_questions = []
        else:
            sub_questions = [
                question,
                f"Key facts about: {question}",
            ]

    logger.info("planner.done", extra={
        "mode": research_mode,
        "sub_questions_count": len(sub_questions),
        "time_range": time_range,
        "duration_ms": int((time.time() - start) * 1000),
    })

    return {
        **state,
        "plan": plan,
        "sub_questions": sub_questions,
        "time_range": time_range,
    }
