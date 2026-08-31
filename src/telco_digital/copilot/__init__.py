"""AI Copilot is a presentation layer over structured intelligence (Milestone 12)."""

from telco_digital.copilot.service import (
    COPILOT_SET_VERSION,
    CopilotAnswer,
    CopilotService,
    answer_from_decision,
    is_ungrounded,
    render_fallback,
)

__all__ = [
    "COPILOT_SET_VERSION",
    "CopilotAnswer",
    "CopilotService",
    "answer_from_decision",
    "is_ungrounded",
    "render_fallback",
]
