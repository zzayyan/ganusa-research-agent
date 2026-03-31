import json
import re
from datetime import datetime
from src.graph.state import ResearchState
from src.services.bedrock_client import generate_text


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")
    return json.loads(match.group(0))


def planner_node(state: ResearchState) -> ResearchState:
    question = state["question"]
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
Return ONLY one JSON object. No markdown fences. No explanation.

Schema:
{{
  "plan": "concise research plan",
  "sub_questions": [
    "sub-question 1",
    "sub-question 2"
  ]
}}

Rules:
- Write a clear plan explaining HOW the question will be answered.
- Keep the plan between 1 and 2 sentences.
- Generate between 2 and 4 sub-questions depending on the complexity of the query.
- Prefer fewer sub-questions for simple or factual questions.
- Sub-questions must be directly relevant to the user's actual question.
- Make sub-questions concrete and web-searchable.
- For factual questions (e.g. "Who is the president of X?"), generate sub-questions that directly search for that fact.
- Do NOT redirect sub-questions to unrelated topics.

Current Date: {current_date}
User Question:
{question}
"""

    raw = generate_text(prompt)

    try:
        parsed = extract_json(raw)
        plan = parsed.get("plan", "").strip()
        sub_questions = parsed.get("sub_questions", [])

        if not plan:
            raise ValueError("Empty plan")
        if not isinstance(sub_questions, list) or not (2 <= len(sub_questions) <= 4):
            raise ValueError("Invalid sub_questions")

    except Exception:
        plan = (
            f"Search for reliable and up-to-date information to answer: {question}"
        )
        sub_questions = [
            question,
            f"What are the latest facts and context related to: {question}",
        ]

    return {
        **state,
        "plan": plan,
        "sub_questions": sub_questions,
    }
