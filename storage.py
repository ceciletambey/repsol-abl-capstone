"""
Persistent memory layer for the Repsol ABL app.

Stores each completed learning cycle (baseline -> nudge -> re-assessment) in
a local SQLite database so an employee's skill progression survives page
refreshes and can be plotted over time in "My Progress". This module is
additive only — it never touches `ABLState`, the `graph/` pipeline, or
`agents/`; it just persists numbers `app.py` already computes.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "abl_memory.db"

DEMO_EMPLOYEE = "Ana García (DEMO)"
DEMO_ROLE = "Marketing Teams"


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the learning_cycles table if it doesn't exist yet."""
    try:
        with _connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee TEXT NOT NULL,
                    role TEXT,
                    skill TEXT NOT NULL,
                    before_level INTEGER NOT NULL,
                    after_level INTEGER NOT NULL,
                    required_level INTEGER,
                    verdict TEXT,
                    created_at TEXT NOT NULL DEFAULT (date('now'))
                )
            """)
    except sqlite3.Error as e:
        print(f"[storage] Failed to initialise database: {e}")


def save_cycle(employee, role, skill, before_level, after_level, required_level, verdict, created_at=None):
    """Insert one completed learning cycle for an employee/skill."""
    try:
        with _connect() as conn:
            conn.execute(
                """INSERT INTO learning_cycles
                   (employee, role, skill, before_level, after_level, required_level, verdict, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, date('now')))""",
                (employee, role, skill, before_level, after_level, required_level, verdict, created_at),
            )
    except sqlite3.Error as e:
        print(f"[storage] Failed to save cycle for {employee}/{skill}: {e}")


def get_history(employee):
    """All recorded cycles for an employee, oldest first."""
    try:
        with _connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, employee, role, skill, before_level, after_level, required_level,
                          verdict, created_at
                   FROM learning_cycles
                   WHERE employee = ?
                   ORDER BY created_at ASC, id ASC""",
                (employee,),
            ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[storage] Failed to read history for {employee}: {e}")
        return []


def list_employees():
    """Distinct employee names/IDs that have at least one stored cycle."""
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT employee FROM learning_cycles ORDER BY employee ASC"
            ).fetchall()
            return [row[0] for row in rows]
    except sqlite3.Error as e:
        print(f"[storage] Failed to list employees: {e}")
        return []


def seed_demo_employee():
    """Insert a fictional, idempotent demo employee with an upward skill trend
    across three skills and ~3 months of history, so 'My Progress' looks
    populated from the first run of a live demo."""
    if DEMO_EMPLOYEE in list_employees():
        return

    today = date.today()
    # (skill, before_level, after_level, required_level, verdict, days_ago)
    cycles = [
        ("power_bi", 1, 2, None, "GOOD", 84),
        ("power_bi", 2, 2, None, "NEEDS WORK", 63),
        ("power_bi", 2, 3, None, "GOOD", 42),
        ("ia_gen", 1, 2, 3, "NEEDS WORK", 70),
        ("ia_gen", 2, 3, 3, "GOOD", 49),
        ("ia_gen", 3, 3, 3, "GOOD", 21),
        ("data", 1, 2, 3, "NEEDS WORK", 77),
        ("data", 2, 2, 3, "NEEDS WORK", 56),
        ("data", 2, 3, 3, "GOOD", 14),
    ]
    for skill, before_level, after_level, required_level, verdict, days_ago in cycles:
        created_at = (today - timedelta(days=days_ago)).isoformat()
        save_cycle(DEMO_EMPLOYEE, DEMO_ROLE, skill, before_level, after_level, required_level, verdict, created_at)


init_db()
