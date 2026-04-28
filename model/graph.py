from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import (
    analysis_node,
    heatmap_node,
    reverse_node,
    explanation_node,
    report_node
)


def build_graph():
    """
    Build and compile the MediSeen LangGraph workflow.
    """

    workflow = StateGraph(AgentState)

    # -------------------------
    # Register Nodes
    # -------------------------

    workflow.add_node("vision_analysis", analysis_node)

    workflow.add_node("generate_heatmap", heatmap_node)

    workflow.add_node("retrieve_medical_context", reverse_node)

    workflow.add_node("generate_explanation", explanation_node)

    workflow.add_node("generate_pdf_report", report_node)

    # -------------------------
    # Entry Point
    # -------------------------

    workflow.set_entry_point("vision_analysis")

    # -------------------------
    # Graph Edges (Flow)
    # -------------------------

    workflow.add_edge("vision_analysis", "generate_heatmap")

    workflow.add_edge("generate_heatmap", "retrieve_medical_context")

    workflow.add_edge("retrieve_medical_context", "generate_explanation")

    workflow.add_edge("generate_explanation", "generate_pdf_report")

    workflow.add_edge("generate_pdf_report", END)

    # -------------------------
    # Compile Graph
    # -------------------------

    return workflow.compile()


# Global compiled graph (recommended for FastAPI)
app_graph = build_graph()