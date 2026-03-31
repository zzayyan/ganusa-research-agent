from pydantic import BaseModel
from typing import List, Dict, Any


class ResearchRequest(BaseModel):
    question: str


class ResearchResponse(BaseModel):
    question: str
    plan: str
    sub_questions: List[str]
    search_results: List[Dict[str, Any]]
    verification_notes: str = ""
    confidence_score: float = 0.0
    reflection_notes: str = ""
    final_answer: str
    citations: List[Dict[str, Any]]
