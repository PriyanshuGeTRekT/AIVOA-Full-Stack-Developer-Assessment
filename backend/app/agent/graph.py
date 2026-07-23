"""The LangGraph workflow that processes a complaint end to end.

The graph is a linear pipeline. Each step enriches the shared state:

    extract -> completeness -> risk -> reportability -> duplicate
            -> root_cause -> capa -> summary

A linear graph is the honest choice here: the steps genuinely depend on the
extraction that comes first, and keeping it readable matters more than shaving
a few milliseconds with parallel branches. The structure still makes it trivial
to add branching later (for example, skipping CAPA when a complaint is flagged
as a duplicate).
"""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import ComplaintState


def build_graph():
    """Assemble and compile the complaint processing graph."""
    workflow = StateGraph(ComplaintState)

    # Node names are deliberately distinct from the state keys they write to,
    # because LangGraph reserves state keys and rejects a node of the same name.
    workflow.add_node("extract", nodes.extract_fields)
    workflow.add_node("check_completeness", nodes.check_completeness)
    workflow.add_node("classify_risk", nodes.classify_risk)
    workflow.add_node("assess_reportability", nodes.assess_reportability)
    workflow.add_node("detect_duplicate", nodes.detect_duplicate)
    workflow.add_node("recommend_root_cause", nodes.recommend_root_cause)
    workflow.add_node("recommend_capa", nodes.recommend_capa)
    workflow.add_node("summarise", nodes.summarise)

    workflow.add_edge(START, "extract")
    workflow.add_edge("extract", "check_completeness")
    workflow.add_edge("check_completeness", "classify_risk")
    # Reportability reads the assessed risk, so it runs right after triage.
    workflow.add_edge("classify_risk", "assess_reportability")
    workflow.add_edge("assess_reportability", "detect_duplicate")
    workflow.add_edge("detect_duplicate", "recommend_root_cause")
    workflow.add_edge("recommend_root_cause", "recommend_capa")
    workflow.add_edge("recommend_capa", "summarise")
    workflow.add_edge("summarise", END)

    return workflow.compile()


@lru_cache
def get_graph():
    """Compile the graph once and reuse it across requests."""
    return build_graph()


def run_pipeline(raw_text: str, existing: list[dict]) -> ComplaintState:
    """Convenience wrapper the service layer calls to process one complaint."""
    graph = get_graph()
    initial: ComplaintState = {"raw_text": raw_text, "existing": existing, "used_llm": False}
    return graph.invoke(initial)
