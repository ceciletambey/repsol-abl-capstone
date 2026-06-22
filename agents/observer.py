"""
Agent 01 — The Observer.

Reads the JSON exported by the baseline assessment (the only signal this
project has — no Copilot Studio / M365 footprint access) and identifies
which skill gap to act on.
"""

import json

# Maps the assessment's "priority_skill" PD answer (closed 4-option
# question, see PD_QUESTIONS[4] in the assessment HTML) to one of the
# 7 baseline categories. Keep in sync with that question's option order.
PD_PRIORITY_TO_SKILL = {
    "ai_ml": "ia_gen",
    "data_bi": "power_bi",
    "security": "cybersecurity",
    "collaboration": "m365",
}


def detect_gap(data, pd):
    """Pick which skill to act on. Being ahead of what your role requires is
    never a gap, no matter what else is flagged — so a real deficit against
    the employee's OWN ROLE requirement always comes first. An overconfidence
    flag only jumps the queue among skills that are ALREADY behind (confidently
    wrong about something your job needs is worse than just still learning
    it); it can't override a skill where the requirement is already met."""
    deficits = {
        s: v["required_level"] - v.get("level", 0)
        for s, v in data.items() if "required_level" in v
    }
    behind = {s: d for s, d in deficits.items() if d > 0}

    if behind:
        flagged_behind = {s: d for s, d in behind.items() if data[s].get("knowledge_gap")}
        pool = flagged_behind or behind
        gap_skill = max(pool, key=pool.get)
        return gap_skill, ("knowledge_gap" if gap_skill in flagged_behind else "role_requirement")

    # Nobody's behind their role's requirement. A knowledge_gap on a skill
    # with no role target (e.g. power_bi) is still worth a nudge.
    gap_skill = next((s for s, v in data.items() if v.get("knowledge_gap")), None)
    if gap_skill:
        return gap_skill, "knowledge_gap"

    wanted = PD_PRIORITY_TO_SKILL.get(pd.get("priority_skill"))
    if wanted and wanted in data and data[wanted].get("level", 0) < 4:
        return wanted, "personal_development"

    gap_skill = min(data, key=lambda s: data[s].get("level", 99))
    return gap_skill, "lowest_level"


def observer_node(state):
    footprint = state["footprint"]
    data = json.loads(footprint)
    pd = data.pop("personal_development", {})

    # Let the employee directly choose their focus skill if they want to —
    # the automatic detection below is a default, not a mandate.
    chosen = state.get("chosen_skill")
    if chosen and chosen in data:
        gap_skill, reason = chosen, "user_choice"
    else:
        gap_skill, reason = detect_gap(data, pd)

    level = data[gap_skill].get("level")
    if reason == "user_choice":
        skill_gap = f"User chose to focus on {gap_skill} (level {level})."
    elif reason == "personal_development":
        skill_gap = f"User asked to prioritise {gap_skill} (level {level}) as a personal development goal."
    elif reason == "role_requirement" or (reason == "knowledge_gap" and "required_level" in data[gap_skill]):
        required = data[gap_skill]["required_level"]
        skill_gap = f"User's role requires {gap_skill} level {required}, but they're at level {level}."
    else:
        skill_gap = f"User shows a gap in {gap_skill} (level {level})."

    return {
        "detected_skill": gap_skill,
        "detected_level": level,
        "required_level": data[gap_skill].get("required_level"),
        "is_knowledge_gap": reason == "knowledge_gap",
        "skill_gap": skill_gap,
    }
