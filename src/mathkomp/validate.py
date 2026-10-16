"""Pruefregeln auf der importierten Datenbank.

Jede Regel nennt den Abschnitt der Spezifikation, den sie durchsetzt.

Zwei Schweregrade:
    ERROR   - verletzt eine ausdrueckliche Vorgabe der Spezifikation.
              Der MVP gilt damit als nicht abnahmefaehig.
    NOTICE  - fachliche Luecke oder Inkonsistenz in der Spezifikation selbst.
              Kein Implementierungsfehler, sondern Gegenstand einer
              Rueckfrage (§1). Siehe OFFENE_FRAGEN.md.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

ERROR = "ERROR"
NOTICE = "NOTICE"


@dataclass(frozen=True)
class Finding:
    severity: str
    rule: str
    spec_section: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule} ({self.spec_section}): {self.message}"


# --------------------------------------------------------------------- Regeln


def rule_calibration_status(conn: sqlite3.Connection) -> list[Finding]:
    """§6: Alle im MVP erstellten Aufgaben sind UNCALIBRATED_MVP_ITEM."""
    rows = conn.execute(
        "SELECT task_id, calibration_status FROM tasks"
        " WHERE calibration_status <> 'UNCALIBRATED_MVP_ITEM'"
    ).fetchall()
    return [
        Finding(ERROR, "calibration_status", "§6",
                f"{r['task_id']} hat calibration_status {r['calibration_status']};"
                " in V1 ist nur UNCALIBRATED_MVP_ITEM zulaessig")
        for r in rows
    ]


def rule_relation_evidence(conn: sqlite3.Connection) -> list[Finding]:
    """§114: keine Relation ohne relation_type und evidence_status.
    Zusatz: A oder B nur mit einer Quelle, die amtlich oder empirisch ist."""
    out: list[Finding] = []
    rows = conn.execute(
        "SELECT r.relation_id, r.evidence_status, r.source_id, s.source_type"
        " FROM relations r LEFT JOIN sources s ON s.source_id = r.source_id"
    ).fetchall()
    for r in rows:
        if r["evidence_status"] in ("A", "B"):
            if r["source_type"] not in ("OFFICIAL_STANDARD", "EMPIRICAL_RESEARCH"):
                out.append(Finding(
                    ERROR, "relation_evidence", "§114",
                    f"{r['relation_id']} traegt evidence_status {r['evidence_status']},"
                    f" die Quelle ist aber {r['source_type'] or 'nicht gesetzt'}."
                    " Ohne belastbare Quelle nur C oder D"))
    return out


def rule_llm_not_in_decision_path(conn: sqlite3.Connection) -> list[Finding]:
    """§75/§76: Das LLM darf nicht die zentrale Routing-Engine sein."""
    row = conn.execute(
        "SELECT value FROM system_config WHERE config_key = 'routing.llm_in_decision_path'"
    ).fetchone()
    if row is None:
        return [Finding(ERROR, "llm_guard", "§75",
                        "Konfigurationsschluessel routing.llm_in_decision_path fehlt")]
    if row["value"] != "false":
        return [Finding(ERROR, "llm_guard", "§75",
                        f"routing.llm_in_decision_path = {row['value']}; in V1 muss false gelten")]
    return []


def rule_time_not_used_for_inference(conn: sqlite3.Connection) -> list[Finding]:
    """§62: Bearbeitungszeit ist Kontextinformation, kein Kompetenzindikator."""
    row = conn.execute(
        "SELECT value FROM system_config"
        " WHERE config_key = 'evidence.time_seconds_used_for_inference'"
    ).fetchone()
    if row is None or row["value"] != "false":
        return [Finding(ERROR, "time_guard", "§62",
                        "evidence.time_seconds_used_for_inference muss in V1 false sein")]
    return []


def rule_error_codes_observation_only(conn: sqlite3.Connection) -> list[Finding]:
    """§59: Fehlercodes beschreiben Beobachtungen, keine Diagnosen."""
    rows = conn.execute(
        "SELECT error_code FROM error_codes WHERE is_observation_only <> 1"
    ).fetchall()
    return [Finding(ERROR, "error_code_observation", "§59",
                    f"{r['error_code']} ist nicht als reine Beobachtung markiert")
            for r in rows]


def rule_prerequisite_graph_acyclic(conn: sqlite3.Connection) -> list[Finding]:
    """§11/§36: Voraussetzungskanten muessen rueckwaerts navigierbar sein.
    Ein Zyklus aus HARD_ oder STRONG_PREREQUISITE macht die Rueckwaertssuche
    aus §36 unentscheidbar."""
    edges: dict[str, list[str]] = {}
    for r in conn.execute(
        "SELECT source_competency AS s, target_competency AS t FROM relations"
        " WHERE relation_type IN ('HARD_PREREQUISITE', 'STRONG_PREREQUISITE')"
    ):
        edges.setdefault(r["s"], []).append(r["t"])

    state: dict[str, int] = {}
    out: list[Finding] = []

    def visit(node: str, path: list[str]) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            cycle = " -> ".join(path[path.index(node):] + [node])
            out.append(Finding(ERROR, "prerequisite_cycle", "§11, §36",
                               f"Zyklus im Voraussetzungsgraphen: {cycle}"))
            return
        state[node] = 1
        for nxt in edges.get(node, []):
            visit(nxt, path + [node])
        state[node] = 2

    for node in list(edges):
        visit(node, [])
    return out


def rule_parallel_item_symmetry(conn: sqlite3.Connection) -> list[Finding]:
    """§25: Ein Parallelitem muss Struktur, Darstellung und Schwierigkeit
    konstant halten. §116 Grundsatz der minimalen Veraenderung."""
    out: list[Finding] = []
    rows = conn.execute(
        "SELECT a.task_id AS a_id, a.internal_difficulty AS a_d,"
        " a.representation_mode AS a_r, a.interaction_mode AS a_i,"
        " b.task_id AS b_id, b.internal_difficulty AS b_d,"
        " b.representation_mode AS b_r, b.interaction_mode AS b_i"
        " FROM tasks a JOIN tasks b ON b.task_id = a.parallel_item_id"
    ).fetchall()
    for r in rows:
        diffs = []
        if r["a_d"] != r["b_d"]:
            diffs.append(f"Schwierigkeit {r['a_d']} vs {r['b_d']}")
        if r["a_r"] != r["b_r"]:
            diffs.append(f"Darstellung {r['a_r']} vs {r['b_r']}")
        if r["a_i"] != r["b_i"]:
            diffs.append(f"Bedienform {r['a_i']} vs {r['b_i']}")
        if diffs:
            out.append(Finding(ERROR, "parallel_item_minimal_change", "§25, §116",
                               f"{r['a_id']} -> {r['b_id']}: " + ", ".join(diffs)))
    return out


def rule_parallel_family_homogeneous(conn: sqlite3.Connection) -> list[Finding]:
    """§116 innerhalb einer PARALLEL_ITEM-Familie."""
    out: list[Finding] = []
    rows = conn.execute(
        "SELECT f.task_family_id,"
        " COUNT(DISTINCT t.internal_difficulty) AS n_diff,"
        " COUNT(DISTINCT t.representation_mode) AS n_repr,"
        " COUNT(*) AS n"
        " FROM task_families f JOIN tasks t ON t.task_family_id = f.task_family_id"
        " WHERE f.family_type = 'PARALLEL_ITEM' GROUP BY f.task_family_id"
    ).fetchall()
    for r in rows:
        if r["n_diff"] > 1 or r["n_repr"] > 1:
            out.append(Finding(ERROR, "parallel_family_homogeneous", "§25, §116",
                               f"{r['task_family_id']}: {r['n_diff']} Schwierigkeitsstufen"
                               f" und {r['n_repr']} Darstellungsformen in einer"
                               " PARALLEL_ITEM-Familie"))
    return out


def rule_family_size(conn: sqlite3.Connection) -> list[Finding]:
    """§58: eine Familie ohne Vergleichspartner hat keinen Zweck."""
    rows = conn.execute(
        "SELECT f.task_family_id, COUNT(t.task_id) AS n FROM task_families f"
        " LEFT JOIN tasks t ON t.task_family_id = f.task_family_id"
        " GROUP BY f.task_family_id HAVING n < 2"
    ).fetchall()
    return [Finding(ERROR, "family_size", "§58",
                    f"{r['task_family_id']} hat {r['n']} Item(s); ein Vergleich braucht zwei")
            for r in rows]


def rule_route_targets(conn: sqlite3.Connection) -> list[Finding]:
    """§83/§84: jede Route braucht ein Ziel und darf nicht auf sich selbst zeigen."""
    out: list[Finding] = []
    for r in conn.execute("SELECT route_id, source_task, target_task FROM task_routes"):
        if r["target_task"] == r["source_task"]:
            out.append(Finding(ERROR, "route_self_reference", "§83",
                               f"{r['route_id']} zeigt auf die Ausgangsaufgabe zurueck"))
    return out


def rule_hypothesis_falsifiable(conn: sqlite3.Connection) -> list[Finding]:
    """§115: eine Hypothese muss durch eine Aufgabe widerlegbar sein.
    In Sprint 1-3 noch ohne Daten; die Regel sichert das Schema ab."""
    row = conn.execute(
        "SELECT value FROM system_config"
        " WHERE config_key = 'hypothesis.require_falsifying_task'"
    ).fetchone()
    if row is None or row["value"] != "true":
        return [Finding(ERROR, "falsifiability", "§115",
                        "hypothesis.require_falsifying_task muss true sein")]
    rows = conn.execute(
        "SELECT hypothesis_id FROM student_hypotheses WHERE falsifying_task IS NULL"
    ).fetchall()
    return [Finding(ERROR, "falsifiability", "§115",
                    f"Hypothese {r['hypothesis_id']} ohne widerlegendes Item")
            for r in rows]


# ------------------------------------------------------- Hinweise (NOTICE)


def rule_tasks_deliverable(conn: sqlite3.Connection) -> list[Finding]:
    """§113: jede Aufgabe braucht correct_answer und, bei Auswahlaufgaben,
    Optionen.

    War in Version 1.0 ein Hinweis, weil §42-57 fuer 13 Items keine
    Distraktoren nennen (F-17) und fuer ZO05-D4-S-A keine Antwortmenge (F-18).
    Beide sind mit den Entscheidungen D-09 und D-10 geschlossen; seither ist ein
    unvollstaendiges Item ein Fehler und kein Befund ueber die Spezifikation.
    """
    out: list[Finding] = []
    for r in conn.execute("SELECT task_id, task_payload, correct_answer FROM tasks"):
        payload = json.loads(r["task_payload"])
        answer = json.loads(r["correct_answer"])
        if payload.get("options_status") == "UNDEFINED":
            out.append(Finding(ERROR, "options_undefined", "§113",
                               f"{r['task_id']}: Auswahlaufgabe ohne Distraktoren"))
        if isinstance(answer, dict) and answer.get("status") == "UNDEFINED":
            out.append(Finding(ERROR, "answer_undefined", "§113",
                               f"{r['task_id']}: akzeptierte Antworten nicht festgelegt"))
        if payload.get("options") and not payload.get("options_status"):
            out.append(Finding(ERROR, "options_status_missing", "§113",
                               f"{r['task_id']}: Optionen ohne options_status -"
                               " die Herkunft der Distraktoren muss dokumentiert sein"))
    return out


def notice_undefined_config(conn: sqlite3.Connection) -> list[Finding]:
    rows = conn.execute(
        "SELECT config_key, spec_section FROM system_config WHERE value IS NULL"
    ).fetchall()
    return [Finding(NOTICE, "config_undefined", r["spec_section"] or "§1",
                    f"{r['config_key']} ist UNDEFINED")
            for r in rows]


def notice_competencies_without_items(conn: sqlite3.Connection) -> list[Finding]:
    """§10 verlangt die Knoten, §42-57 liefern nicht fuer alle Items."""
    rows = conn.execute(
        "SELECT c.competency_id FROM competencies c"
        " LEFT JOIN tasks t ON t.primary_competency = c.competency_id"
        " WHERE c.is_mvp = 1 AND t.task_id IS NULL"
        " GROUP BY c.competency_id ORDER BY c.competency_id"
    ).fetchall()
    if not rows:
        return []
    ids = ", ".join(r["competency_id"] for r in rows)
    return [Finding(NOTICE, "competency_without_items", "§10, §58",
                    f"{len(rows)} MVP-Kompetenzknoten ohne eigenes Item: {ids}")]


def notice_missing_descriptions(conn: sqlite3.Connection) -> list[Finding]:
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM competencies WHERE description IS NULL"
    ).fetchone()["n"]
    if not n:
        return []
    return [Finding(NOTICE, "competency_description", "§10 / F-01",
                    f"{n} Kompetenzknoten ohne Beschreibung -"
                    " §10 listet die Knoten ohne fachliche Definition")]


def notice_relation_coverage(conn: sqlite3.Connection) -> list[Finding]:
    """Wie viele Kompetenzknoten haengen ueberhaupt im Relationsgraphen?"""
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM competencies WHERE is_mvp = 1"
    ).fetchone()["n"]
    # Gezaehlt wird dieselbe Menge, von der die Rede ist. Ohne die zweite
    # Bedingung stammte "connected" aus allen Knoten und "total" nur aus den
    # MVP-Knoten; seit content/klassen5bis10/ dazugekommen ist, stand da
    # "72 von 50".
    connected = conn.execute(
        "SELECT COUNT(DISTINCT cid) AS n FROM ("
        " SELECT source_competency AS cid FROM relations"
        " UNION SELECT target_competency AS cid FROM relations)"
        " WHERE cid IN (SELECT competency_id FROM competencies WHERE is_mvp = 1)"
    ).fetchone()["n"]
    return [Finding(NOTICE, "relation_coverage", "§10, §11",
                    f"{connected} von {total} MVP-Knoten haengen im Relationsgraphen."
                    " §10 gibt keine Kantenliste an (§11: kein linearer Baum); die"
                    " Kanten sind unter Entscheidung D-12 autorisiert und tragen nach"
                    " §114 hoechstens evidence_status C oder D")]


def notice_no_successor_relations(conn: sqlite3.Connection) -> list[Finding]:
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM relations WHERE relation_type = 'SUCCESSOR'"
    ).fetchone()["n"]
    if n:
        return []
    return [Finding(NOTICE, "successor_missing", "§12 / F-05",
                    "Keine SUCCESSOR-Relation vorhanden. §12 fuehrt den Typ,"
                    " die Spezifikation behauptet aber keine konkrete"
                    " Nachfolgerbeziehung")]


def rule_representation_route_confound(conn: sqlite3.Connection) -> list[Finding]:
    """§116: Eine Route mit reason CHANGE_REPRESENTATION soll nur die
    Darstellung wechseln. Wechselt sie gleichzeitig die Schwierigkeit oder
    die Frageform, ist ein Unterschied nicht mehr der Darstellung
    zuzuordnen - genau davor warnt §32."""
    out: list[Finding] = []
    rows = conn.execute(
        "SELECT r.route_id, a.task_id AS a_id, b.task_id AS b_id,"
        " a.internal_difficulty AS a_d, b.internal_difficulty AS b_d,"
        " a.scoring_rule AS a_s, b.scoring_rule AS b_s,"
        " a.question_form AS a_q, b.question_form AS b_q"
        " FROM task_routes r"
        " JOIN tasks a ON a.task_id = r.source_task"
        " JOIN tasks b ON b.task_id = r.target_task"
        " WHERE r.reason = 'CHANGE_REPRESENTATION'"
    ).fetchall()
    for r in rows:
        diffs = []
        if r["a_d"] != r["b_d"]:
            diffs.append(f"Schwierigkeit {r['a_d']} -> {r['b_d']}")
        if r["a_s"] != r["b_s"]:
            diffs.append(f"Antwortformat {r['a_s']} -> {r['b_s']}")
        if r["a_q"] != r["b_q"]:
            diffs.append(f"Frageform {r['a_q']} -> {r['b_q']}")
        if diffs:
            out.append(Finding(
                ERROR, "representation_route_confound", "§116, §32",
                f"{r['route_id']} ({r['a_id']} -> {r['b_id']}) wechselt neben der"
                f" Darstellung auch: {', '.join(diffs)}. §32 verbietet, aus einem"
                " so entstandenen Unterschied auf die Darstellung zu schliessen."))
    return out


def notice_representation_family_confound(conn: sqlite3.Connection) -> list[Finding]:
    """§116 innerhalb einer REPRESENTATION_VARIATION-Familie: ausser der
    Darstellung soll nichts variieren."""
    out: list[Finding] = []
    rows = conn.execute(
        "SELECT f.task_family_id,"
        " COUNT(DISTINCT t.internal_difficulty) AS n_diff,"
        " COUNT(DISTINCT t.interaction_mode) AS n_inter,"
        " COUNT(DISTINCT t.scoring_rule) AS n_scoring"
        " FROM task_families f JOIN tasks t ON t.task_family_id = f.task_family_id"
        " WHERE f.family_type = 'REPRESENTATION_VARIATION' GROUP BY f.task_family_id"
    ).fetchall()
    for r in rows:
        varied = []
        if r["n_diff"] > 1:
            varied.append("Schwierigkeit")
        if r["n_inter"] > 1:
            varied.append("Bedienform")
        if r["n_scoring"] > 1:
            varied.append("Antwortformat")
        if varied:
            out.append(Finding(
                NOTICE, "representation_family_confound", "§116, §17 / F-13, F-21",
                f"{r['task_family_id']} variiert neben der Darstellung auch:"
                f" {', '.join(varied)}"))
    return out


ERROR_RULES = (
    rule_calibration_status,
    rule_tasks_deliverable,
    rule_representation_route_confound,
    rule_relation_evidence,
    rule_llm_not_in_decision_path,
    rule_time_not_used_for_inference,
    rule_error_codes_observation_only,
    rule_prerequisite_graph_acyclic,
    rule_parallel_item_symmetry,
    rule_parallel_family_homogeneous,
    rule_family_size,
    rule_route_targets,
    rule_hypothesis_falsifiable,
)

NOTICE_RULES = (
    notice_undefined_config,
    notice_competencies_without_items,
    notice_missing_descriptions,
    notice_relation_coverage,
    notice_no_successor_relations,
    notice_representation_family_confound,
)


def run_all(conn: sqlite3.Connection) -> list[Finding]:
    findings: list[Finding] = []
    for rule in ERROR_RULES + NOTICE_RULES:
        findings.extend(rule(conn))
    return findings


def errors(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == ERROR]
