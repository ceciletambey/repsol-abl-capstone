"""
Agent 05 - Delivery.

Packages ALL of the curated, formatted content into the final "nudge" - a
structured JSON payload ready to be pushed to Teams/email in a real
deployment. Carries every item (Repsol course, YouTube video, Coursera
course, ...) the Formatter shaped, not just one.
"""

from datetime import datetime


def delivery_node(state):
    items = state.get("filtered_content") or []

    nudge = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "skill": state.get("detected_skill"),
        "gap": state.get("skill_gap"),
        "items": [
            {
                "content": c.get("text", "No content available"),
                "source": c.get("source", "n/a"),
                "format": c.get("format", "text"),
                "url": c.get("url"),
                "title": c.get("title"),
            }
            for c in items
        ] or [{"content": "No content available", "source": "n/a", "format": "text", "url": None, "title": None}],
    }
    return {"final_nudge": nudge}
