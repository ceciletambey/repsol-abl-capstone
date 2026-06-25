"""
Agent 07 - The Suggester.

Runs once the Evaluator's re-assessment has a verdict. Recommends the ONE
next piece of content worth reading: the same level's gap-closer if the
verdict wasn't GOOD, or the next level up if it was. Checks Repsol's own
catalog first, same as the Curator, then falls back to a fresh web search
for an article - and never re-suggests a title the employee already saw.
"""

import os

from agents.curator import REPSOL_COURSES

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

_llm = None


def get_llm():
    global _llm
    if _llm is None and ChatGoogleGenerativeAI is not None:
        _llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    return _llm


def suggest_next(skill, after_level, required_level, verdict, seen_titles=None):
    """Pick the next thing to read and a one-line reason why."""
    seen_titles = seen_titles or set()
    after_level = after_level or 1
    target_level = min(after_level + 1, 4) if verdict == "GOOD" else after_level

    pick = _next_repsol_course(skill, target_level, seen_titles) or _search_article(skill, target_level, seen_titles)
    pick["rationale"] = _rationale(skill, after_level, required_level, verdict, pick)
    return pick


def _next_repsol_course(skill, target_level, seen_titles):
    courses = [c for c in REPSOL_COURSES.get(skill, []) if c["title"] not in seen_titles]
    if not courses:
        return None
    match = (
        next((c for c in courses if c["level"] == target_level), None)
        or next((c for c in sorted(courses, key=lambda c: c["level"]) if c["level"] > target_level), None)
        or min(courses, key=lambda c: c["level"])
    )
    return {**match, "source": "internal", "platform": "repsol"}


def _search_article(skill, target_level, seen_titles):
    skill_label = skill.replace("_", " ")
    query = f"{skill_label} level {target_level} article"
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        results = client.search(query=query, max_results=5)
        for r in results.get("results", []):
            title = r.get("title")
            if title and title not in seen_titles:
                return {
                    "title": title,
                    "text": r.get("content", ""),
                    "url": r.get("url"),
                    "source": "external",
                    "platform": "web",
                }
    except Exception:
        pass

    return {
        "title": f"Further reading: {skill_label}",
        "text": f"[stub] next article matching: {query}",
        "source": "external",
        "platform": "web",
    }


def _rationale(skill, after_level, required_level, verdict, pick):
    skill_label = skill.replace("_", " ")
    llm = get_llm()
    if llm is None:
        return f"Picked to build on your level {after_level} in {skill_label}."

    prompt = (
        f"An employee just finished a re-assessment on '{skill_label}'. They are now at "
        f"level {after_level}"
        + (f" (their role requires level {required_level})" if required_level else "")
        + f". The verdict on their progress was '{verdict}'. "
        f"In ONE short sentence (under 25 words), tell them why reading "
        f'"{pick["title"]}" next makes sense given that verdict. Be direct and '
        "encouraging, no preamble."
    )
    try:
        return llm.invoke(prompt).content.strip()
    except Exception:
        return f"Picked to build on your level {after_level} in {skill_label}."
