"""Fortlaufende, sprechende Schluessel.

Bewusst keine UUIDs fuer Versuche, Evidenz, Hypothesen und Entscheidungen:
§88 verlangt, dass eine Lehrkraft nachvollziehen kann, warum das System einen
Pfad gewaehlt hat, und §89 verlangt ein Entscheidungsprotokoll. Ein Protokoll
mit lesbaren, geordneten Schluesseln ist dafuer brauchbar, eines mit UUIDs
nicht. Nebeneffekt: die Simulation der sechs Testfaelle (§104 Sprint 12) wird
reproduzierbar.

§86 bleibt unberuehrt: die student_id selbst ist ein pseudonymes UUID und
taucht in diesen Schluesseln nur gekuerzt und ohne Rueckschlussmoeglichkeit auf
den Klarnamen auf, weil es keinen Klarnamen gibt.
"""

from __future__ import annotations

import hashlib
import sqlite3

_COUNTED = {
    "task_attempts": ("attempt_id", "AT"),
    "evidence_events": ("evidence_id", "EV"),
    "student_hypotheses": ("hypothesis_id", "HY"),
    "routing_decisions": ("decision_id", "DE"),
    "interaction_events": ("event_id", "IE"),
}


def student_tag(student_id: str) -> str:
    """Kurzes, stabiles Kuerzel einer pseudonymen student_id."""
    return hashlib.sha1(student_id.encode("utf-8")).hexdigest()[:6].upper()


def next_id(conn: sqlite3.Connection, table: str, student_id: str | None = None) -> str:
    column, prefix = _COUNTED[table]
    if student_id and table != "interaction_events":
        row = conn.execute(
            f"SELECT COUNT(*) AS n FROM {table} WHERE student_id = ?", (student_id,)
        ).fetchone()
        return f"{prefix}-{student_tag(student_id)}-{row['n'] + 1:04d}"
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
    return f"{prefix}-{row['n'] + 1:06d}"
