from typing import TypedDict, List, Dict, Any


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
