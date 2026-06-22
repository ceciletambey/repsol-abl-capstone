"""
Agent 05 — Delivery.

Packages the curated content into the final "nudge" — a structured JSON
payload ready to be pushed to Teams/email in a real deployment. Here it
just becomes the final_nudge field in state.
"""

from datetime import datetime


def delivery_node(state):
    chosen = (state.get("filtered_content") or [{}])[0]

    nudge = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "skill": state.get("detected_skill"),
        "gap": state.get("skill_gap"),
        "content": chosen.get("text", "No content available"),
        "source": chosen.get("source", "n/a"),
        "format": chosen.get("format", "text"),
        "url": chosen.get("url"),
        "title": chosen.get("title"),
    }
    return {"final_nudge": nudge}
