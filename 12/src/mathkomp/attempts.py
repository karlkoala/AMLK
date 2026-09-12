"""Versuche und Interaktionsdaten (Sprint 5).

Diese Schicht schreibt ausschliesslich Rohdaten und Beobachtungen - Ebene 1
von §66. Sie erzeugt keine Evidenz und keinen Kompetenzstatus.

§60 gibt die Felder eines Versuchs vor, §61 die eines Interaktionsereignisses.
Die Rohantwort wird unveraendert gespeichert: §66 verlangt ausdruecklich, dass
answer = 58 als Beobachtung erhalten bleibt und nicht durch den daraus
abgeleiteten Fehlercode ersetzt wird.

§62 ist bindend: time_seconds wird gespeichert, aber nirgends als
Kompetenzindikator gelesen. Die Pruefregel rule_time_not_used_for_inference
sichert das ab.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from . import ids, scoring
from .clock import Clock


@dataclass
class Submission:
    """Was die Oberflaeche abgibt."""
    task_id: str
    answer: Any
    events: list[dict] = field(default_factory=list)
    time_seconds: float | None = None
    support_used: bool = False
    #: ROUTE_REASON, mit dem das Routing dieses Item ausgewaehlt hat (§31).
    selected_by_reason: str | None = None
    #: route_id oder Regelname, fuer das Entscheidungsprotokoll (§89).
    selected_by_rule: str | None = None


@dataclass
class RecordedAttempt:
    attempt_id: str
    task_id: str
    is_correct: bool
    score: float
    error_codes: list[str]
    attempt_number: int


def ensure_student(conn: sqlite3.Connection, student_id: str, clock: Clock,
                   grade_reference: int | None = None) -> None:
    """§86: nur pseudonyme ID, kein personenbezogenes Feld."""
    exists = conn.execute(
        "SELECT 1 FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    if exists:
        return
    conn.execute(
        "INSERT INTO students (student_id, created_at, grade_reference) VALUES (?, ?, ?)",
        (student_id, clock.now_iso(), grade_reference),
    )


def task_features(conn: sqlite3.Connection, task_id: str) -> dict[str, set[str]]:
    """Merkmale eines Items nach Klasse (§82)."""
    out: dict[str, set[str]] = {}
    for row in conn.execute(
        "SELECT feature_kind, feature_value FROM task_features WHERE task_id = ?", (task_id,)
    ):
        out.setdefault(row["feature_kind"], set()).add(row["feature_value"])
    return out


def load_task(conn: sqlite3.Connection, task_id: str) -> dict:
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if row is None:
        raise KeyError(f"Unbekannte Aufgabe: {task_id}")
    return dict(row)


def record(conn: sqlite3.Connection, student_id: str, submission: Submission,
           clock: Clock) -> RecordedAttempt:
    """Wertet aus, klassifiziert und schreibt Rohdaten. Ebene 1 von §66."""
    task = load_task(conn, submission.task_id)
    result = scoring.score(task, submission.answer)

    ctx = scoring.ClassificationContext(
        features=task_features(conn, submission.task_id),
        events=submission.events,
        selected_by_reason=submission.selected_by_reason,
    )
    codes = scoring.classify(task, submission.answer, result, ctx)

    previous = conn.execute(
        "SELECT COUNT(*) AS n FROM task_attempts WHERE student_id = ? AND task_id = ?",
        (student_id, submission.task_id),
    ).fetchone()["n"]
    attempt_number = previous + 1

    attempt_id = ids.next_id(conn, "task_attempts", student_id)
    now = clock.now_iso()
    conn.execute(
        "INSERT INTO task_attempts (attempt_id, student_id, task_id, started_at,"
        " completed_at, answer, is_correct, score, time_seconds, support_used,"
        " attempt_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (attempt_id, student_id, submission.task_id, now, now,
         json.dumps(submission.answer, ensure_ascii=False),
         1 if result.is_correct else 0, result.score, submission.time_seconds,
         1 if submission.support_used else 0, attempt_number),
    )

    for i, event in enumerate(submission.events, 1):
        conn.execute(
            "INSERT INTO interaction_events (event_id, attempt_id, timestamp,"
            " event_type, object_id, value, sequence_number) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ids.next_id(conn, "interaction_events"), attempt_id,
             event.get("timestamp", now), event["event_type"],
             event.get("object_id"),
             None if event.get("value") is None else str(event["value"]), i),
        )

    for code in codes:
        conn.execute(
            "INSERT OR IGNORE INTO attempt_error_codes (attempt_id, error_code, detail)"
            " VALUES (?, ?, ?)",
            (attempt_id, code, json.dumps(result.detail, ensure_ascii=False)),
        )

    return RecordedAttempt(attempt_id=attempt_id, task_id=submission.task_id,
                           is_correct=result.is_correct, score=result.score,
                           error_codes=codes, attempt_number=attempt_number)


def attempt_history(conn: sqlite3.Connection, student_id: str,
                    competency_id: str | None = None) -> list[dict]:
    """Versuche mit den Merkmalen der zugehoerigen Aufgabe.

    Grundlage fuer §71 (Merkmale vergleichen statt pauschal herabstufen) und
    fuer §117 (Aufschluesselung nach Facetten statt Prozentwert).
    """
    sql = (
        "SELECT a.attempt_id, a.task_id, a.is_correct, a.score, a.support_used,"
        " a.attempt_number, a.completed_at, t.primary_competency,"
        " t.internal_difficulty, t.representation_mode, t.interaction_mode,"
        " t.task_purpose, t.task_family_id, t.secondary_competencies,"
        " t.scoring_rule, t.question_form"
        " FROM task_attempts a JOIN tasks t ON t.task_id = a.task_id"
        " WHERE a.student_id = ?"
    )
    params: list[Any] = [student_id]
    if competency_id:
        sql += " AND t.primary_competency = ?"
        params.append(competency_id)
    sql += " ORDER BY a.completed_at, a.attempt_id"

    rows = [dict(r) for r in conn.execute(sql, params)]
    for row in rows:
        row["features"] = task_features(conn, row["task_id"])
        row["error_codes"] = [
            r["error_code"] for r in conn.execute(
                "SELECT error_code FROM attempt_error_codes WHERE attempt_id = ?",
                (row["attempt_id"],))
        ]
        row["secondary_competencies"] = json.loads(row["secondary_competencies"])
    return rows
