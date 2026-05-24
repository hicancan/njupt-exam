from typing import Any, Literal
from pydantic import BaseModel

SemanticMode = Literal[
    "llm",
    "heuristic",
    "heuristic_degraded",
    "guarded_metadata",
    "unprocessed",
]

class SemanticResult(BaseModel):
    semantic_mode: SemanticMode
    field_sources: dict[str, str]
    category: str
    domain: str
    intent: str
    lifecycle: str
    evidence: list[str]
    confidence: float | None
    deadline: str | None
    action_required: bool
    action_type: str | None
    action_summary: str | None
    required_materials: list[str]
    sensitive: bool
    sensitive_types: list[str]
    review_required: bool
    risk_flags: list[str]
    content: str
    summary: str
    attachments: list[dict[str, Any]]
    student_score: float
    importance_score: float
    tags: list[str]
    llm: dict[str, Any]
