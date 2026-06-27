"""
Agent 06 - The Evaluator.

Generates the second assessment: a longer follow-up quiz for the ONE
skill the employee worked on, calibrated to their starting level and
grounded in EVERY piece of content the Curator/Formatter gathered (the
Repsol course, the YouTube video, the Coursera course - not just one of
them). Smart in the sense that it depends entirely on three things per
employee: which skill, what level they started at (and what their role
actually requires), and what they were actually given to learn from. This
is the baseline the original assessment promised growth would be measured
against.
"""

from typing import Literal, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

_llm = None
NUM_QUESTIONS = 4


class QuizQuestion(BaseModel):
    type: Literal["self_report", "knowledge_check"]
    text: str
    options: list[str] = Field(description="Exactly 4 answer options.")
    scores: Optional[list[int]] = Field(
        default=None,
        description="self_report only: each option's level 1-4, same order as options.")
    correct: Optional[int] = Field(
        default=None,
        description="knowledge_check only: 0-based index of the correct option.")
    explanation: Optional[str] = Field(
        default=None,
        description="knowledge_check only: which source the answer came from.")


class Quiz(BaseModel):
    questions: list[QuizQuestion] = Field(description=f"Exactly {NUM_QUESTIONS} questions.")


def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    return _llm


def evaluator_node(state):
    skill = state.get("detected_skill", "")
    level = state.get("detected_level")
    required_level = state.get("required_level")
    is_knowledge_gap = state.get("is_knowledge_gap", False)
    items = state.get("final_nudge", {}).get("items", [])

    content = _combine_sources(items)
    questions = _generate_quiz(skill, level, required_level, is_knowledge_gap, content)

    return {
        "reassessment": {
            "skill": skill,
            "baseline_level": level,
            "required_level": required_level,
            "based_on": [i.get("title") or i.get("content", "")[:60] for i in items],
            "questions": questions,
        }
    }


def _combine_sources(items):
    return "\n\n---\n\n".join(
        f"[Source: {i.get('title') or i.get('source', 'unknown')}]\n{i.get('content', '')}"
        for i in items if i.get("content")
    )


def _generate_quiz(skill, level, required_level, is_knowledge_gap, content):
    if is_knowledge_gap:
        goal = (
            "They previously claimed confidence but failed a knowledge check, so "
            "the goal now is to verify their FOUNDATIONAL understanding is solid "
            "- don't test advanced material they weren't given."
        )
    elif required_level:
        goal = (
            f"They started at level {level} but their ROLE REQUIRES level "
            f"{required_level} (1=Awareness, 2=Basic, 3=Intermediate, 4=Expert) "
            f"for this skill, so the goal is specifically to check whether they "
            f"now perform at level {required_level}, not just whether they "
            f"improved at all."
        )
    else:
        goal = (
            f"They started at level {level} (1=Awareness, 2=Basic, "
            "3=Intermediate, 4=Expert), so the goal is to check whether they've "
            "moved up at least one level after this specific content."
        )

    prompt = (
        f"An employee has a skill gap in '{skill}'. {goal}\n\n"
        f"They were just given ALL of the following learning sources - a "
        f"thorough follow-up should draw on each of them, not just one:\n\n{content}\n\n"
        f"Write a follow-up assessment of exactly {NUM_QUESTIONS} questions "
        "that can ONLY be answered well by someone who actually engaged with "
        "THIS material - not generic trivia about the topic. Spread the "
        "questions across the different sources above where possible.\n\n"
        "2 questions must be type 'self_report': about applying this specific "
        "skill now, 4 options in random order (not sorted by competency), and "
        "a 'scores' array mapping each option, in order, to a distinct level "
        "1-4.\n"
        f"{NUM_QUESTIONS - 2} questions must be type 'knowledge_check': one "
        "objectively correct answer drawn directly from the sources above, 4 "
        "options, the 0-based correct index, and a short explanation that "
        "cites which source it came from."
    )

    try:
        quiz = get_llm().with_structured_output(Quiz).invoke(prompt)
        questions = [q.model_dump(exclude_none=True) for q in quiz.questions]
    except Exception:
        questions = []
    return [q for q in questions if _is_valid_question(q)]


def _is_valid_question(q):
    """Drop anything the LLM returned in the wrong shape - score_questions()
    assumes every self_report has a full scores array and every
    knowledge_check has a valid correct index, with no further checking."""
    if not isinstance(q, dict) or not isinstance(q.get("options"), list) or not q["options"]:
        return False
    if q.get("type") == "self_report":
        return isinstance(q.get("scores"), list) and len(q["scores"]) == len(q["options"])
    if q.get("type") == "knowledge_check":
        return isinstance(q.get("correct"), int) and 0 <= q["correct"] < len(q["options"])
    return False
