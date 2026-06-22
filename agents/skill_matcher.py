"""
Agent 02 — The Skill Matcher (Cécile's node).

The star of the pipeline. Takes the detected gap, retrieves candidate
learning content, and GRADES it for relevance. If nothing relevant
survives the filter, it rewrites the query and retries instead of
recommending irrelevant courses — the self-corrective RAG loop.

Loop is capped by state["loop_step"] to avoid infinite retries.
"""

MAX_LOOPS = 3

_llm = None


def get_llm():
    """Lazily build the Gemini client so the module imports without a key set."""
    global _llm
    if _llm is None:
        from langchain_google_genai import ChatGoogleGenerativeAI
        _llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    return _llm


def grade_content_node(state):
    """Grade each candidate chunk: relevant to the skill gap? Keep only 'yes'."""
    gap = state["skill_gap"]
    candidates = state.get("candidate_content", [])
    filtered = []

    for chunk in candidates:
        prompt = (
            "You are grading whether a piece of learning content is relevant "
            f"to this skill gap:\n\nGAP: {gap}\n\nCONTENT: {chunk.get('text', '')}\n\n"
            "Answer with exactly one word: yes or no."
        )
        verdict = get_llm().invoke(prompt).content.strip().lower()
        if verdict.startswith("yes"):
            filtered.append(chunk)

    return {"filtered_content": filtered}


def transform_query_node(state):
    """Rewrite the skill query to get better retrieval on the next pass."""
    gap = state["skill_gap"]
    prompt = (
        f"The search for learning content about '{gap}' returned nothing relevant. "
        "Rewrite it as a clearer, more specific search query for a learning-content "
        "database. Return only the rewritten query, nothing else."
    )
    better = get_llm().invoke(prompt).content.strip()
    return {
        "skill_gap": better,
        "loop_step": state.get("loop_step", 0) + 1,
    }


def decide_to_generate(state):
    """Router: enough relevant content -> curate; nothing left -> retry (capped)."""
    if not state.get("filtered_content"):
        if state.get("loop_step", 0) < MAX_LOOPS:
            return "transform_query"
        return "curate"   # give up retrying, proceed with what we have
    return "curate"
