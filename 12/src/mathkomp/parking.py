"""Parken und Reaktivieren (Sprint 9).

§38 Wenn eine Kompetenz ausreichend konsistent gezeigt wurde: SECURE -> PARKED.
    Sie wird aus dem normalen aktiven Aufgabenpool entfernt.

§39 PARKED wird wieder aktiviert bei CONTRADICTORY_EVIDENCE, EVIDENCE_TOO_OLD
    oder NEW_TARGET_REQUIRES_PREREQUISITE zusammen mit
    EXISTING_EVIDENCE_INSUFFICIENT. Zeitgrenzen nicht hardcoden.

§122 Ein Pfad wird nicht endgueltig geloescht. Er wird geparkt und kann spaeter
     reaktiviert werden.

Zusaetzliche Bedingung fuer das Parken, die §38 nicht nennt: es muessen
mindestens zwei VERSCHIEDENE Items richtig beantwortet worden sein. Grund ist
§26 ITEM_SPECIFIC_SUCCESS und §19: zwei richtige Versuche an derselben Aufgabe
sind keine ausreichend konsistente Evidenz, weil Aufgaben derselben Kompetenz
nicht austauschbar sind. Die Zahl steht in system_config
(park.min_distinct_items). Siehe ENTSCHEIDUNGEN.md D-05.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .attempts import attempt_history
from .clock import Clock
from .config import Config
from .state import evidence_age_days


@dataclass
class Transition:
    competency_id: str
    from_status: str
    to_status: str
    reason: str | None
    spec_section: str


def check_park(conn: sqlite3.Connection, student_id: str, competency_id: str,
               cfg: Config, clock: Clock) -> Transition | None:
    """§38. Wird nach jeder Zustandsaenderung aufgerufen."""
    row = conn.execute(
        "SELECT status FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?", (student_id, competency_id)
    ).fetchone()
    if not row or row["status"] != cfg.require("park.enter_status"):
        return None

    history = attempt_history(conn, student_id, competency_id)
    distinct_correct = {r["task_id"] for r in history if r["is_correct"]}
    if len(distinct_correct) < cfg.require("park.min_distinct_items"):
        return None

    conn.execute(
        "UPDATE student_competency_state SET status = 'PARKED', parked_at = ?,"
        " reactivation_reason = NULL, updated_at = ?"
        " WHERE student_id = ? AND competency_id = ?",
        (clock.now_iso(), clock.now_iso(), student_id, competency_id),
    )
    return Transition(competency_id, row["status"], "PARKED", None, "§38")


def check_reactivation(conn: sqlite3.Connection, student_id: str, competency_id: str,
                       cfg: Config, clock: Clock,
                       new_target_requires: bool = False) -> Transition | None:
    """§39. Prueft die drei Reaktivierungsgruende in dieser Reihenfolge."""
    row = conn.execute(
        "SELECT status, parked_at, last_direct_evidence FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?", (student_id, competency_id)
    ).fetchone()
    if not row or row["status"] != "PARKED":
        return None

    reason = None

    # 1. Widerspruechliche Evidenz nach dem Parken.
    #    Eine direkte negative Beobachtung genuegt. Indirekte Evidenz zaehlt
    #    ebenfalls, aber erst in Wiederholung: §31 verlangt fuer die weiter vom
    #    Verhalten entfernte Schlussfolgerung staerkere Evidenz. Das ist der
    #    Fall aus §103 - "spaeter mehrere Stellenwertfehler" treten typischerweise
    #    beim Rechnen an anderer Stelle auf, wo Stellenwert Sekundaerkompetenz ist.
    direct = conn.execute(
        "SELECT COUNT(*) AS n FROM evidence_events WHERE student_id = ?"
        " AND competency_id = ? AND evidence_type = 'DIRECT_NEGATIVE'"
        " AND created_at > COALESCE(?, '')",
        (student_id, competency_id, row["parked_at"]),
    ).fetchone()["n"]
    indirect = conn.execute(
        "SELECT COUNT(*) AS n FROM evidence_events WHERE student_id = ?"
        " AND competency_id = ? AND evidence_type = 'INDIRECT_NEGATIVE'"
        " AND created_at > COALESCE(?, '')",
        (student_id, competency_id, row["parked_at"]),
    ).fetchone()["n"]
    if direct or indirect >= cfg.require("mastery.failure_replication_required"):
        reason = "CONTRADICTORY_EVIDENCE"

    # 2. Evidenz zu alt. §39 verbietet hardcodierte Zeitgrenzen; ist der Wert
    #    UNDEFINED, bleibt dieser Grund abgeschaltet statt geraten zu werden.
    if reason is None:
        max_age = cfg.optional("park.evidence_too_old_days")
        age = evidence_age_days(conn, student_id, competency_id, clock)
        if max_age is not None and age is not None and age > max_age:
            reason = "EVIDENCE_TOO_OLD"

    # 3. Ein neues Ziel braucht diese Voraussetzung und die vorhandene Evidenz
    #    reicht nicht. Wird vom Routing gesetzt.
    if reason is None and new_target_requires and _evidence_insufficient(
            conn, student_id, competency_id, cfg):
        reason = "NEW_TARGET_REQUIRES_PREREQUISITE"

    if reason is None:
        return None

    conn.execute(
        "UPDATE student_competency_state SET status = 'REACTIVATED',"
        " reactivation_reason = ?, updated_at = ?"
        " WHERE student_id = ? AND competency_id = ?",
        (reason, clock.now_iso(), student_id, competency_id),
    )
    return Transition(competency_id, "PARKED", "REACTIVATED", reason, "§39")


def _evidence_insufficient(conn: sqlite3.Connection, student_id: str, competency_id: str,
                           cfg: Config) -> bool:
    """EXISTING_EVIDENCE_INSUFFICIENT nach §39.

    Ausreichend heisst hier: genug direkte positive Evidenz UND ueber mehr als
    ein Item gezeigt. Damit ist die Bedingung dieselbe wie beim Parken - eine
    Kompetenz, die nur wegen eines einzigen Items geparkt wurde, gilt als
    unzureichend belegt, sobald sie tatsaechlich gebraucht wird.
    """
    history = attempt_history(conn, student_id, competency_id)
    distinct_correct = {r["task_id"] for r in history if r["is_correct"]}
    return len(distinct_correct) < cfg.require("park.min_distinct_items")


def set_blocked(conn: sqlite3.Connection, student_id: str, competency_id: str,
                clock: Clock, blocked: bool = True) -> Transition:
    """§3: die Lehrkraft kann Aufgaben sperren und Systementscheidungen
    uebersteuern. BLOCKED wird nur hier gesetzt und von recompute() respektiert."""
    row = conn.execute(
        "SELECT status FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?", (student_id, competency_id)
    ).fetchone()
    previous = row["status"] if row else "UNKNOWN"
    target = "BLOCKED" if blocked else "ACTIVE"
    if row:
        conn.execute(
            "UPDATE student_competency_state SET status = ?, updated_at = ?"
            " WHERE student_id = ? AND competency_id = ?",
            (target, clock.now_iso(), student_id, competency_id))
    else:
        conn.execute(
            "INSERT INTO student_competency_state (student_id, competency_id, status,"
            " updated_at) VALUES (?, ?, ?, ?)",
            (student_id, competency_id, target, clock.now_iso()))
    return Transition(competency_id, previous, target, "Lehrkraft", "§3")
