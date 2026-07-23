"""LangGraph pipeline for a single complaint.

Flow is mostly linear. If a strong duplicate is found we skip root-cause/CAPA
and jump to the summary.

    extract -> completeness -> risk -> reportability -> duplicate
            -> root_cause -> capa -> summary
            or (duplicate) -> skip_investigation -> summary
"""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import ComplaintState


def _after_duplicate(state: ComplaintState) -> str:
    if state.get("duplicate_of") is not None:
        return "skip_investigation"
    return "recommend_root_cause"


def build_graph():
    workflow = StateGraph(ComplaintState)

    # Node names must not collide with state keys (LangGraph restriction).
    workflow.add_node("extract", nodes.extract_fields)
    workflow.add_node("check_completeness", nodes.check_completeness)
    workflow.add_node("classify_risk", nodes.classify_risk)
    workflow.add_node("assess_reportability", nodes.assess_reportability)
    workflow.add_node("detect_duplicate", nodes.detect_duplicate)
    workflow.add_node("recommend_root_cause", nodes.recommend_root_cause)
    workflow.add_node("recommend_capa", nodes.recommend_capa)
    workflow.add_node("skip_investigation", nodes.skip_investigation_for_duplicate)
    workflow.add_node("summarise", nodes.summarise)

    workflow.add_edge(START, "extract")
    workflow.add_edge("extract", "check_completeness")
    workflow.add_edge("check_completeness", "classify_risk")
    workflow.add_edge("classify_risk", "assess_reportability")
    workflow.add_edge("assess_reportability", "detect_duplicate")
    workflow.add_conditional_edges(
        "detect_duplicate",
        _after_duplicate,
        {
            "recommend_root_cause": "recommend_root_cause",
            "skip_investigation": "skip_investigation",
        },
    )
    workflow.add_edge("recommend_root_cause", "recommend_capa")
    workflow.add_edge("recommend_capa", "summarise")
    workflow.add_edge("skip_investigation", "summarise")
    workflow.add_edge("summarise", END)

    return workflow.compile()


@lru_cache
def get_graph():
    return build_graph()


def run_pipeline(raw_text: str, existing: list[dict]) -> ComplaintState:
    graph = get_graph()
    initial: ComplaintState = {"raw_text": raw_text, "existing": existing, "used_llm": False}
    return graph.invoke(initial)
