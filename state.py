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
    detected_skill: str             # Digcomp skill code, e.g. "power_bi"
    skill_gap: str                  # human-readable description of the gap
    candidate_content: List[dict]   # content chunks retrieved from the vector DB
    filtered_content: List[dict]    # chunks that survived relevance grading
    final_nudge: dict               # delivery payload (the "nudge")
    loop_step: int                  # caps the self-correct loop (avoid infinite loops)
    messages: Annotated[list, add_messages]
