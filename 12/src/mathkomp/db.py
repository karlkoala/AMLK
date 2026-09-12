"""Datenbankzugriff.

Bewusst duenn: sqlite3 aus der Standardbibliothek, keine ORM-Schicht.
Sprint 1 braucht nur Schema-Initialisierung und Transaktionen; ab Sprint 4
kann eine API-Schicht darauf aufsetzen, ohne dass sich das Schema aendert.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

#: Die 13 in §78 verlangten Tabellen. Der Rest des Schemas (vocabularies,
#: vocabulary_terms, students, attempt_error_codes, routing_decisions,
#: system_config) ist Ergaenzung - §78 sagt "Mindestens".
REQUIRED_TABLES_SPEC_78 = (
    "competencies",
    "relations",
    "task_families",
    "tasks",
    "task_routes",
    "task_features",
    "error_codes",
    "student_competency_state",
    "student_hypotheses",
    "task_attempts",
    "interaction_events",
    "evidence_events",
    "sources",
)


def connect(path: str | Path) -> sqlite3.Connection:
    """Oeffnet eine Verbindung mit aktivierten Fremdschluesseln."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Legt das Schema an. Bricht ab, wenn schon Tabellen existieren."""
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'competencies'"
    ).fetchone()
    if existing:
        raise RuntimeError(
            "Schema existiert bereits. Zum Neuaufbau die Datenbankdatei loeschen."
        )
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {row["name"] for row in rows}


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Alles-oder-nichts. Ein fehlgeschlagener Import laesst keine
    halb gefuellte Datenbank zurueck."""
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def check_foreign_keys(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liefert alle verletzten Fremdschluessel. Muss leer sein."""
    return conn.execute("PRAGMA foreign_key_check").fetchall()
