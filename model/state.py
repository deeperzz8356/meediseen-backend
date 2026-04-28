from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    """
    Shared state across LangGraph nodes.
    Each node reads/writes fields from this state.
    """
    session_id: str
    # -------------------------
    # User Input
    # -------------------------
    uid: str
    request_id: str
    user_symptoms: str
    image_path: str

    # -------------------------
    # AI Analysis
    # -------------------------
    prediction: Optional[str]
    confidence_score: Optional[float]
    confidence: Optional[str]
    explanation: Optional[str]
    bounding_box: Optional[list]

    # -------------------------
    # Medical Knowledge Context
    # -------------------------
    db_context: Optional[str]

    # -------------------------
    # Explainable AI Outputs
    # -------------------------
    heatmap_path: Optional[str]

    # -------------------------
    # Final AI Report
    # -------------------------
    final_report: Optional[str]
    report_path: Optional[str]

    # -------------------------
    # Cloud Storage URLs
    # -------------------------
    image_url: Optional[str]
    report_url: Optional[str]

    # -------------------------
    # Error Handling
    # -------------------------
    error: Optional[str]