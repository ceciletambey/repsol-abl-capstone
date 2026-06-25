"""
Repsol ABL — Streamlit front-end.

The full connected loop:
  1. Real baseline assessment (assessment/data.py — same questions and
     scoring rules as the assessment HTML)
  2. Run the agentic pipeline -> a curated, formatted learning nudge
  3. The Evaluator's personalised re-assessment for that exact skill,
     scored with the same rule, showing real before/after progression

Run locally:   streamlit run app.py
Deploy:        push to GitHub, then deploy on share.streamlit.io
               (add GOOGLE_API_KEY and TAVILY_API_KEY as secrets there)
"""

import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from assessment.data import CATEGORIES, PD_QUESTIONS, ROLES, build_footprint, evaluate_outcome, score_questions
from agents.observer import detect_gap
from agents.suggester import suggest_next

st.set_page_config(page_title="Repsol ABL", page_icon="🎯", layout="centered")

st.title("Repsol ABL — Agentic Based Learning")
st.caption("Assessment → Observer → Curator → Formatter → Delivery → Evaluator's "
           "re-assessment. A proof-of-concept learning loop, not a full platform.")

# ============ STEP 1: REAL BASELINE ASSESSMENT ============
st.header("1 · Baseline assessment")

if "footprint" not in st.session_state:
    with st.form("assessment_form"):
        role = st.selectbox("What is your role?", list(ROLES.keys()), index=None,
                             placeholder="Select your role — sets the required level per skill")

        category_answers = {}
        for cat in CATEGORIES:
            st.subheader(cat["label"])
            answers = []
            for qi, q in enumerate(cat["questions"]):
                tag = " (Knowledge Check)" if q["type"] == "knowledge_check" else ""
                idx = st.radio(q["text"] + tag, range(len(q["options"])),
                                format_func=lambda i, q=q: q["options"][i],
                                key=f"{cat['id']}_{qi}", index=None)
                answers.append(idx)
            category_answers[cat["id"]] = answers

        st.subheader("Personal Development (optional)")
        pd_answers = {}
        for q in PD_QUESTIONS:
            if q["type"] == "multi_select":
                sel = st.multiselect(q["text"], range(len(q["options"])),
                                      format_func=lambda i, q=q: q["options"][i], key=q["id"])
                pd_answers[q["id"]] = sel
            else:
                idx = st.radio(q["text"], range(len(q["options"])),
                               format_func=lambda i, q=q: q["options"][i],
                               key=q["id"], index=None)
                pd_answers[q["id"]] = idx

        fmt = st.radio("Delivery format for the nudge", ["text", "audio"], horizontal=True)
        submitted = st.form_submit_button("Submit assessment", type="primary")

        if submitted:
            missing = [c["id"] for c in CATEGORIES if any(a is None for a in category_answers[c["id"]])]
            if role is None:
                st.error("Please select your role.")
            elif missing:
                st.error(f"Please answer every question — missing: {', '.join(missing)}")
            else:
                st.session_state["footprint"] = build_footprint(category_answers, pd_answers, role=role)
                st.session_state["delivery_format"] = fmt
                st.rerun()
else:
    footprint = st.session_state["footprint"]
    st.success("Assessment submitted.")
    cols = st.columns(4)
    for i, (skill, v) in enumerate(footprint.items()):
        if skill == "personal_development":
            continue
        with cols[i % 4]:
            label = skill if "required_level" not in v else f"{skill} (role needs {v['required_level']})"
            note = "gap flagged" if v["knowledge_gap"] else None
            if note is None and "required_level" in v and v["level"] < v["required_level"]:
                note = f"below role requirement"
            st.metric(label, v["level"], note)
    if st.button("Retake assessment"):
        for key in ["footprint", "delivery_format", "pipeline_results", "show_reassessment", "reassessment_results", "suggestions"]:
            st.session_state.pop(key, None)
        st.rerun()

# ============ STEP 2: PICK SKILLS TO WORK ON (auto-suggested, overridable, multiple) ============
if "footprint" in st.session_state and "pipeline_results" not in st.session_state:
    st.header("2 · Choose skills to work on")
    footprint = st.session_state["footprint"]
    skill_data = {k: v for k, v in footprint.items() if k != "personal_development"}
    pd_data = footprint.get("personal_development", {})
    suggested, reason = detect_gap(skill_data, pd_data)

    reason_text = {
        "knowledge_gap": "an overconfidence flag on a skill behind your role's requirement",
        "role_requirement": "the biggest gap against your role's actual requirement",
        "personal_development": "your stated personal development priority",
        "lowest_level": "your lowest-scoring category",
    }.get(reason, reason)
    st.caption(f"Suggested: **{suggested}** — based on {reason_text}. You can work on more than one at a time.")

    skill_ids = list(skill_data.keys())
    chosen_skills = st.multiselect("Skills to focus on", skill_ids, default=[suggested])

# ============ STEP 3: RUN PIPELINE (once per chosen skill) ============
if "footprint" in st.session_state and "pipeline_results" not in st.session_state:
    st.header("3 · Run the ABL pipeline")
    if st.button("▶ Run pipeline", type="primary"):
        if not chosen_skills:
            st.error("Pick at least one skill.")
        else:
            try:
                from graph.build_graph import app as pipeline

                results = {}
                with st.spinner("Observer → Curate → Format → Deliver → Evaluate..."):
                    for skill in chosen_skills:
                        results[skill] = pipeline.invoke({
                            "footprint": json.dumps(st.session_state["footprint"]),
                            "chosen_skill": skill,
                            "delivery_format": st.session_state["delivery_format"],
                            "loop_step": 0,
                            "messages": [],
                        })
                st.session_state["pipeline_results"] = results
                st.rerun()
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.caption("If this is an auth error, set GOOGLE_API_KEY (and TAVILY_API_KEY) "
                           "in Streamlit secrets or your local .env.")

# ============ STEP 4: SHOW THE NUDGES (its own page, one block per skill) ============
if "pipeline_results" in st.session_state and not st.session_state.get("show_reassessment"):
    st.header("3 · Run the ABL pipeline")

    for skill, result in st.session_state["pipeline_results"].items():
        nudge = result["final_nudge"]
        st.subheader(f"📣 Learning Nudge — {skill}")
        st.caption(f"{len(nudge['items'])} source(s) gathered for this skill.")
        for item in nudge["items"]:
            with st.container(border=True):
                st.markdown(f"**{item.get('title') or item['source']}**  \n"
                            f"Source: {item['source']} · Format: {item['format']}")
                if item.get("url"):
                    st.markdown(f"[Open link]({item['url']})")
                st.write(item["content"])
        with st.expander(f"Raw nudge payload (JSON) — {skill}"):
            st.json(nudge)

    if st.button("Next → Re-assessment", type="primary"):
        st.session_state["show_reassessment"] = True
        st.rerun()

# ============ STEP 5: THE EVALUATOR'S RE-ASSESSMENT (separate page, retakeable) ============
if st.session_state.get("show_reassessment"):
    st.header("4 · Re-assessment — after you've gone through the content")

    if st.button("← Back to nudges"):
        st.session_state["show_reassessment"] = False
        st.rerun()

    reassessment_results = st.session_state.setdefault("reassessment_results", {})

    for skill, result in st.session_state["pipeline_results"].items():
        st.markdown(f"### {skill}")
        reassessment = result.get("reassessment", {})
        questions = reassessment.get("questions", [])

        if not questions:
            st.warning(f"The Evaluator didn't return a usable quiz for {skill} — check GOOGLE_API_KEY / logs.")
            continue

        if skill not in reassessment_results:
            sources = ", ".join(reassessment.get("based_on", []))
            st.write(f"Personalised follow-up, drawing on: *{sources}*")
            with st.form(f"reassessment_form_{skill}"):
                answers = []
                for qi, q in enumerate(questions):
                    tag = " (Knowledge Check)" if q["type"] == "knowledge_check" else ""
                    idx = st.radio(q["text"] + tag, range(len(q["options"])),
                                    format_func=lambda i, q=q: q["options"][i],
                                    key=f"reassess_{skill}_{qi}", index=None)
                    answers.append(idx)
                done = st.form_submit_button(f"Submit re-assessment — {skill}", type="primary")

                if done:
                    if any(a is None for a in answers):
                        st.error("Please answer every question.")
                    else:
                        reassessment_results[skill] = score_questions(questions, answers)
                        st.rerun()
        else:
            before = result["detected_level"]
            after = reassessment_results[skill]["final"]
            required = reassessment.get("required_level")
            delta = after - before

            c1, c2, c3 = st.columns(3)
            c1.metric("Before", before)
            c2.metric("After", after)
            c3.metric("Progression", f"+{delta}" if delta >= 0 else str(delta))

            verdict, explanation = evaluate_outcome(before, after, required, reassessment_results[skill])
            if verdict == "GOOD":
                st.success(f"✅ GOOD — {explanation}")
            elif verdict == "NEEDS WORK":
                st.warning(f"🟡 NEEDS WORK — {explanation}")
            else:
                st.error(f"❌ BAD — {explanation}")

            suggestions = st.session_state.setdefault("suggestions", {})
            if skill not in suggestions:
                seen_titles = {i.get("title") for i in result["final_nudge"]["items"] if i.get("title")}
                with st.spinner("Suggesting what to read next..."):
                    suggestions[skill] = suggest_next(skill, after, required, verdict, seen_titles)
            suggestion = suggestions[skill]

            st.markdown("**📚 Suggested next read**")
            with st.container(border=True):
                platform_tag = f" · {suggestion['platform']}" if suggestion.get("platform") else ""
                st.markdown(f"**{suggestion['title']}**{platform_tag}")
                if suggestion.get("url"):
                    st.markdown(f"[Open link]({suggestion['url']})")
                st.write(suggestion["text"])
                st.caption(suggestion["rationale"])

            if verdict != "GOOD" and st.button(f"🔁 Go through the content again & retake — {skill}"):
                reassessment_results.pop(skill, None)
                suggestions.pop(skill, None)
                st.session_state["show_reassessment"] = False
                st.rerun()
            elif verdict == "GOOD" and st.button(f"🔁 Retake anyway — {skill}"):
                reassessment_results.pop(skill, None)
                suggestions.pop(skill, None)
                st.rerun()

        st.divider()
