import logging
import time
from datetime import datetime
from src.graph.state import ResearchState
from src.services.llm_router import generate_text
from src.utils.json_parser import extract_json

logger = logging.getLogger(__name__)

MAX_REACT_STEPS = 8
MIN_REACT_STEPS = 2


def _build_evidence_summary(evidence: list, max_items: int = 10) -> str:
    """Summarize accumulated evidence into a numbered block, using compaction for older evidence."""
    if not evidence:
        return "No evidence collected yet."
    
    recent = evidence[-6:]  # detail for the 6 most recent items
    older = evidence[:-6]   # summary for the older ones
    
    lines = []
    if older:
        lines.append(f"[Previously gathered {len(older)} sources covering: "
                     f"{', '.join(set(e.get('sub_question', '')[:50] for e in older[:5]))}...]")
    
    for idx, item in enumerate(recent, start=len(older) + 1):
        lines.append(
            f"[{idx}] {item.get('title', 'Untitled')}\n"
            f"  Source: {item.get('url', '')}\n"
            f"  Content: {item.get('content', '')[:400]}\n"
        )
    return "\n".join(lines)


def _build_trace_summary(trace: list) -> str:
    """Summarize past reasoning steps for context in the current prompt."""
    if not trace:
        return "No previous reasoning steps."
    lines = []
    for step in trace:
        lines.append(
            f"Step {step.get('step', '?')}:\n"
            f"  Thought: {step.get('thought', '')}\n"
            f"  Action: {step.get('action', '')} → {step.get('action_input', '')}\n"
            f"  Observation: {step.get('observation', '')}\n"
        )
    return "\n".join(lines)


def reasoner_node(state: ResearchState) -> ResearchState:
    question = state.get("question", "")
    plan = state.get("plan", "")
    model = state.get("model")
    react_step = state.get("react_step", 0)
    react_trace = state.get("react_trace", [])
    accumulated_evidence = state.get("accumulated_evidence", [])
    time_range = state.get("time_range")
    current_date = datetime.now().strftime("%Y-%m-%d")

    start = time.time()
    logger.info("reasoner.start", extra={
        "step": react_step,
        "evidence_count": len(accumulated_evidence),
    })

    evidence_summary = _build_evidence_summary(accumulated_evidence)
    trace_summary = _build_trace_summary(react_trace)
    steps_remaining = MAX_REACT_STEPS - react_step

    prompt = f"""You are a senior research analyst performing a ReAct (Reason + Act) loop.
You are thorough, skeptical, and never settle for shallow answers.
Your goal is to build a comprehensive, multi-angle evidence base before writing a research report.

Current Date: {current_date}
Current Step: {react_step} (you have completed {react_step} search iterations so far)
Steps Remaining: {steps_remaining} (you MUST choose "finish" if steps_remaining <= 0)
Minimum Searches Required: {MIN_REACT_STEPS} (you CANNOT choose "finish" until you have completed at least {MIN_REACT_STEPS} search iterations)

Research Plan:
{plan}

User Question:
{question}

─── Reasoning History ───────────────────────────────
{trace_summary}

─── Accumulated Evidence ────────────────────────────
{evidence_summary}

─────────────────────────────────────────────────────

Instructions:
- You are a CRITICAL analyst. Do NOT be easily satisfied with the evidence you have.
- Before choosing an action, create a coverage assessment:
  * List 3-5 key aspects needed to fully answer this question.
  * For each aspect, rate: COVERED (multiple corroborating sources), PARTIAL (only 1 source or vague info), or MISSING (no evidence).
- PARTIAL is NOT good enough. If ANY aspect is PARTIAL or MISSING, you MUST choose "search".
- Choose "finish" ONLY when ALL of the following are true:
  1. You have completed at least {MIN_REACT_STEPS} search iterations.
  2. ALL aspects in your coverage assessment are COVERED (not PARTIAL, not MISSING).
  3. You have evidence from multiple distinct sources to corroborate key claims.
  4. The evidence is detailed enough to write an 800+ word report with citations.
- If you are unsure whether you have enough, DEFAULT TO SEARCHING MORE. It is always better to over-research than to under-research.
- Each search query must target a DIFFERENT angle or aspect from previous queries. Avoid rephrasing the same query.
- If steps_remaining <= 1, you MUST choose "finish" regardless of coverage.

Return ONLY one JSON object. No markdown fences. No explanation.

Schema:
{{
  "coverage": {{
    "aspect_1": "COVERED",
    "aspect_2": "PARTIAL",
    "aspect_3": "MISSING"
  }},
  "thought": "your critical analysis of current evidence gaps and quality",
  "action": "search" or "finish",
  "action_input": {{
    "query": "specific web search query targeting an uncovered angle (only when action is search)",
    "search_depth": "basic" or "advanced"
  }}
}}

If action is "finish", set action_input to {{}}.
"""

    raw = generate_text(prompt, model_id=model, max_tokens=512, temperature=0.4)

    try:
        parsed = extract_json(raw)
        coverage = parsed.get("coverage", {})
        thought = parsed.get("thought", "").strip()
        action = parsed.get("action", "finish").strip().lower()
        action_input = parsed.get("action_input", {})

        if action not in ("search", "finish"):
            action = "finish"

        # Safety guard: force finish if max steps reached
        if react_step >= MAX_REACT_STEPS:
            action = "finish"
            thought = thought or "Max steps reached. Proceeding to synthesis."
            action_input = {}

        # Criticality guard: force search if minimum steps not yet reached
        if action == "finish" and react_step < MIN_REACT_STEPS:
            action = "search"
            # If LLM tried to finish too early but gave no query, generate a fallback
            if not action_input.get("query"):
                action_input = {
                    "query": f"{question} detailed analysis",
                    "search_depth": "advanced",
                }
            thought = (thought or "") + f" [Overridden: minimum {MIN_REACT_STEPS} search iterations required before finishing.]"

    except Exception:
        coverage = {}
        thought = "Could not parse reasoning. Defaulting to finish."
        action = "finish"
        action_input = {}

    pending_action = {
        "action": action,
        "action_input": action_input,
        "time_range": time_range,  # pass down to executor
    }

    # Record this reasoning step in the trace (observation will be filled by executor)
    new_trace_entry = {
        "step": react_step,
        "coverage": coverage,
        "thought": thought,
        "action": action,
        "action_input": action_input,
        "observation": None,  # filled after executor runs
    }
    updated_trace = react_trace + [new_trace_entry]

    logger.info("reasoner.done", extra={
        "step": react_step,
        "action": action,
        "query": action_input.get("query", ""),
        "duration_ms": int((time.time() - start) * 1000),
    })

    return {
        **state,
        "react_step": react_step,
        "react_trace": updated_trace,
        "pending_action": pending_action,
    }
