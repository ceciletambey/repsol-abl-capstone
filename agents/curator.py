"""
Agent 04 — The Curator.

Takes the relevance-filtered content, picks the best item, and chooses a
delivery format (short audio vs. text) based on context. Keeps it simple:
internal content wins ties, first relevant item is selected.
"""


def curator_node(state):
    filtered = state.get("filtered_content", [])

    if not filtered:
        # Nothing survived even after retries — flag it honestly.
        return {
            "filtered_content": [],
            "skill_gap": state["skill_gap"] + " [no relevant content found]",
        }

    # Prefer internal content if present.
    chosen = next((c for c in filtered if c.get("source") == "internal"), filtered[0])

    # Naive format choice: short text by default (a real version would read
    # the user's calendar to decide audio-vs-text).
    chosen["format"] = "2-min text summary"
    return {"filtered_content": [chosen]}
