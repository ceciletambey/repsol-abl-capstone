"""
Agent 01 — The Observer.

In production this monitors digital footprints (Teams, calendar, Jira).
For the capstone it reads the JSON exported by the baseline assessment
and identifies which skill gap to act on.
"""

import json


def observer_node(state):
    footprint = state["footprint"]
    data = json.loads(footprint)

    # Prefer a skill flagged with a knowledge gap (overconfidence detected);
    # otherwise fall back to the lowest-level skill.
    gap_skill = next(
        (skill for skill, v in data.items() if v.get("knowledge_gap")),
        min(data, key=lambda s: data[s].get("level", 99)),
    )

    return {
        "detected_skill": gap_skill,
        "skill_gap": f"User shows a gap in {gap_skill} "
                     f"(level {data[gap_skill].get('level')}).",
    }
