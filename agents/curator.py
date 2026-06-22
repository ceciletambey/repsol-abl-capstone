"""
Agent 04 — The Curator.

Assembles learning content for the detected skill gap: Repsol's own course
catalog first (static data below, taken directly from Repsol's Target
Skills Matrix brief), then fresh external web content (articles, videos,
courses, via Tavily search) to fill any gap the catalog doesn't cover.

No connection to Microsoft Copilot Studio or the M365 platform anywhere —
per the project brief, this system replaces those tools, it doesn't call
them. Tavily is a plain public-web search API.

Returns raw, unformatted content. Shaping it for the employee (short text
nudge vs audio script) is the Formatter's job, not this one.
"""

import os

EXTERNAL_RESULTS = 5

# Repsol's real internal course catalog, by detected_skill id, taken from
# the Target Skills Matrix brief. No course exists yet for "digcomp",
# "automation", or "cybersecurity" — those rely entirely on external search.
REPSOL_COURSES = {
    "data": [
        {"title": "Introduction to Data and AI", "level": 1, "duration_hours": 2,
         "text": "Fundamentals of Data Management, Big Data, and AI, and how Repsol applies them to turn data into value."},
        {"title": "Introduction to Data Governance", "level": 1, "duration_hours": 1,
         "text": "The strategic value of data and how to design a governance framework: access, ownership, and quality standards."},
        {"title": "Introduction to Storytelling with Data", "level": 1, "duration_hours": 3,
         "text": "How to analyze, interpret, and communicate data: choosing the right chart and structuring a clear data story."},
        {"title": "Citizen Data Science", "level": 4, "duration_hours": 90,
         "text": "Full data project lifecycle: Power BI, Python, building models, and a real project with business data, plus data governance and responsible AI."},
    ],
    "ia_gen": [
        {"title": "Introduction to IA Gen and Prompting", "level": 1, "duration_hours": 2,
         "text": "How generative AI works in plain language, plus the 6 Ps prompting method for getting strong results from it."},
        {"title": "Copilot Web", "level": 1, "duration_hours": 1,
         "text": "Practical, hands-on use of Copilot Web (Repsol's deployed generative AI tool) with responsible-use guidance."},
    ],
    "power_bi": [
        {"title": "Consuming Power BI", "level": 1, "duration_hours": 2,
         "text": "Core features for report consumers: exploring shared reports, exporting data, managing favorites, subscribing to updates."},
        {"title": "Power BI Basic", "level": 2, "duration_hours": 6,
         "text": "First steps building reports: workspaces, connecting to data sources, transforming data, relationships, intro to DAX, publishing."},
        {"title": "Consuming internal Data Collection", "level": 2, "duration_hours": 2,
         "text": "Connecting to Repsol's published data collections from Power BI Service and Desktop to build reports."},
        {"title": "Power BI Intermediate", "level": 3, "duration_hours": 16,
         "text": "Advanced Power Query, deeper DAX for efficient reporting models, and Power Platform integration."},
        {"title": "Create Data Collections", "level": 3, "duration_hours": 2,
         "text": "Building and publishing data collections to the Repsol Data Portal."},
        {"title": "Power BI Expert", "level": 4, "duration_hours": 12,
         "text": "End-to-end Power BI mastery: data modeling, DAX measures, interactive dashboards, publishing/sharing, Row-Level Security."},
    ],
    "m365": [
        {"title": "Course of Copilot M365", "level": 2, "duration_hours": 10,
         "text": "Repsol's official training on using Copilot within the M365 suite day-to-day."},
    ],
}


def curator_node(state):
    detected_skill = state.get("detected_skill")
    upstream = [
        c for c in state.get("filtered_content", [])
        if not c.get("text", "").startswith("[stub]")
    ]
    internal = _repsol_courses(detected_skill) + upstream

    query = state.get("skill_gap") or detected_skill or ""
    assembled = internal + _search_external(query)

    if not assembled:
        return {
            "filtered_content": [],
            "skill_gap": state["skill_gap"] + " [no relevant content found]",
        }

    return {"filtered_content": assembled}


def _repsol_courses(skill):
    return [
        {**course, "source": "internal", "platform": "repsol"}
        for course in REPSOL_COURSES.get(skill, [])
    ]


def _search_external(query):
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        results = client.search(query=query, max_results=EXTERNAL_RESULTS)
        return [
            {
                "text": r.get("content", ""),
                "source": "external",
                "platform": _platform(r.get("url", "")),
                "url": r.get("url"),
                "title": r.get("title"),
            }
            for r in results.get("results", [])
        ]
    except Exception:
        # No Tavily key / package / network — stub so the pipeline still runs.
        return [{
            "text": f"[stub] external content matching: {query}",
            "source": "external",
            "platform": "web",
        }]


def _platform(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "coursera.org" in url:
        return "coursera"
    return "web"
