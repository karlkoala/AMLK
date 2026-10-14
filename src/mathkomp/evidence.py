"""Evidence Engine (Sprint 6).

Ebene 2 von §66: aus einer Beobachtung wird Evidenz. Diese Schicht setzt
keinen Kompetenzstatus (das ist state.py) und eroeffnet keine Hypothese (das
ist hypotheses.py).

Die drei bindenden Grenzen dieser Schicht:

§29  Ein Fehler ist keine Diagnose. Ein falscher Versuch erzeugt
     DIRECT_NEGATIVE auf der primaeren Kompetenz - nicht mehr.

§121 Keine automatische Ferninferenz. Aus A beobachtet folgt nicht E. Deshalb
     reicht indirekte Evidenz genau EINEN Schritt weit im Graphen, ist als
     INDIRECT_* markiert und traegt ein kleineres Gewicht.

§31  Je weiter die Schlussfolgerung vom beobachteten Verhalten entfernt ist,
     desto staerkere Evidenz muss erforderlich sein. Umgesetzt ueber
     abgestufte strength-Werte aus system_config.

Asymmetrie mit Absicht: ein RICHTIGER Versuch erzeugt indirekt positive
Evidenz auf den Voraussetzungen (wer 6*8 loest, hat die Voraussetzungen
wahrscheinlich). Ein FALSCHER Versuch erzeugt KEINE indirekt negative Evidenz
auf den Voraussetzungen - das waere der Schluss "Aufgabe falsch, also
Voraussetzung fehlt", den §29 und §31 gerade verbieten. Stattdessen loest der
Fehler nach §30 ein Parallelitem aus und erst nach Replikation nach §31 eine
Voraussetzungspruefung. Siehe ENTSCHEIDUNGEN.md D-05.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from . import ids
from .attempts import RecordedAttempt, load_task, task_features
from .clock import Clock
from .config import Config

#: Evidenzarten, die in direct_evidence_score und indirect_evidence_score
#: eingehen. Die uebrigen Arten aus §28 sind typisierte Zusatzbeobachtungen
#: fuer Hypothesen und Facetten und werden NICHT mitsummiert - sonst zaehlte
#: ein Versuch mehrfach.
SCORED_TYPES = ("DIRECT_POSITIVE", "DIRECT_NEGATIVE",
                "INDIRECT_POSITIVE", "INDIRECT_NEGATIVE")

PREREQUISITE_TYPES = ("HARD_PREREQUISITE", "STRONG_PREREQUISITE")


@dataclass
class EvidenceRecord:
    evidence_id: str
    competency_id: str
    evidence_type: str
    direction: str
    strength: float | None


def _direction(is_correct: bool) -> str:
    return "POSITIVE" if is_correct else "NEGATIVE"


def _answer_is_expression(task: dict) -> bool:
    correct = json.loads(task["correct_answer"])
    expected = correct.get("selection") or correct.get("expression")
    return isinstance(expected, str) and any(op in expected for op in "+-*:")


def create(conn: sqlite3.Connection, student_id: str, attempt: RecordedAttempt,
           clock: Clock, cfg: Config) -> list[EvidenceRecord]:
    """Erzeugt alle Evidenzereignisse zu einem Versuch."""
    task = load_task(conn, attempt.task_id)
    features = task_features(conn, attempt.task_id)
    direction = _direction(attempt.is_correct)

    support_used = conn.execute(
        "SELECT support_used FROM task_attempts WHERE attempt_id = ?", (attempt.attempt_id,)
    ).fetchone()["support_used"]

    w_direct = cfg.require("evidence.weight_direct")
    w_indirect = cfg.require("evidence.weight_indirect")
    w_support = cfg.require("evidence.weight_support")
    w_cross = cfg.require("evidence.weight_cross_domain")
    support_factor = cfg.require("evidence.support_discount") if support_used else 1.0
    review_days = cfg.optional("park.next_review_interval_days")

    out: list[EvidenceRecord] = []

    def emit(competency_id: str, evidence_type: str, strength: float | None,
             direction_override: str | None = None) -> None:
        record = EvidenceRecord(
            evidence_id=ids.next_id(conn, "evidence_events", student_id),
            competency_id=competency_id, evidence_type=evidence_type,
            direction=direction_override or direction,
            strength=None if strength is None else round(min(1.0, strength), 4),
        )
        conn.execute(
            "INSERT INTO evidence_events (evidence_id, student_id, competency_id,"
            " source_task, source_attempt, evidence_type, direction, strength,"
            " created_at, review_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record.evidence_id, student_id, competency_id, attempt.task_id,
             attempt.attempt_id, record.evidence_type, record.direction,
             record.strength, clock.now_iso(), clock.plus_days_iso(review_days)),
        )
        out.append(record)

    # 1. Direkte Evidenz auf der primaeren Kompetenz (§28).
    emit(task["primary_competency"],
         "DIRECT_POSITIVE" if attempt.is_correct else "DIRECT_NEGATIVE",
         w_direct * support_factor)

    # 2. Sekundaerkompetenzen: das Item beruehrt sie nachweislich, also
    #    indirekte Evidenz in beide Richtungen - aber mit kleinerem Gewicht (§31).
    for secondary in json.loads(task["secondary_competencies"]):
        emit(secondary,
             "INDIRECT_POSITIVE" if attempt.is_correct else "INDIRECT_NEGATIVE",
             w_indirect * support_factor)

    # 3. Voraussetzungen: nur bei richtiger Antwort, nur einen Schritt weit (§121).
    if attempt.is_correct:
        for row in conn.execute(
            "SELECT source_competency FROM relations WHERE target_competency = ?"
            f" AND relation_type IN ({','.join('?' * len(PREREQUISITE_TYPES))})",
            (task["primary_competency"], *PREREQUISITE_TYPES),
        ):
            emit(row["source_competency"], "INDIRECT_POSITIVE", w_indirect * support_factor)

    # 4. Typisierte Zusatzevidenz. Geht nicht in die Scores ein, sondern
    #    traegt Facetten (§117) und Hypothesen (§64).
    emit(task["primary_competency"], "REPRESENTATION_EVIDENCE", w_direct * support_factor)

    if _answer_is_expression(task) or features.get("STRATEGY_AFFORDANCE"):
        emit(task["primary_competency"], "STRATEGY_EVIDENCE", w_direct * support_factor)

    if task["task_purpose"] == "TRANSFER":
        emit(task["primary_competency"], "TRANSFER_EVIDENCE", w_direct * support_factor)

    if support_used:
        # §33: eine Leistung unter Unterstuetzung ist nicht dieselbe Beobachtung
        # wie eine ohne. Deshalb ein eigener Evidenztyp statt eines Abzugs.
        emit(task["primary_competency"], "SUPPORT_EVIDENCE", w_support)

    # 5. Leitideenuebergreifend (§14). Ziel ist der Wurzelknoten der Leitidee,
    #    weil L2 bis L5 im MVP keine inhaltlichen Knoten haben (§7).
    for leitidee in json.loads(task["secondary_leitideen"]):
        root = conn.execute(
            "SELECT competency_id FROM competencies WHERE leitidee = ? AND parent_id IS NULL",
            (leitidee,),
        ).fetchone()
        if root:
            emit(root["competency_id"], "CROSS_DOMAIN_EVIDENCE", w_cross)

    return out


def counts(conn: sqlite3.Connection, student_id: str, competency_id: str) -> dict:
    """Gezaehlte und gewichtete Evidenz einer Kompetenz.

    §117 verbietet, daraus einen Prozentwert zu bilden. Die Werte dienen
    ausschliesslich den Statusuebergaengen und der Konsistenzberechnung.
    """
    rows = list(conn.execute(
        "SELECT evidence_type, direction, strength, created_at FROM evidence_events"
        " WHERE student_id = ? AND competency_id = ?"
        f" AND evidence_type IN ({','.join('?' * len(SCORED_TYPES))})"
        " ORDER BY created_at, evidence_id",
        (student_id, competency_id, *SCORED_TYPES),
    ))
    direct_pos = sum(1 for r in rows if r["evidence_type"] == "DIRECT_POSITIVE")
    direct_neg = sum(1 for r in rows if r["evidence_type"] == "DIRECT_NEGATIVE")
    ind_pos = sum(1 for r in rows if r["evidence_type"] == "INDIRECT_POSITIVE")
    ind_neg = sum(1 for r in rows if r["evidence_type"] == "INDIRECT_NEGATIVE")

    direct_score = sum((r["strength"] or 0) * (1 if r["direction"] == "POSITIVE" else -1)
                       for r in rows if r["evidence_type"].startswith("DIRECT"))
    indirect_score = sum((r["strength"] or 0) * (1 if r["direction"] == "POSITIVE" else -1)
                         for r in rows if r["evidence_type"].startswith("INDIRECT"))

    return {
        "direct_positive": direct_pos, "direct_negative": direct_neg,
        "indirect_positive": ind_pos, "indirect_negative": ind_neg,
        "direct_score": round(direct_score, 4),
        "indirect_score": round(indirect_score, 4),
        "consistency": consistency(direct_pos, direct_neg),
        "first": rows[0]["created_at"] if rows else None,
        "last_direct": next((r["created_at"] for r in reversed(rows)
                             if r["evidence_type"].startswith("DIRECT")), None),
        "last_indirect": next((r["created_at"] for r in reversed(rows)
                               if r["evidence_type"].startswith("INDIRECT")), None),
    }


def consistency(positive: int, negative: int) -> float | None:
    """Konsistenz der direkten Evidenz, 0 bis 1.

    1.0 bedeutet: alle Beobachtungen zeigen in dieselbe Richtung. 0.0 bedeutet:
    genau haelftig widersprüchlich. §41 warnt ausdruecklich, dass einfache
    Zaehlregeln zufaellige Fehler und unterschiedliche Aufgabenmerkmale schlecht
    beruecksichtigen - deshalb steuert die Konsistenz mit, ob ueberhaupt ein
    Status gesetzt wird, und deshalb ist der Schwellwert konfigurierbar.

    Diese Formel ist eine Entscheidung des Implementierers; §63 fuehrt das Feld
    evidence_consistency, gibt aber keine Vorschrift an (F-08, D-05).
    """
    total = positive + negative
    if total == 0:
        return None
    return round(abs(positive - negative) / total, 4)
