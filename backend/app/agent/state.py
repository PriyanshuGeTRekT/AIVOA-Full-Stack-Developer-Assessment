"""Shared state passed between LangGraph nodes.

LangGraph threads a single dict-like state object through the graph. Each node
reads what it needs and returns the keys it wants to update. Using a TypedDict
documents the shape and gives editors useful hints without locking us into a
heavy model.
"""

from typing import TypedDict


class ComplaintState(TypedDict, total=False):
    # Inputs.
    raw_text: str
    # Existing complaints used only for duplicate detection. Each item is a
    # small dict: {id, reference, product_name, batch_number, description}.
    existing: list[dict]

    # Node outputs.
    extracted: dict
    completeness: dict
    risk_level: str
    risk_rationale: str
    root_cause: str
    capa: str
    summary: str
    duplicate_of: int | None
    duplicate_score: float

    # True if at least one node reached the real LLM. Handy for the demo so we
    # can show whether Groq or the heuristic produced the result.
    used_llm: bool
