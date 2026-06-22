"""
Shared state for the Repsol ABL pipeline.

This is the CONTRACT every agent reads from and writes to.
Nodes never talk to each other directly — they read this shared
document and overwrite specific fields. Agree on this file before
splitting work across the team; changing it mid-build breaks everyone.
"""

from typing import TypedDict, List, Annotated
from langgraph.graph.message import add_messages


class ABLState(TypedDict):
    footprint: str                  # raw trigger (e.g. assessment JSON export)
    chosen_skill: str               # optional: employee's own pick, overrides auto-detection
    detected_skill: str             # Digcomp skill code, e.g. "power_bi"
    detected_level: int             # the employee's baseline level (1-4) for detected_skill
    required_level: int             # the role's required level for detected_skill, if any (None otherwise)
    is_knowledge_gap: bool          # True if this gap is an overconfidence cap, not just low level
    skill_gap: str                  # human-readable description of the gap
    candidate_content: List[dict]   # content chunks retrieved from the vector DB
    filtered_content: List[dict]    # chunks that survived relevance grading
    final_nudge: dict               # delivery payload (the "nudge")
    delivery_format: str            # "text" or "audio" — drives the Formatter
    reassessment: dict              # Evaluator's personalised follow-up quiz
    loop_step: int                  # caps the self-correct loop (avoid infinite loops)
    messages: Annotated[list, add_messages]
