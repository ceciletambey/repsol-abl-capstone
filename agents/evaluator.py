"""
Agent 06 — The Evaluator.

Generates the second assessment: a short follow-up quiz for the ONE skill
the employee worked on, calibrated to their starting level and grounded in
the exact content the Formatter/Delivery just gave them. Not a generic
quiz — it's smart in the sense that it depends entirely on three things
per employee: which skill, what level they started at, and what they were
actually taught. This is the baseline the original assessment promised
growth would be measured against.
"""

import json
import re

from langchain_google_genai import ChatGoogleGenerativeAI

_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    return _llm


def evaluator_node(state):
    skill = state.get("detected_skill", "")
    level = state.get("detected_level")
    is_knowledge_gap = state.get("is_knowledge_gap", False)
    nudge = state.get("final_nudge", {})
    content = nudge.get("content", "")

    questions = _generate_quiz(skill, level, is_knowledge_gap, content)

    return {
        "reassessment": {
            "skill": skill,
            "baseline_level": level,
            "based_on": nudge.get("title") or content[:80],
            "questions": questions,
        }
    }


def _generate_quiz(skill, level, is_knowledge_gap, content):
    if is_knowledge_gap:
        goal = (
            "They previously claimed confidence but failed a knowledge check, so "
            "the goal now is to verify their FOUNDATIONAL understanding is solid "
            "— don't test advanced material they weren't given."
        )
    else:
        goal = (
            f"They started at level {level} (1=Awareness, 2=Basic, "
            "3=Intermediate, 4=Expert), so the goal is to check whether they've "
            "moved up at least one level after this specific content."
        )

    prompt = (
        f"An employee has a skill gap in '{skill}'. {goal}\n\n"
        f"They were just given this exact learning content:\n\n{content}\n\n"
        "Write a follow-up assessment of exactly 2 questions that can ONLY be "
        "answered well by someone who actually engaged with THIS content — not "
        "generic trivia about the topic.\n\n"
        "1. A 'self_report' question about applying this specific skill now, "
        "with 4 options in random order (not sorted by competency) and a "
        "'scores' array mapping each option, in order, to a distinct level "
        "1-4.\n"
        "2. A 'knowledge_check' question with one objectively correct answer "
        "drawn directly from the content above, 4 options, the 0-based "
        "correct index, and a short explanation.\n\n"
        "Reply with ONLY a JSON array of exactly 2 question objects, no other "
        "text, in this exact shape:\n"
        '[{"type": "self_report", "text": "...", '
        '"options": ["...", "...", "...", "..."], "scores": [1, 2, 3, 4]}, '
        '{"type": "knowledge_check", "text": "...", '
        '"options": ["...", "...", "...", "..."], "correct": 0, '
        '"explanation": "..."}]'
    )

    raw = get_llm().invoke(prompt).content
    match = re.search(r"\[.*\]", raw, re.S)
    try:
        questions = json.loads(match.group(0)) if match else []
    except (ValueError, TypeError):
        questions = []
    return questions
