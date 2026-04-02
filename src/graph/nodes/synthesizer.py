import logging
import time
from datetime import datetime
from src.graph.state import ResearchState
from src.services.bedrock_client import generate_text
from src.utils.json_parser import extract_json

logger = logging.getLogger(__name__)


def synthesizer_node(state: ResearchState) -> ResearchState:
    question = state.get("question", "")
    research_mode = state.get("research_mode", "basic")
    start = time.time()
    logger.info("synthesizer.start", extra={"question": question[:100], "mode": research_mode})
    search_results = state.get("search_results", [])
    confidence = state.get("confidence_score", 0)
    current_date = datetime.now().strftime("%Y-%m-%d")

    # If evidence quality is too low, avoid hallucinated synthesis
    if confidence < 0.40:
        logger.info("synthesizer.skip", extra={"reason": "low_confidence"})
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

    # Deep mode gets more sources to compensate for shorter snippets
    evidence_cap = 8 if research_mode == "basic" else 12

    for idx, item in enumerate(valid_results[:evidence_cap], start=1):
        evidence_lines.append(
            f"[{idx}] {item.get('title')}\n"
            f"URL: {item.get('url')}\n"
            f"Snippet: {item.get('content', '')}\n"
        )

        citations.append({
            "id": idx,
            "title": item.get("title"),
            "url": item.get("url"),
            "sub_question": item.get("sub_question")
        })

    evidence_block = "\n".join(evidence_lines)

    # Mode-specific prompt rules
    if research_mode == "basic":
        mode_rules = (
            "- **Overview**: 1-2 sentences — answer the question directly\n"
            "- **Key Findings**: 2-3 bullet points of the most critical facts\n"
            "- **Detailed Analysis**: 1-2 paragraphs with key context. Be concise.\n"
            "- **Limitations**: 1 sentence on evidence gaps\n"
            "- Keep the report between 150-300 words total"
        )
        schema_example = (
            '  "final_answer": "## Overview\\n\\nBrief summary paragraph with citations.'
            '\\n\\n## Key Findings\\n\\n- Finding one with citation [1]\\n- Finding two with citation [2]'
            '\\n\\n## Detailed Analysis\\n\\nIn-depth analysis paragraphs with citations.'
            '\\n\\n## Limitations\\n\\nShort note on evidence gaps or caveats."'
        )
        structure_instruction = "- Write a research report using the EXACT section structure shown in the schema above"
    else:
        mode_rules = (
            "- Design your OWN section headings (## level) that best fit the topic and evidence\n"
            "- You MUST have at least 4 sections and at most 7 sections\n"
            "- The FIRST section must be an introductory overview answering the user's question\n"
            "- The LAST section must address limitations, caveats, or areas needing further research\n"
            "- Middle sections should cover distinct aspects of the topic (e.g., causes, impacts, comparisons, timeline, technical details, stakeholders, etc.)\n"
            "- Use a MIX of paragraphs and bullet points — do not rely on only one format\n"
            "- Each section should have 2-4 paragraphs or equivalent content\n"
            "- Keep the report between 800-1000 words total if the topic is complex, otherwise keep it between 500-800 words total"
        )
        schema_example = (
            '  "final_answer": "## [Your Intro Heading]\\n\\nSummary paragraph answering the question [1].'
            '\\n\\n## [Topic-Specific Heading]\\n\\nDetailed analysis with citations [2][3].'
            '\\n\\n## [Another Relevant Heading]\\n\\n- Key point one [1]\\n- Key point two [4]'
            '\\n\\n## [Limitations / Further Research]\\n\\nCaveats and gaps [2]."'
        )
        structure_instruction = "- Design your own report structure — choose section headings that naturally fit the topic"

    prompt = f"""
Return ONLY one JSON object. No markdown fences. No explanation.

Schema:
{{
{schema_example}
}}

Rules:
- OVERRIDE EXCEPTION: If the User Question explicitly requests a specific format, structure, outline, or length (e.g., "berikan 3 poin utama", "buat tabel", "format dalam pro kontra", dll), you MUST prioritize and strictly follow the user's requested structure instead of the default structure/rules below.
{structure_instruction}
- Use ONLY the evidence provided below — do NOT hallucinate facts
- Use inline citations like [1], [2], or [1][2] throughout
{mode_rules}
- Every section must contain at least one citation
- Use markdown formatting (bold, bullet points, headers)
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

    # Token budget & temperature per mode
    max_tokens = 512 if research_mode == "basic" else 2048
    temperature = 0.5 if research_mode == "basic" else 0.7

    raw = generate_text(prompt, max_tokens=max_tokens, temperature=temperature)

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

    logger.info("synthesizer.done", extra={
        "citations_used": len(citations),
        "duration_ms": int((time.time() - start) * 1000)
    })

    return {
        **state,
        "final_answer": final_answer,
        "citations": citations
    }
