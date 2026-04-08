from typing import TypedDict, List, Dict, Any, Optional


class ResearchState(TypedDict, total=False):
    question: str
    research_mode: str
    model: str
    plan: str
    sub_questions: List[str]
    time_range: str
    search_results: List[Dict[str, Any]]
    verification_notes: str
    confidence_score: float
    needs_retry: bool
    reflection_notes: str
    final_answer: str
    citations: List[Dict[str, Any]]
    iteration_count: int

    # ── ReAct loop fields (deep mode only) ──────────────────
    react_step: int                          # current step index (0-indexed)
    react_trace: List[Dict[str, Any]]        # full reasoning trace: [{thought, action, action_input, observation}]
    accumulated_evidence: List[Dict[str, Any]]  # evidence appended across all iterations
    pending_action: Optional[Dict[str, Any]] # action chosen by reasoner: {action, action_input}
