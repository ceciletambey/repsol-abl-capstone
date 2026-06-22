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


def observer_node(state):
    footprint = state["footprint"]
    data = json.loads(footprint)
    pd = data.pop("personal_development", {})

    # 1. A required-skill knowledge gap always wins — applied knowledge not
    # matching self-reported confidence outranks everything else.
    gap_skill = next((skill for skill, v in data.items() if v.get("knowledge_gap")), None)
    reason = "knowledge_gap"

    # 2. No overconfidence case: the biggest deficit against the employee's
    # OWN ROLE requirement (Repsol's Target Skills Matrix) is still a real
    # job requirement, so it outranks personal aspiration.
    if gap_skill is None:
        deficits = {
            s: v["required_level"] - v.get("level", 0)
            for s, v in data.items() if "required_level" in v
        }
        worst = max(deficits, key=deficits.get, default=None)
        if worst and deficits[worst] > 0:
            gap_skill, reason = worst, "role_requirement"

    # 3. No role deficit either: honor the employee's stated PD priority, as
    # long as it maps to a real category and they're not already Expert.
    if gap_skill is None:
        wanted = PD_PRIORITY_TO_SKILL.get(pd.get("priority_skill"))
        if wanted and wanted in data and data[wanted].get("level", 0) < 4:
            gap_skill, reason = wanted, "personal_development"

    # 4. Otherwise fall back to the lowest-scoring required skill.
    if gap_skill is None:
        gap_skill = min(data, key=lambda s: data[s].get("level", 99))
        reason = "lowest_level"

    level = data[gap_skill].get("level")
    if reason == "personal_development":
        skill_gap = f"User asked to prioritise {gap_skill} (level {level}) as a personal development goal."
    elif reason == "role_requirement":
        required = data[gap_skill]["required_level"]
        skill_gap = f"User's role requires {gap_skill} level {required}, but they're at level {level}."
    else:
        skill_gap = f"User shows a gap in {gap_skill} (level {level})."

    return {
        "detected_skill": gap_skill,
        "detected_level": level,
        "is_knowledge_gap": reason == "knowledge_gap",
        "skill_gap": skill_gap,
    }
