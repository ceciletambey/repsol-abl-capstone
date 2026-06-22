"""
Agent 04b — The Formatter.

Sits between the Curator (gathers 2-3 candidates — a Repsol course, a
YouTube video, a Coursera course, whatever turns up) and Delivery
(packages the final payload). Shapes EVERY candidate for its own content
type — a Repsol course becomes a "take this course" pointer, a YouTube
result becomes a "watch this video" pointer, anything else gets a short
text/audio summary — rather than narrowing down to a single "best" pick.
The employee sees all of them.
"""

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
    shaped = [_shape(dict(c), _infer_presentation(c), delivery_format) for c in candidates]
    return {"filtered_content": shaped}


def _shape(chosen, presentation, delivery_format):
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
    platform = chosen.get("platform")
    if platform in ("repsol", "coursera"):
        return "course"
    if platform == "youtube":
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
