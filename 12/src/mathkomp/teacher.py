"""Lehrkraftansicht (§106) und Nachvollziehbarkeit (§88).

§3 ist der Rahmen: KI/System + Schueler:in + Lehrkraft. Das System liefert
Beobachtungen, Kompetenz-Evidenz, Muster, offene Hypothesen, moegliche naechste
Pruefschritte und Foerdervorschlaege. Es trifft keine endgueltigen
paedagogischen oder diagnostischen Entscheidungen.

§106 verlangt mindestens: Kompetenz, Status, Evidenz, letzte Aufgaben, offene
Hypothesen, aktueller Foerderbereich, naechster geplanter Schritt.

§117 verbietet den Prozentwert und verlangt die Aufschluesselung nach Facetten.
Dieser Report zeigt deshalb nirgends einen Anteil richtiger Antworten. Er zeigt
Zaehlungen (zwei richtig, ein falsch) und Facettenstatus - das ist etwas
anderes als eine Quote, weil es die Bedingungen mitnennt.

§88 verlangt, dass die Lehrkraft erkennen kann, warum das System diesen Pfad
gewaehlt hat. Dafuer wird das Entscheidungsprotokoll (§89) mitgelesen.
"""

from __future__ import annotations

import json
import sqlite3

from . import hypotheses as hypo
from .attempts import attempt_history
from .clock import Clock
from .config import Config
from .state import facets_of, variation_dimensions

#: Facettenklassen, die in der Lehrkraftansicht gezeigt werden, in dieser
#: Reihenfolge. §118 zeigt genau diese Art von Aufschluesselung fuer ZO09:
#: concept, symbolic, iconic, derived strategy.
REPORTED_FACETS = ("REPRESENTATION_MODE", "INTERNAL_DIFFICULTY", "STRUCTURAL_FEATURE",
                   "STRATEGY_AFFORDANCE", "SURFACE_FEATURE", "TASK_PURPOSE")

STATUS_LABEL = {
    "UNKNOWN": "unbekannt",
    "ACTIVE": "in Bearbeitung",
    "SECURE": "aktuell ausreichend konsistente Evidenz",
    "UNCERTAIN": "unsicher, widersprüchliche Evidenz",
    "SUPPORT_FOCUS": "Förderschwerpunkt",
    "PARKED": "geparkt",
    "BLOCKED": "gesperrt durch Lehrkraft",
    "REACTIVATED": "reaktiviert",
}


def report(conn: sqlite3.Connection, student_id: str, cfg: Config,
           clock: Clock) -> dict:
    """Vollstaendiger Bericht zu einer Schueler:in."""
    competencies = []
    for row in conn.execute(
        "SELECT s.*, c.name FROM student_competency_state s"
        " JOIN competencies c ON c.competency_id = s.competency_id"
        " WHERE s.student_id = ? ORDER BY s.competency_id", (student_id,)
    ):
        competency_id = row["competency_id"]
        history = attempt_history(conn, student_id, competency_id)
        facets = facets_of(conn, student_id, competency_id)
        competencies.append({
            "competency_id": competency_id,
            "name": row["name"],
            "status": row["status"],
            "status_label": STATUS_LABEL.get(row["status"], row["status"]),
            "evidence": {
                "direct_positive": sum(1 for h in history if h["is_correct"]),
                "direct_negative": sum(1 for h in history if not h["is_correct"]),
                "consistency": row["evidence_consistency"],
                "first": row["first_evidence"],
                "last_direct": row["last_direct_evidence"],
                "next_review": row["next_review"],
            },
            "window": {"floor": row["current_floor"], "ceiling": row["current_ceiling"]},
            "profile_markers": json.loads(row["profile_markers"]),
            "variation_dimensions": variation_dimensions(history),
            "facets": {
                kind: {value: entry["status"] for value, entry in sorted(values.items())}
                for kind, values in facets.items() if kind in REPORTED_FACETS
            },
            "recent_tasks": [
                {"task_id": h["task_id"], "correct": bool(h["is_correct"]),
                 "difficulty": h["internal_difficulty"],
                 "representation": h["representation_mode"],
                 "errors": h["error_codes"]}
                for h in history[-5:]
            ],
            "parked_at": row["parked_at"],
            "reactivation_reason": row["reactivation_reason"],
        })

    open_hypotheses = [
        {**h, "beschreibung": hypo.describe(h)} for h in hypo.open_hypotheses(conn, student_id)
    ]

    support_focus = [c["competency_id"] for c in competencies
                     if c["status"] == "SUPPORT_FOCUS"]

    last_decision = conn.execute(
        "SELECT * FROM routing_decisions WHERE student_id = ?"
        " ORDER BY timestamp DESC, decision_id DESC LIMIT 1", (student_id,)
    ).fetchone()

    return {
        "student_id": student_id,
        "competencies": competencies,
        "open_hypotheses": open_hypotheses,
        "support_focus": support_focus,
        "next_step": dict(last_decision) if last_decision else None,
        "totals": {
            "attempts": conn.execute(
                "SELECT COUNT(*) AS n FROM task_attempts WHERE student_id = ?",
                (student_id,)).fetchone()["n"],
            "decisions": conn.execute(
                "SELECT COUNT(*) AS n FROM routing_decisions WHERE student_id = ?",
                (student_id,)).fetchone()["n"],
        },
    }


def render(rep: dict) -> str:
    """Textfassung. §106 nennt die Pflichtfelder, §88 die Begruendungspflicht."""
    lines: list[str] = []
    lines.append(f"LEHRKRAFTANSICHT  Schueler:in {rep['student_id']}")
    lines.append(f"{rep['totals']['attempts']} Aufgaben bearbeitet,"
                 f" {rep['totals']['decisions']} Routingentscheidungen protokolliert")
    lines.append("")

    for c in rep["competencies"]:
        ev = c["evidence"]
        lines.append(f"{c['competency_id']}  {c['name']}")
        lines.append(f"  Status      {c['status']} - {c['status_label']}")
        # §117: Zaehlung mit Bedingungen, kein Prozentwert.
        lines.append(f"  Evidenz     {ev['direct_positive']} richtig,"
                     f" {ev['direct_negative']} falsch"
                     f"  (Konsistenz {ev['consistency']})")
        if c["window"]["floor"] or c["window"]["ceiling"]:
            lines.append(f"  Fenster     Untergrenze {c['window']['floor'] or '-'},"
                         f" Obergrenze {c['window']['ceiling'] or '-'}")
        if c["profile_markers"]:
            lines.append(f"  Marker      {', '.join(c['profile_markers'])}"
                         "   (§26: keine Diagnosen)")
        for kind, values in c["facets"].items():
            shown = ", ".join(f"{v}={s}" for v, s in values.items())
            lines.append(f"  {kind:<22} {shown}")
        if c["reactivation_reason"]:
            lines.append(f"  Reaktiviert {c['reactivation_reason']}")
        if c["recent_tasks"]:
            lines.append("  Letzte Aufgaben")
            for t in c["recent_tasks"]:
                mark = "richtig" if t["correct"] else "falsch "
                errors = f"  [{', '.join(t['errors'])}]" if t["errors"] else ""
                lines.append(f"    {t['task_id']:<24} {t['difficulty']}"
                             f" {t['representation']:<20} {mark}{errors}")
        lines.append("")

    if rep["open_hypotheses"]:
        lines.append("OFFENE HYPOTHESEN  (§115: jede ist durch eine Aufgabe widerlegbar)")
        for h in rep["open_hypotheses"]:
            lines.append(f"  {h['hypothesis_id']}  {h['status']}  {h['hypothesis_type']}")
            lines.append(f"    {h['beschreibung']}")
            lines.append(f"    widerlegbar durch: {h['falsifying_task'] or 'kein Item vorhanden'}")
        lines.append("")

    if rep["support_focus"]:
        lines.append(f"AKTUELLER FOERDERBEREICH  {', '.join(rep['support_focus'])}")
        lines.append("")

    step = rep["next_step"]
    if step:
        lines.append("NAECHSTER SCHRITT  (§88, §89)")
        lines.append(f"  Aufgabe      {step['selected_task'] or 'keine - nicht weitertesten'}")
        lines.append(f"  Regel        {step['rule_triggered']}")
        lines.append(f"  Konfidenz    {step['confidence']}"
                     "   (Sicherheit der Auswahl, nicht einer Aussage über die Schüler:in)")
        alternatives = json.loads(step["alternatives_considered"])
        if alternatives:
            lines.append("  Alternativen")
            for alt in alternatives:
                lines.append(f"    {alt['task_id']:<24} Score {alt['score']}"
                             f"  {alt.get('reason') or ''}")
    return "\n".join(lines)


def profile_summary(conn: sqlite3.Connection, student_id: str) -> str:
    """Zielbild aus §118: Status je Knoten, Facetten je Kompetenz, offene
    Hypothese, naechster Schritt. §118: "Das ist wesentlich informativer als
    eine Schulnote."
    """
    lines = [f"STUDENT {student_id}", ""]
    for row in conn.execute(
        "SELECT competency_id, status FROM student_competency_state"
        " WHERE student_id = ? ORDER BY competency_id", (student_id,)
    ):
        lines.append(f"  {row['competency_id']:<32} {row['status']}")
    lines.append("")
    for row in conn.execute(
        "SELECT DISTINCT competency_id FROM student_competency_facets"
        " WHERE student_id = ? ORDER BY competency_id", (student_id,)
    ):
        facets = facets_of(conn, student_id, row["competency_id"])
        representation = facets.get("REPRESENTATION_MODE", {})
        strategy = facets.get("STRATEGY_AFFORDANCE", {})
        if not representation and not strategy:
            continue
        lines.append(f"  {row['competency_id']}:")
        for value, entry in sorted(representation.items()):
            lines.append(f"      {value:<24} {entry['status']}")
        for value, entry in sorted(strategy.items()):
            lines.append(f"      {value:<24} {entry['status']}")
    lines.append("")
    for h in hypo.open_hypotheses(conn, student_id):
        lines.append(f"  OFFEN: {hypo.describe(h)}")
    last = conn.execute(
        "SELECT selected_task FROM routing_decisions WHERE student_id = ?"
        " ORDER BY timestamp DESC, decision_id DESC LIMIT 1", (student_id,)).fetchone()
    if last:
        lines.append(f"  NAECHSTES: {last['selected_task'] or 'nicht weitertesten (§73)'}")
    return "\n".join(lines)


def decision_trail(conn: sqlite3.Connection, student_id: str, limit: int = 20) -> str:
    """§89 Explainability Logging, lesbar gemacht."""
    lines = ["ENTSCHEIDUNGSPROTOKOLL (§89)", ""]
    for row in conn.execute(
        "SELECT * FROM routing_decisions WHERE student_id = ?"
        " ORDER BY timestamp, decision_id LIMIT ?", (student_id, limit)
    ):
        lines.append(f"{row['decision_id']}  {row['timestamp']}")
        lines.append(f"  vorher   {row['previous_task'] or '-'}")
        lines.append(f"  gewaehlt {row['selected_task'] or '- (nicht weitertesten)'}")
        lines.append(f"  Regel    {row['rule_triggered']}   Konfidenz {row['confidence']}")
        breakdown = json.loads(row["score_breakdown"])
        if breakdown:
            lines.append("  Score    " + ", ".join(
                f"{k}={v}" for k, v in sorted(breakdown.items()) if v))
        used = json.loads(row["hypothesis_used"])
        if used:
            lines.append(f"  Hypothese {', '.join(used)}")
        lines.append("")
    return "\n".join(lines)
