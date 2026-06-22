# Repsol ABL — Agentic Based Learning

A LangGraph + Gemini + Chroma pipeline that turns a digital-skills gap into a
targeted learning "nudge." Built for the IE × Repsol capstone.

The flow: a **baseline assessment** detects a skill gap → a five-agent pipeline
matches the gap to internal-first learning content → a **re-assessment** measures
the progression.

## Architecture

```
Assessment (HTML)  →  Observer  →  Skill Matcher  →  Retriever  →  Curator  →  Delivery  →  Nudge
                                   └── self-corrective RAG loop ──┘
```

| Node | Role |
|------|------|
| Observer (01) | Reads the assessment JSON, picks the gap to act on |
| Skill Matcher (02) | Matches gap to Digcomp skills; self-corrective RAG loop |
| Retriever (03) | Queries Chroma for content, internal-weighted |
| Curator (04) | Filters/ranks, chooses delivery format |
| Delivery (05) | Packages the nudge as a JSON payload |

## Setup

One command:

```bash
bash setup.sh
```

Then paste your Gemini key into `.env` (get one free at https://aistudio.google.com).

Or manually:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then paste your real keys into .env
```

## Run

```bash
python smoke_test.py             # 1. verify Gemini auth  → "ABL pipeline online"
python -m ingestion.build_vectorstore   # 2. build the Chroma vector store
python -m graph.build_graph      # 3. run the full pipeline → prints the final nudge
```

The pipeline runs even before the vector store is built — the Retriever falls
back to stubs — so you can test wiring first and add real content later.

## Team task split

Build your node against the frozen `ABLState` in `state.py` — don't change that file
without telling everyone. Each person works on a branch and opens a PR.

- **Observer** — `agents/observer.py` (done, reference example)
- **Skill Matcher + self-corrective loop** — `agents/skill_matcher.py` ← Cécile
- **Retriever + Chroma ingestion** — `agents/retriever.py`, `ingestion/build_vectorstore.py`
- **Curator** — `agents/curator.py`
- **Supervisor + Delivery + graph wiring** — `graph/build_graph.py`, `agents/delivery.py`

## Notes

- Never commit `.env` or the `chroma_db/` folder (both gitignored). Commit the
  ingestion *script*, not the built vector store — teammates rebuild it locally.
- `temperature=0` across all agents keeps demo runs reproducible.
- The Microsoft tools in the Repsol brief are what we *replace*, not a dependency.
