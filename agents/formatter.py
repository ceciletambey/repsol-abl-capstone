"""
Agent 04b — The Formatter.

Sits between the Curator (gathers several candidates — Repsol courses,
web articles, videos, whatever else turns up) and Delivery (packages the
final payload). Rather than hardcoding "always take item 0" or "if it's
YouTube do X", it asks the LLM to look at the actual candidates and the
skill gap, reason about which one is genuinely most useful right now and
how it should be presented (read / watch / take a course), then shapes
that one item accordingly.
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


def formatter_node(state):
    candidates = state.get("filtered_content") or []
    if not candidates:
        return {"filtered_content": []}

    delivery_format = state.get("delivery_format", "text")
    decision = _pick_best(candidates, state.get("skill_gap", ""))
    chosen = candidates[decision["index"]]

    return {"filtered_content": [_shape(chosen, decision.get("presentation"), delivery_format)]}


def _pick_best(candidates, skill_gap):
    if len(candidates) == 1:
        return {"index": 0, "presentation": None}

    listing = "\n".join(
        f"{i}. [{c.get('source')}/{c.get('platform', 'web')}] "
        f"{c.get('title') or c.get('text', '')[:80]}"
        for i, c in enumerate(candidates)
    )
    prompt = (
        f"An employee has this skill gap: {skill_gap}\n\n"
        f"Candidate learning resources:\n{listing}\n\n"
        "Pick the single most useful one for closing this specific gap right "
        "now. Prefer Repsol's own internal courses when they genuinely fit — "
        "only pick an external resource if it covers the gap better.\n\n"
        "Reply with ONLY a JSON object, no other text: "
        '{"index": <int>, "presentation": "read"|"watch"|"course"}'
    )
    raw = get_llm().invoke(prompt).content
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        decision = json.loads(match.group(0)) if match else {}
        decision["index"] = max(0, min(int(decision["index"]), len(candidates) - 1))
        return decision
    except (KeyError, ValueError, TypeError):
        return {"index": 0, "presentation": None}


def _shape(chosen, presentation, delivery_format):
    presentation = presentation or _infer_presentation(chosen)

    if presentation == "course":
        title = chosen.get("title", "Repsol course")
        hours = chosen.get("duration_hours")
        duration = f" ({hours}h)" if hours else ""
        chosen["text"] = f"{title}{duration}: {chosen.get('text', '')}"
        chosen["format"] = "take this course"
    elif presentation == "watch":
        title = chosen.get("title") or "this video"
        url = chosen.get("url", "")
        chosen["text"] = f'Watch "{title}" — {url}' if url else title
        chosen["format"] = "watch this video"
    else:
        raw = chosen.get("text", "")
        if raw:
            chosen["text"] = _summarise(raw, delivery_format)
            chosen["format"] = "2-min audio script" if delivery_format == "audio" else "2-min text summary"

    return chosen


def _infer_presentation(chosen):
    if chosen.get("platform") == "repsol":
        return "course"
    if chosen.get("url"):
        return "watch"
    return "read"


def _summarise(raw, delivery_format):
    if delivery_format == "audio":
        prompt = (
            "Rewrite this learning content as a friendly 2-minute spoken audio "
            "script a colleague could listen to before a meeting. Keep it under "
            f"120 words.\n\nCONTENT: {raw}"
        )
    else:
        prompt = (
            "Summarise this learning content into a crisp text nudge of 2-3 "
            f"sentences a busy employee can read in 30 seconds.\n\nCONTENT: {raw}"
        )
    return get_llm().invoke(prompt).content.strip()
