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
  "final_answer": "## Overview\\n\\nBrief summary paragraph with citations.\\n\\n## Key Findings\\n\\n- Finding one with citation [1]\\n- Finding two with citation [2]\\n- Finding three with citation [3]\\n\\n## Detailed Analysis\\n\\nIn-depth analysis paragraphs with citations.\\n\\n## Limitations\\n\\nShort note on evidence gaps or caveats."
}}

Rules:
- Write a comprehensive research report using the structure above
- Use ONLY the evidence provided below — do NOT hallucinate facts
- Use inline citations like [1], [2], or [1][2] throughout
- **Overview**: 2-3 sentences summarizing the answer to the question
- **Key Findings**: 3-5 bullet points of the most important facts discovered
- **Detailed Analysis**: 2-4 paragraphs providing deeper context and explanation
- **Limitations**: 1-2 sentences noting any gaps or caveats in the evidence
- Every section must contain at least one citation
- Use markdown formatting (bold, bullet points, headers)
- Keep the report between 300-500 words
- Answer the user's question directly and factually based on the evidence
- Factor in the current date when evaluating time-sensitive questions
- Write in a professional, analytical tone
- IMPORTANT: Detect the language of the User Question and write the ENTIRE report in that same language, including all section headings

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

        # Basic sanity check — report should have at least one heading
        if "##" not in final_answer:
            raise ValueError("Missing report structure")

    except Exception:
        final_answer = (
            "## Overview\n\n"
            "The research pipeline was unable to generate a properly structured report "
            "from the retrieved evidence [1].\n\n"
            "## Key Findings\n\n"
            "- The search results contain potentially useful context that may help answer this question [1][2]\n"
            "- Consider rephrasing the question for more targeted results [1]\n\n"
            "## Limitations\n\n"
            "The synthesizer could not produce a structured response from the available evidence."
        )

    return {
        **state,
        "final_answer": final_answer,
        "citations": citations
    }
