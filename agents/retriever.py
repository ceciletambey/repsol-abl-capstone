"""
Agent 03 — The Retriever.

Queries the Chroma vector store for learning content matching the skill gap.
Repsol's brief requires INTERNAL content ranked before external, so we fetch
from both and boost internal results.

Falls back to a stub list if the vector store hasn't been built yet, so the
graph runs end-to-end before ingestion is finished.
"""

import os

PERSIST_DIR = "chroma_db"


def retriever_node(state):
    query = state["skill_gap"]

    try:
        from langchain_chroma import Chroma
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        store = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)

        results = store.similarity_search(query, k=6)
        chunks = [
            {
                "text": r.page_content,
                "source": r.metadata.get("source", "external"),
            }
            for r in results
        ]
        # Boost internal: internal chunks first, external after.
        chunks.sort(key=lambda c: 0 if c["source"] == "internal" else 1)

    except Exception:
        # Vector store not built yet — stub so the pipeline still runs.
        chunks = [
            {"text": f"[stub] internal course matching: {query}", "source": "internal"},
            {"text": f"[stub] external article matching: {query}", "source": "external"},
        ]

    return {"candidate_content": chunks}
