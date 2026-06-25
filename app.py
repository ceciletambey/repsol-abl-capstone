"""
Repsol ABL - Streamlit front-end.

The full connected loop:
  1. Real baseline assessment (assessment/data.py - same questions and
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
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from assessment.data import (CATEGORIES, PD_PRIORITY_IDS, PD_QUESTIONS, ROLES, build_footprint,
                              evaluate_outcome, score_questions)
from agents.observer import detect_gap, detect_all_gaps, PD_PRIORITY_TO_SKILL
from agents.suggester import suggest_next
import storage

st.set_page_config(page_title="Repsol ABL", layout="centered")


def inject_custom_css():
    """All Repsol branding lives here - tweak the hex values in :root to retheme."""
    st.markdown("""
    <style>
    :root {
        --repsol-navy: #0A1A2F;
        --repsol-orange: #FF8200;
        --repsol-orange-hover: #E37300;
        --repsol-cream: #FDF6F0;
        --repsol-teal: #19A7C0;
        --repsol-gradient: linear-gradient(90deg, #FFC629 0%, #FF6B1A 50%, #ED2E5C 100%);
    }

    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Manrope', sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background-color: var(--repsol-cream);
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid rgba(10, 26, 47, 0.08);
    }

    h1, h2, h3 {
        color: var(--repsol-navy) !important;
        font-weight: 800 !important;
        letter-spacing: -0.01em;
    }

    [data-testid="stCaptionContainer"] {
        color: rgba(10, 26, 47, 0.65) !important;
    }

    /* Primary action buttons */
    button[kind="primary"],
    [data-testid^="stBaseButton-primary"] {
        background-color: var(--repsol-orange) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        transition: background-color 0.15s ease-in-out;
    }
    button[kind="primary"]:hover,
    [data-testid^="stBaseButton-primary"]:hover {
        background-color: var(--repsol-orange-hover) !important;
        color: #FFFFFF !important;
    }

    /* Secondary buttons - quiet navy outline so primary actions still pop */
    button[kind="secondary"],
    [data-testid^="stBaseButton-secondary"] {
        border-radius: 8px !important;
        border-color: rgba(10, 26, 47, 0.25) !important;
        color: var(--repsol-navy) !important;
    }

    /* Nudge cards (st.container(border=True)) - flagged via a marker div so the
       rule doesn't accidentally catch every other vertical block on the page */
    div[data-testid="stVerticalBlock"]:has(> div.repsol-card-marker),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(div.repsol-card-marker) {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid rgba(10, 26, 47, 0.06) !important;
        border-left: 4px solid var(--repsol-orange) !important;
        box-shadow: 0 2px 10px rgba(10, 26, 47, 0.08) !important;
        padding: 0.5rem 1rem !important;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        color: var(--repsol-navy) !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--repsol-teal) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
    }

    /* Tables */
    [data-testid="stTable"] table {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Alerts - keep semantic colors, just round the corners for consistency */
    [data-testid="stAlertContainer"] {
        border-radius: 10px !important;
    }

    /* Header band */
    .repsol-header-band {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0 0.25rem 0;
    }
    .repsol-wordmark {
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
        font-size: 2rem;
        color: var(--repsol-navy);
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
    }
    .repsol-dot {
        display: inline-block;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: var(--repsol-gradient);
        margin-right: 10px;
    }
    .repsol-gradient-shape {
        width: 130px;
        height: 42px;
        border-radius: 21px;
        background: var(--repsol-gradient);
        opacity: 0.9;
    }
    .repsol-gradient-bar {
        height: 5px;
        width: 100%;
        border-radius: 4px;
        background: var(--repsol-gradient);
        margin: 0.25rem 0 1.25rem 0;
    }

    /* Teal sub-labels used for skill names in My Progress */
    .repsol-sublabel {
        color: var(--repsol-teal);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.85rem;
        margin-bottom: 0.2rem;
    }
    </style>
    """, unsafe_allow_html=True)


def render_repsol_header():
    """Recreated 'repsol' wordmark - pure CSS/SVG, no external image, so there's
    nothing trademarked to clear before a real demo.

    To swap in an official logo later, replace the st.markdown call below with:
        st.image("assets/repsol_logo.png", width=180)
    """
    st.markdown("""
    <div class="repsol-header-band">
        <div class="repsol-wordmark"><span class="repsol-dot"></span>repsol</div>
        <div class="repsol-gradient-shape"></div>
    </div>
    <div class="repsol-gradient-bar"></div>
    """, unsafe_allow_html=True)


inject_custom_css()
render_repsol_header()

storage.seed_demo_employee()

st.title("Repsol ABL - Agentic Based Learning")
st.caption("Assessment -> Observer -> Curator -> Formatter -> Delivery -> Evaluator's "
           "re-assessment. A proof-of-concept learning loop, not a full platform.")

view = st.sidebar.radio("View", ["Learning loop", "My Progress"])

if view == "My Progress":
    st.header("My Progress")
    employees = storage.list_employees()

    if not employees:
        st.info("No learning cycles recorded yet for anyone. Go to the **Learning loop** "
                "tab, pick or create an employee, and complete a cycle to start tracking "
                "progress here.")
        st.stop()

    active_employee = st.session_state.get("employee")
    default_idx = employees.index(active_employee) if active_employee in employees else 0
    employee = st.selectbox("Employee", employees, index=default_idx)

    history = storage.get_history(employee)
    if not history:
        st.info(f"No learning cycles recorded yet for **{employee}**. Complete an "
                "assessment -> nudge -> re-assessment cycle in the **Learning loop** tab "
                "to start tracking progress here.")
        st.stop()

    st.caption(f"Showing progress for **{employee}** - {len(history)} recorded cycle(s).")

    df = pd.DataFrame(history)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df.sort_values("created_at")

    st.subheader("Level over time, per skill")
    brand_palette = ["#FF8200", "#19A7C0", "#ED2E5C", "#FFC629"]
    for i, skill in enumerate(sorted(df["skill"].unique())):
        skill_df = df[df["skill"] == skill]
        st.markdown(f'<p class="repsol-sublabel">{skill}</p>', unsafe_allow_html=True)
        chart_df = skill_df.set_index("created_at")[["after_level"]].rename(columns={"after_level": "level"})
        st.line_chart(chart_df, color=brand_palette[i % len(brand_palette)])

    st.subheader("Current level vs. required level")
    latest = df.groupby("skill", as_index=False).tail(1)
    summary = pd.DataFrame({
        "Skill": latest["skill"],
        "Current level": latest["after_level"],
        "Required level": latest["required_level"].apply(lambda r: str(int(r)) if pd.notna(r) else "-"),
        "Status": [
            "-" if pd.isna(req) else ("Met" if after >= req else "Gap")
            for after, req in zip(latest["after_level"], latest["required_level"])
        ],
    })
    st.table(summary.set_index("Skill"))
    st.stop()

# The learning loop is a small page machine: "setup" (employee + baseline +
# skill choice) -> "nudges" -> "quiz" -> "results". Each transition is an
# explicit button click that sets st.session_state["page"] and reruns, so
# the employee only ever sees one step at a time, with a way back.
page = st.session_state.setdefault("page", "setup")

existing_employees = storage.list_employees()
current_employee = st.session_state.get("employee")

if page == "setup":
    # ============ STEP 0: WHO ARE YOU? ============
    st.header("0 - Who are you?")

    employee_options = ["- Select -", "+ New employee"] + existing_employees
    default_employee_idx = employee_options.index(current_employee) if current_employee in employee_options else 0
    employee_choice = st.selectbox(
        "Employee name or ID",
        employee_options,
        index=default_employee_idx,
        key="employee_choice",
    )
    selected_employee = None
    if employee_choice == "+ New employee":
        new_employee = st.text_input("Enter new employee name or ID", key="new_employee_input")
        if new_employee.strip():
            selected_employee = new_employee.strip()
    elif employee_choice != "- Select -":
        selected_employee = employee_choice

    # Fall back to the already-confirmed employee if the widget reports a blank
    # selection on this rerun (e.g. right after a brand-new profile gets saved
    # and the dropdown's option list changes) - don't force a re-pick.
    selected_employee = selected_employee or current_employee

    if not selected_employee:
        st.info("Select or create an employee to continue.")
        st.stop()

    # Switching to a different employee on the same page must not leak the
    # previous one's footprint/pipeline/re-assessment state - wipe everything
    # scoped to a single employee before adopting the new one.
    if st.session_state.get("employee") != selected_employee:
        for key in ["footprint", "role", "pipeline_results",
                    "required_skills", "pd_skills",
                    "reassessment_results", "suggestions", "profile_loaded_for"]:
            st.session_state.pop(key, None)
        for key in [k for k in st.session_state if k.startswith("cycle_saved_")]:
            st.session_state.pop(key, None)
        st.session_state["employee"] = selected_employee
        st.session_state["page"] = "setup"

    employee = st.session_state["employee"]
    st.success(f"Working as: **{employee}**")
else:
    employee = current_employee
    if not employee:
        st.session_state["page"] = "setup"
        st.rerun()

# Restore a returning employee's last saved role + footprint once per session,
# so they land on "Baseline assessment on file" instead of retaking the whole
# quiz. "Retake assessment" still works: it clears footprint/role, and this
# check doesn't fire again for the same employee since profile_loaded_for is
# already set, so the blank form is shown as normal.
if st.session_state.get("profile_loaded_for") != employee:
    if "footprint" not in st.session_state:
        profile = storage.get_profile(employee)
        if profile:
            st.session_state["footprint"] = profile["footprint"]
            st.session_state["role"] = profile["role"]
    st.session_state["profile_loaded_for"] = employee

if page == "setup":
    # ============ STEP 1: REAL BASELINE ASSESSMENT ============
    st.header("1 - Baseline assessment")

    if "footprint" not in st.session_state:
        with st.form("assessment_form"):
            role = st.selectbox("What is your role?", list(ROLES.keys()), index=None,
                                 placeholder="Select your role - sets the required level per skill")

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

            submitted = st.form_submit_button("Submit assessment", type="primary")

            if submitted:
                missing = [c["id"] for c in CATEGORIES if any(a is None for a in category_answers[c["id"]])]
                if role is None:
                    st.error("Please select your role.")
                elif missing:
                    st.error(f"Please answer every question - missing: {', '.join(missing)}")
                else:
                    footprint = build_footprint(category_answers, pd_answers, role=role)
                    st.session_state["footprint"] = footprint
                    st.session_state["role"] = role
                    storage.save_profile(employee, role, footprint)
                    st.rerun()
    else:
        footprint = st.session_state["footprint"]
        st.success("Baseline assessment on file - no need to retake it.")
        cols = st.columns(4)
        for i, (skill, v) in enumerate(footprint.items()):
            if skill == "personal_development":
                continue
            with cols[i % 4]:
                label = skill if "required_level" not in v else f"{skill} (role needs {v['required_level']})"
                note = "gap flagged" if v["knowledge_gap"] else None
                if note is None and "required_level" in v and v["level"] < v["required_level"]:
                    note = "below role requirement"
                st.metric(label, v["level"], note)

        # Returning employees skip the baseline quiz, but can still update what
        # they want to develop next - the one part of the assessment that's
        # expected to change between cycles even though their role/level didn't.
        with st.expander("Update personal development priorities"):
            with st.form("pd_update_form"):
                pd_answers = {}
                for q in PD_QUESTIONS:
                    if q["type"] == "multi_select":
                        sel = st.multiselect(q["text"], range(len(q["options"])),
                                              format_func=lambda i, q=q: q["options"][i], key=f"pd_update_{q['id']}")
                        pd_answers[q["id"]] = sel
                    else:
                        idx = st.radio(q["text"], range(len(q["options"])),
                                        format_func=lambda i, q=q: q["options"][i],
                                        key=f"pd_update_{q['id']}", index=None)
                        pd_answers[q["id"]] = idx
                pd_submitted = st.form_submit_button("Save personal development update")

                if pd_submitted:
                    priority_idx = pd_answers.get("pd_priority_skill")
                    if priority_idx is not None:
                        footprint["personal_development"] = {"priority_skill": PD_PRIORITY_IDS[priority_idx]}
                        st.session_state["footprint"] = footprint
                        storage.save_profile(employee, st.session_state.get("role"), footprint)
                        st.success("Personal development priorities updated.")
                        st.rerun()
                    else:
                        st.error("Please select your top development priority.")

        if st.button("Retake full baseline assessment"):
            for key in ["footprint", "role", "pipeline_results",
                        "required_skills", "pd_skills", "reassessment_results", "suggestions"]:
                st.session_state.pop(key, None)
            for key in [k for k in st.session_state if k.startswith("cycle_saved_")]:
                st.session_state.pop(key, None)
            st.rerun()

    # ============ STEP 2: PICK SKILLS TO WORK ON (auto-suggested, overridable, multiple) ============
    all_gaps = []
    chosen_skills = []
    if "footprint" in st.session_state:
        st.header("2 - Choose skills to work on")
        footprint = st.session_state["footprint"]
        skill_data = {k: v for k, v in footprint.items() if k != "personal_development"}
        pd_data = footprint.get("personal_development", {})
        suggested, reason = detect_gap(skill_data, pd_data)
        all_gaps = detect_all_gaps(skill_data)

        # The employee's stated personal-development priority (from the assessment's
        # PD question) should be pre-selected too, alongside the role gaps - not just
        # left for them to notice and add manually. Skip it if they're already maxed
        # out on it, same rule the Observer uses to decide it's worth nudging on.
        pd_priority_skill = PD_PRIORITY_TO_SKILL.get(pd_data.get("priority_skill"))
        if pd_priority_skill and pd_priority_skill in skill_data and skill_data[pd_priority_skill].get("level", 0) >= 4:
            pd_priority_skill = None

        default_skills = list(all_gaps)
        if pd_priority_skill and pd_priority_skill not in default_skills:
            default_skills.append(pd_priority_skill)
        if not default_skills:
            default_skills = [suggested]

        reason_text = {
            "knowledge_gap": "an overconfidence flag on a skill behind your role's requirement",
            "role_requirement": "the biggest gap against your role's actual requirement",
            "personal_development": "your stated personal development priority",
            "lowest_level": "your lowest-scoring category",
        }.get(reason, reason)
        if all_gaps:
            caption = (f"Pre-selected: **{', '.join(all_gaps)}** - every skill currently below your "
                       f"role's required level. Top priority: **{suggested}** ({reason_text}).")
            if pd_priority_skill:
                caption += f" Also pre-selected for personal development: **{pd_priority_skill}**."
            caption += " Add or remove skills below as you like."
            st.caption(caption)
        else:
            st.caption(f"Suggested: **{suggested}** - based on {reason_text}. You can work on more than one at a time.")

        skill_ids = list(skill_data.keys())
        chosen_skills = st.multiselect("Skills to focus on", skill_ids, default=default_skills)

        # ============ STEP 3: RUN PIPELINE (once per chosen skill) ============
        st.header("3 - Run the pipeline")
        if st.button("Run pipeline", type="primary"):
            if not chosen_skills:
                st.error("Pick at least one skill.")
            else:
                try:
                    from graph.build_graph import app as pipeline

                    results = {}
                    with st.spinner("Observer -> Curate -> Format -> Deliver -> Evaluate..."):
                        for skill in chosen_skills:
                            results[skill] = pipeline.invoke({
                                "footprint": json.dumps(st.session_state["footprint"]),
                                "chosen_skill": skill,
                                "loop_step": 0,
                                "messages": [],
                            })
                    st.session_state["pipeline_results"] = results
                    # Remember which chosen skills were an actual role gap vs. an
                    # extra the employee picked for their own development, so the
                    # nudges page can split them into the two sections.
                    st.session_state["required_skills"] = [s for s in chosen_skills if s in all_gaps]
                    st.session_state["pd_skills"] = [s for s in chosen_skills if s not in all_gaps]
                    st.session_state["page"] = "nudges"
                    st.rerun()
                except Exception as e:
                    st.error(f"Pipeline error: {e}")
                    st.caption("If this is an auth error, set GOOGLE_API_KEY (and TAVILY_API_KEY) "
                               "in Streamlit secrets or your local .env.")

# ============ PAGE: NUDGES ============
elif page == "nudges":
    if "pipeline_results" not in st.session_state:
        st.session_state["page"] = "setup"
        st.rerun()

    st.header("Learning nudges")
    if st.button("Back to setup"):
        st.session_state["page"] = "setup"
        st.rerun()

    def render_nudge(skill, result):
        nudge = result["final_nudge"]
        st.subheader(f"Learning Nudge - {skill}")
        st.caption(f"{len(nudge['items'])} source(s) gathered for this skill.")
        for item in nudge["items"]:
            with st.container(border=True):
                st.markdown('<div class="repsol-card-marker"></div>', unsafe_allow_html=True)
                st.markdown(f"**{item.get('title') or item['source']}**  \n"
                            f"Source: {item['source']} - Format: {item['format']}")
                if item.get("url"):
                    st.markdown(f"[Open link]({item['url']})")
                st.write(item["content"])
        with st.expander(f"Raw nudge payload (JSON) - {skill}"):
            st.json(nudge)

    pipeline_results = st.session_state["pipeline_results"]
    required_skills = [s for s in st.session_state.get("required_skills", []) if s in pipeline_results]
    pd_skills = [s for s in st.session_state.get("pd_skills", []) if s in pipeline_results]

    if required_skills:
        st.subheader("Required skills")
        st.caption("Trainings for the skill gaps detected against your role's requirements.")
        for skill in required_skills:
            render_nudge(skill, pipeline_results[skill])

    st.subheader("Personal development skills")
    if pd_skills:
        st.caption("Trainings for the extra skills you chose to work on for your own development.")
        for skill in pd_skills:
            render_nudge(skill, pipeline_results[skill])
    else:
        st.info("No personal development skills were selected for this cycle.")

    if st.button("Next: Re-assessment", type="primary"):
        st.session_state["page"] = "quiz"
        st.rerun()

# ============ PAGE: RE-ASSESSMENT QUIZ ============
elif page == "quiz":
    pipeline_results = st.session_state.get("pipeline_results")
    if not pipeline_results:
        st.session_state["page"] = "setup"
        st.rerun()

    reassessment_results = st.session_state.setdefault("reassessment_results", {})
    unanswered = [s for s in pipeline_results if s not in reassessment_results]

    if not unanswered:
        st.session_state["page"] = "results"
        st.rerun()

    st.header("Re-assessment - after you've gone through the content")
    if st.button("Back to nudges"):
        st.session_state["page"] = "nudges"
        st.rerun()

    for skill in unanswered:
        result = pipeline_results[skill]
        st.markdown(f"### {skill}")
        reassessment = result.get("reassessment", {})
        questions = reassessment.get("questions", [])

        if not questions:
            st.warning(f"The Evaluator didn't return a usable quiz for {skill} - check GOOGLE_API_KEY / logs.")
            reassessment_results[skill] = {"final": result["detected_level"], "knowledge_gap": False, "skipped": True}
            st.divider()
            continue

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
            done = st.form_submit_button(f"Submit re-assessment - {skill}", type="primary")

            if done:
                if any(a is None for a in answers):
                    st.error("Please answer every question.")
                else:
                    reassessment_results[skill] = score_questions(questions, answers)
                    st.rerun()
        st.divider()

# ============ PAGE: RESULTS AND SUGGESTIONS ============
elif page == "results":
    pipeline_results = st.session_state.get("pipeline_results")
    if not pipeline_results:
        st.session_state["page"] = "setup"
        st.rerun()

    st.header("Results and suggestions")
    if st.button("Back to nudges"):
        st.session_state["page"] = "nudges"
        st.rerun()

    reassessment_results = st.session_state.setdefault("reassessment_results", {})
    suggestions = st.session_state.setdefault("suggestions", {})

    for skill, result in pipeline_results.items():
        st.markdown(f"### {skill}")
        outcome = reassessment_results.get(skill)

        if outcome is None:
            st.info("Re-assessment not completed yet for this skill.")
            st.divider()
            continue

        if outcome.get("skipped"):
            st.warning(f"No usable quiz was generated for {skill} - check GOOGLE_API_KEY / logs.")
            st.divider()
            continue

        before = result["detected_level"]
        after = outcome["final"]
        reassessment = result.get("reassessment", {})
        required = reassessment.get("required_level")
        delta = after - before

        c1, c2, c3 = st.columns(3)
        c1.metric("Before", before)
        c2.metric("After", after)
        c3.metric("Progression", f"+{delta}" if delta >= 0 else str(delta))

        verdict, explanation = evaluate_outcome(before, after, required, outcome)
        if verdict == "GOOD":
            st.success(f"GOOD - {explanation}")
        elif verdict == "NEEDS WORK":
            st.warning(f"NEEDS WORK - {explanation}")
        else:
            st.error(f"BAD - {explanation}")

        saved_key = f"cycle_saved_{skill}"
        if not st.session_state.get(saved_key):
            storage.save_cycle(
                employee=st.session_state["employee"],
                role=st.session_state.get("role"),
                skill=skill,
                before_level=before,
                after_level=after,
                required_level=required,
                verdict=verdict,
            )
            st.session_state[saved_key] = True

        if skill not in suggestions:
            seen_titles = {i.get("title") for i in result["final_nudge"]["items"] if i.get("title")}
            with st.spinner("Suggesting what to read next..."):
                suggestions[skill] = suggest_next(skill, after, required, verdict, seen_titles)
        suggestion = suggestions[skill]

        st.markdown("**Suggested next read**")
        with st.container(border=True):
            platform_tag = f" - {suggestion['platform']}" if suggestion.get("platform") else ""
            st.markdown(f"**{suggestion['title']}**{platform_tag}")
            if suggestion.get("url"):
                st.markdown(f"[Open link]({suggestion['url']})")
            st.write(suggestion["text"])
            st.caption(suggestion["rationale"])

        if verdict != "GOOD" and st.button(f"Go through the content again and retake - {skill}"):
            reassessment_results.pop(skill, None)
            suggestions.pop(skill, None)
            st.session_state.pop(saved_key, None)
            st.session_state["page"] = "nudges"
            st.rerun()
        elif verdict == "GOOD" and st.button(f"Retake anyway - {skill}"):
            reassessment_results.pop(skill, None)
            suggestions.pop(skill, None)
            st.session_state.pop(saved_key, None)
            st.session_state["page"] = "quiz"
            st.rerun()

        st.divider()
