"""
The full ABL pipeline graph.

    python -m graph.build_graph

Flow:
    START -> observer -> retrieve -> grade -> [decide]
                                                ├─ transform_query -> retrieve  (self-correct loop)
                                                └─ curate -> deliver -> END
"""

from langgraph.graph import StateGraph, START, END
from state import ABLState
from agents.observer import observer_node
from agents.retriever import retriever_node
from agents.skill_matcher import (
    grade_content_node,
    transform_query_node,
    decide_to_generate,
)
from agents.curator import curator_node
from agents.delivery import delivery_node

workflow = StateGraph(ABLState)

# --- Nodes ---
workflow.add_node("observer", observer_node)
workflow.add_node("retrieve", retriever_node)
workflow.add_node("grade", grade_content_node)
workflow.add_node("transform_query", transform_query_node)
workflow.add_node("curate", curator_node)
workflow.add_node("deliver", delivery_node)

# --- Edges ---
workflow.add_edge(START, "observer")
workflow.add_edge("observer", "retrieve")
workflow.add_edge("retrieve", "grade")

# Self-corrective branch: grade decides whether to retry or move on.
workflow.add_conditional_edges(
    "grade",
    decide_to_generate,
    {"transform_query": "transform_query", "curate": "curate"},
)
workflow.add_edge("transform_query", "retrieve")   # the loop back

workflow.add_edge("curate", "deliver")
workflow.add_edge("deliver", END)

app = workflow.compile()


if __name__ == "__main__":
    import json

    sample_footprint = (
        '{"power_bi": {"level": 2, "knowledge_gap": true}, '
        '"cybersecurity": {"level": 3, "knowledge_gap": false}}'
    )
    result = app.invoke({
        "footprint": sample_footprint,
        "loop_step": 0,
        "messages": [],
    })

    print("\n=== FINAL NUDGE ===")
    print(json.dumps(result["final_nudge"], indent=2))
