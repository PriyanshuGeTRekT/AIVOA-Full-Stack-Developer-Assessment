"""Shared state dict passed through the LangGraph nodes."""

from typing import TypedDict


class ComplaintState(TypedDict, total=False):
    raw_text: str
    # Lightweight rows for duplicate check: id, reference, product, batch, description.
    existing: list[dict]

    extracted: dict
    completeness: dict
    risk_level: str
    risk_rationale: str
    reportable: bool
    report_type: str
    report_reason: str
    root_cause: str
    capa: str
    summary: str
    duplicate_of: int | None
    duplicate_score: float

    # True if any node got a real LLM response.
    used_llm: bool
