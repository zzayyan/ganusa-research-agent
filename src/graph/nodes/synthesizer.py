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


def synthesizer_node(state: ResearchState) -> ResearchState:
    question = state["question"]
    search_results = state.get("search_results", [])
    confidence = state.get("confidence_score", 0)
    current_date = datetime.now().strftime("%Y-%m-%d")

    # If evidence quality is too low, avoid hallucinated synthesis
    if confidence < 0.40:
        return {
            **state,
            "final_answer": (
                "The retrieved sources do not provide enough evidence to reliably answer this question. "
                "Please try rephrasing your question or asking something more specific."
            ),
            "citations": []
        }

    valid_results = [
        item for item in search_results
        if item.get("url") and item.get("title") != "Search failed"
    ]

    evidence_lines = []
    citations = []

    for idx, item in enumerate(valid_results[:8], start=1):
        evidence_lines.append(
            f"[{idx}] {item.get('title')}\n"
            f"URL: {item.get('url')}\n"
            f"Snippet: {item.get('content')}\n"
        )

        citations.append({
            "id": idx,
            "title": item.get("title"),
            "url": item.get("url"),
            "sub_question": item.get("sub_question")
        })

    evidence_block = "\n".join(evidence_lines)

    prompt = f"""
Return ONLY one JSON object. No markdown fences. No explanation.

Schema:
{{
  "final_answer": "Direct answer:\\n- sentence with citations\\n- sentence with citations\\n- sentence with citations\\n\\nLimitation: short limitation with citation"
}}

Rules:
- Use ONLY the evidence below
- Use inline citations like [1], [2], or [1][2]
- Write exactly THREE bullet points under 'Direct answer:'
- Each bullet must be a complete sentence
- Every bullet must contain at least one citation
- Do NOT include labels like 'Bullet 1'
- The limitation must NOT be a bullet
- Keep the answer under 180 words
- Answer the user's question directly and factually based on the evidence
- Factor in the current date if the user's question depends on it

Current Date: {current_date}
User Question:
{question}

Evidence:
{evidence_block}
"""

    raw = generate_text(prompt)

    try:
        parsed = extract_json(raw)
        final_answer = parsed.get("final_answer", "").strip()

        if not final_answer:
            raise ValueError("Empty final_answer")

        # Validate bullet structure
        bullets = final_answer.split("\n")
        bullet_count = sum(1 for b in bullets if b.strip().startswith("-"))

        if bullet_count != 3:
            raise ValueError("Invalid bullet count")

    except Exception:
        final_answer = (
            "Direct answer:\n"
            "- The research pipeline was unable to generate a properly structured answer from the retrieved evidence. "
            "Please review the sources below for relevant information [1].\n"
            "- The search results contain potentially useful context that may help answer this question [1][2].\n"
            "- Consider rephrasing the question for more targeted results [1].\n\n"
            "Limitation: The synthesizer could not produce a structured response from the available evidence."
        )

    return {
        **state,
        "final_answer": final_answer,
        "citations": citations
    }
