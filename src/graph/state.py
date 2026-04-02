from typing import TypedDict, List, Dict, Any


class ResearchState(TypedDict, total=False):
    question: str
    research_mode: str          # "basic" | "deep"
    plan: str
    sub_questions: List[str]
    time_range: str             # null | "day" | "week" | "month" | "year" (set by planner)
    search_results: List[Dict[str, Any]]
    verification_notes: str
    confidence_score: float
    needs_retry: bool
    reflection_notes: str
    final_answer: str
    citations: List[Dict[str, Any]]
    iteration_count: int
