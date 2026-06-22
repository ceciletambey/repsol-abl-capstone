"""
Builds the Chroma vector store from learning content.

    python -m ingestion.build_vectorstore

Each document is tagged with source = "internal" or "external" so the
Retriever can rank internal Repsol content first (per the brief).

Replace SAMPLE_DOCS with real content: Digcomp skill definitions, the
Level 1-4 internal course catalog, SOPs, and external trend articles.
"""

import os
from dotenv import load_dotenv

load_dotenv()

PERSIST_DIR = "chroma_db"

# --- Replace these with real Repsol content ---
SAMPLE_DOCS = [
    {
        "text": "Power BI Intermediate Level (16h): building reports, data "
                "transformation, table relationships, intro to DAX measures.",
        "source": "internal",
        "skill": "power_bi",
    },
    {
        "text": "DAX (Data Analysis Expressions) is Power BI's formula language "
                "for calculated columns and measures beyond drag-and-drop.",
        "source": "internal",
        "skill": "power_bi",
    },
    {
        "text": "Introduction to GenAI and Prompting (2h): Repsol's 6 Ps method "
                "for giving an AI enough context to produce useful output.",
        "source": "internal",
        "skill": "ai_prompting",
    },
    {
        "text": "External blog: 10 advanced DAX patterns every analyst should know.",
        "source": "external",
        "skill": "power_bi",
    },
]


def build():
    from langchain_chroma import Chroma
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    texts = [d["text"] for d in SAMPLE_DOCS]
    metadatas = [{"source": d["source"], "skill": d["skill"]} for d in SAMPLE_DOCS]

    store = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        persist_directory=PERSIST_DIR,
    )
    print(f"Built vector store with {len(texts)} documents at ./{PERSIST_DIR}")


if __name__ == "__main__":
    build()
