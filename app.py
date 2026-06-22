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

from assessment.data import CATEGORIES, PD_QUESTIONS, ROLES, build_footprint, score_questions

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
        for key in ["footprint", "delivery_format", "pipeline_result"]:
            st.session_state.pop(key, None)
        st.rerun()

# ============ STEP 2: RUN PIPELINE ============
if "footprint" in st.session_state and "pipeline_result" not in st.session_state:
    st.header("2 · Run the ABL pipeline")
    if st.button("▶ Run pipeline", type="primary"):
        try:
            from graph.build_graph import app as pipeline

            with st.spinner("Observer → Curate → Format → Deliver → Evaluate..."):
                result = pipeline.invoke({
                    "footprint": json.dumps(st.session_state["footprint"]),
                    "delivery_format": st.session_state["delivery_format"],
                    "loop_step": 0,
                    "messages": [],
                })
            st.session_state["pipeline_result"] = result
            st.rerun()
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.caption("If this is an auth error, set GOOGLE_API_KEY (and TAVILY_API_KEY) "
                       "in Streamlit secrets or your local .env.")

# ============ STEP 3: SHOW THE NUDGE ============
if "pipeline_result" in st.session_state:
    st.header("2 · Run the ABL pipeline")
    nudge = st.session_state["pipeline_result"]["final_nudge"]
    st.success(f"Detected gap: **{nudge['skill']}**")

    st.subheader("📣 Learning Nudge")
    st.markdown(f"**Skill:** {nudge['skill']}  \n"
                f"**Source:** {nudge['source']}  \n"
                f"**Format:** {nudge['format']}")
    if nudge.get("url"):
        st.markdown(f"[Open link]({nudge['url']})")
    st.info(nudge["content"])

    with st.expander("Raw nudge payload (JSON)"):
        st.json(nudge)

    # ============ STEP 4: THE EVALUATOR'S RE-ASSESSMENT ============
    st.header("3 · Re-assessment — after you've gone through the content")
    reassessment = st.session_state["pipeline_result"].get("reassessment", {})
    questions = reassessment.get("questions", [])

    if not questions:
        st.warning("The Evaluator didn't return a usable quiz — check GOOGLE_API_KEY / logs.")
    elif "reassessment_result" not in st.session_state:
        st.write(f"Personalised follow-up for **{reassessment['skill']}**, based on: "
                 f"*{reassessment['based_on']}*")
        with st.form("reassessment_form"):
            answers = []
            for qi, q in enumerate(questions):
                tag = " (Knowledge Check)" if q["type"] == "knowledge_check" else ""
                idx = st.radio(q["text"] + tag, range(len(q["options"])),
                                format_func=lambda i, q=q: q["options"][i],
                                key=f"reassess_{qi}", index=None)
                answers.append(idx)
            done = st.form_submit_button("Submit re-assessment", type="primary")

            if done:
                if any(a is None for a in answers):
                    st.error("Please answer every question.")
                else:
                    st.session_state["reassessment_result"] = score_questions(questions, answers)
                    st.rerun()
    else:
        before = st.session_state["pipeline_result"]["detected_level"]
        after = st.session_state["reassessment_result"]["final"]
        delta = after - before
        c1, c2, c3 = st.columns(3)
        c1.metric("Before", before)
        c2.metric("After", after)
        c3.metric("Progression", f"+{delta}" if delta >= 0 else str(delta))
        if delta > 0:
            st.success("Skill gap reduced — the ABL loop worked. This delta is your evaluation metric.")
        elif st.session_state["reassessment_result"]["knowledge_gap"]:
            st.warning("Still an overconfidence gap on the follow-up knowledge check — needs another pass.")
        else:
            st.warning("No improvement registered yet.")
