"""
Run this first, before building anything else.
Verifies your .env is set up and Gemini auth works.

    python smoke_test.py

Expected output:  ABL pipeline online
"""

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
print(llm.invoke("Reply with exactly: ABL pipeline online").content)
