"""Datenvertrag fuer die Oberflaeche.

Die UI-Spezifikation verlangt eine strikte Trennung: das Frontend stellt dar,
das Backend entscheidet. Dieses Modul ist die Naht dazwischen. Es liefert genau
die fuenfzehn Objekte, die die Spezifikation nennt - StudentProfile,
CompetencyNode, CompetencyState, Evidence, Observation, ErrorObservation,
ErrorPattern, Task, TaskFeature, RepresentationEvidence,
ProcessCompetencyEvidence, Hypothesis, HypothesisEvidence, HypothesisTest,
RoutingDecision - und nichts, was das Frontend selbst ausrechnen muesste.

Der Entwicklungsmodus der UI-Spezifikation ("falls noch keine Backend-Endpunkte
verfuegbar sind: Mock-Daten hinter einer Datenzugriffsschicht") entfaellt. Das
Backend existiert. Mock-Daten waeren hier nicht nur ueberfluessig, sondern
gefaehrlich: jeder erfundene Statuswert waere eine fachliche Entscheidung, und
§1 der Fachspezifikation verbietet sie ebenso wie der Implementierungsauftrag.

Drei Ableitungen macht dieses Modul, und alle drei stuetzen sich auf Regeln, die
im Backend bereits stehen - keine davon ist neu erfunden:

1. ``resource_class`` gruppiert den Kompetenzstatus in Ressource, offener
   Bereich und ungeprueft. Die Zuordnung kommt aus ``park.enter_status``
   (§38) und der Statussemantik aus §63; sie steht hier, damit sie nicht im
   Frontend steht.
2. ``reproduced`` an einem Fehlermuster nutzt ``mastery.failure_replication_
   required`` (§30, §41) - denselben Schwellenwert, den auch das Routing fuer
   die Replikationsentscheidung verwendet.
3. ``missing_evidence`` an einer Hypothese ist die Aufgabe aus
   ``falsifying_task``, solange sie noch nicht bearbeitet wurde. §115 verlangt
   fuer jede Hypothese genau diese Aufgabe; was fehlt, ist damit benannt und
   nicht geschaetzt.

Was dieses Modul ausdruecklich NICHT liefert, weil die Fachspezifikation es
verbietet: einen Gesamtscore (§117), Prozentwerte (§117), Klassenstufen-
aequivalente (§94) und jede Zuschreibung einer Eigenschaft (§32).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from . import hypotheses as hypo
from .attempts import attempt_history
from .clock import Clock
from .config import Config
from .state import facets_of, variation_dimensions
from .teacher import STATUS_LABEL

#: Evidenztypen, die in die Statusberechnung eingehen (§28). Die UI zeigt das
#: Feld, damit sichtbar bleibt, dass nicht jede Evidenzzeile den Status bewegt -
#: die Spezifikation verlangt in der Debug-Ansicht ausdruecklich, erkennbar zu
#: machen, "welche Daten aktuell nicht relevant waren".
SCORED_EVIDENCE_TYPES = ("DIRECT_POSITIVE", "DIRECT_NEGATIVE",
                         "INDIRECT_POSITIVE", "INDIRECT_NEGATIVE")

#: §115: Status, in denen eine Hypothese noch geprueft wird. REJECTED und
#: CLOSED sind erledigt - ihre Kontrollaufgabe waere keine offene Pruefung
#: mehr, auch wenn sie unbearbeitet in der Zeile steht.
ACTIVE_HYPOTHESIS_STATUS = ("OPEN", "SUPPORTED", "WEAKENED")

#: §63 Statussemantik, gruppiert fuer die Darstellung nach dem Abschnitt
#: "Ressourcen und Schwierigkeiten" der UI-Spezifikation. UNKNOWN ist
#: ausdruecklich ein gueltiger Zustand und kein Defizit.
RESOURCE_CLASS_LABEL = {
    "RESOURCE": "durch Evidenz stabil gezeigt",
    "OPEN": "offener oder schwieriger Bereich",
    "UNCHECKED": "noch nicht ausreichend geprüft",
}


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params)]


def _json(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value) if isinstance(value, str) else value


# ------------------------------------------------------------- Vokabular


def vocabulary(conn: sqlite3.Connection) -> dict[str, dict]:
    """Alle kontrollierten Vokabulare mit deutschen Labels (§108).

    Die UI beschriftet ausschliesslich hieraus - Begriffe wie Ueberschriften.
    Ohne das muesste sie eigene Uebersetzungen mitbringen, und jede davon waere
    eine fachliche Festlegung ausserhalb des Contents. Die Beschreibung aus der
    Vokabeltabelle wandert mit, weil sie an mehreren Stellen die
    entscheidende Einschraenkung traegt: dass D1-D5 nicht die IQB-Stufen sind
    (§6), dass Profilmarker keine Diagnosen sind (§26), dass SECURE nicht
    "dauerhaft beherrscht" heisst (§27).
    """
    out: dict[str, dict] = {}
    for row in conn.execute(
        "SELECT vocabulary, vocabulary_kind, spec_section, description FROM vocabularies"
    ):
        out[row["vocabulary"]] = {
            "kind": row["vocabulary_kind"],
            "spec_section": row["spec_section"],
            "description": row["description"],
            "terms": {},
        }
    for row in conn.execute(
        "SELECT vocabulary, term, label_de, notes FROM vocabulary_terms"
        " ORDER BY vocabulary, term"
    ):
        entry = out.setdefault(row["vocabulary"], {
            "kind": None, "spec_section": None, "description": None, "terms": {}})
        entry["terms"][row["term"]] = {
            "label": row["label_de"] or row["term"],
            "notes": row["notes"],
        }
    return out


def _resource_class_map(cfg: Config) -> dict[str, str]:
    """Statusgruppierung. ``park.enter_status`` sagt, aus welchem Status heraus
    geparkt wird (§38) - geparkt ist also gezeigtes Koennen, nicht Abwesenheit
    von Information."""
    zuordnung = {
        "PARKED": "RESOURCE",
        "SUPPORT_FOCUS": "OPEN",
        "UNCERTAIN": "OPEN",
        "UNKNOWN": "UNCHECKED",
        "ACTIVE": "UNCHECKED",
        "REACTIVATED": "UNCHECKED",
        "BLOCKED": "UNCHECKED",
    }
    # Zuletzt und damit ueberschreibend: der konfigurierte Status gewinnt. In
    # einem Literal stuende er vor den festen Eintraegen und wuerde von ihnen
    # verdraengt - die Konfiguration waere dann wirkungslos, sobald sie auf
    # einen der genannten Werte zeigt. Entscheidung D-36.
    zuordnung[cfg.require("park.enter_status")] = "RESOURCE"
    return zuordnung


# --------------------------------------------------- Graph und Aufgabenbank


def competency_nodes(conn: sqlite3.Connection) -> list[dict]:
    """CompetencyNode. Der Graph aus §7, §9, §10."""
    prereq = {}
    dependents = {}
    for row in conn.execute(
        "SELECT relation_id, source_competency, target_competency, relation_type"
        " FROM relations"
    ):
        dependents.setdefault(row["source_competency"], []).append(row["target_competency"])
        prereq.setdefault(row["target_competency"], []).append(row["source_competency"])

    out = []
    for row in conn.execute(
        "SELECT competency_id, name, description, domain, leitidee, parent_id,"
        " is_mvp, evidence_status, spec_section, grade_reference_min, grade_reference_max"
        " FROM competencies ORDER BY competency_id"
    ):
        node = dict(row)
        node["is_mvp"] = bool(node["is_mvp"])
        # "Basiskompetenzen" der UI-Spezifikation: die Voraussetzungen dieses
        # Knotens, direkt aus dem Graphen (§12/§13) - keine eigene Herleitung.
        node["prerequisites"] = sorted(set(prereq.get(row["competency_id"], [])))
        node["dependents"] = sorted(set(dependents.get(row["competency_id"], [])))
        out.append(node)
    return out


def relations(conn: sqlite3.Connection) -> list[dict]:
    return _rows(conn,
                 "SELECT relation_id, source_competency, target_competency, relation_type,"
                 " strength, evidence_status, bidirectional, notes, spec_section"
                 " FROM relations ORDER BY relation_id")


def tasks(conn: sqlite3.Connection) -> list[dict]:
    """Task inklusive TaskFeature. Die Merkmale sind nach Art gruppiert, weil
    §15 und §112 vier verbindliche Merkmalsfelder nennen und die UI sie
    getrennt zeigen muss."""
    features: dict[str, dict[str, list[str]]] = {}
    for row in conn.execute(
        "SELECT task_id, feature_kind, feature_value FROM task_features"
        " ORDER BY task_id, feature_kind, feature_value"
    ):
        features.setdefault(row["task_id"], {}).setdefault(
            row["feature_kind"], []).append(row["feature_value"])

    out = []
    for row in conn.execute(
        "SELECT task_id, task_family_id, title, primary_competency, secondary_competencies,"
        " primary_leitidee, secondary_leitideen, process_competencies, prerequisites,"
        " internal_difficulty, calibration_status, representation_mode, interaction_mode,"
        " question_form, language_demand, task_prompt, scoring_rule, task_purpose,"
        " parallel_item_id, estimated_time_seconds, spec_section"
        " FROM tasks ORDER BY task_id"
    ):
        task = dict(row)
        for field in ("secondary_competencies", "secondary_leitideen",
                      "process_competencies", "prerequisites"):
            task[field] = _json(task[field], [])
        task["features"] = features.get(row["task_id"], {})
        out.append(task)
    return out


def error_codes(conn: sqlite3.Connection) -> list[dict]:
    return _rows(conn, "SELECT error_code, label_de, description, is_observation_only,"
                       " spec_section FROM error_codes ORDER BY error_code")


# ------------------------------------------------------------ Schuelerdaten


def observations(conn: sqlite3.Connection, student_id: str) -> list[dict]:
    """Observation - die Rohbeobachtung aus §60, Ebene 1 von §66.

    Die Antwort wird unveraendert mitgeliefert (§66: "Rohantwort unveraendert"),
    die Bearbeitungszeit ebenfalls (§60) - mit dem ausdruecklichen Vermerk aus
    §62, dass sie kein Kompetenzindikator ist.
    """
    events = {r["attempt_id"]: r["n"] for r in conn.execute(
        "SELECT attempt_id, COUNT(*) AS n FROM interaction_events GROUP BY attempt_id")}
    out = []
    for row in conn.execute(
        "SELECT a.*, t.primary_competency, t.internal_difficulty, t.representation_mode,"
        " t.question_form, t.task_purpose, t.title"
        " FROM task_attempts a JOIN tasks t ON t.task_id = a.task_id"
        " WHERE a.student_id = ? ORDER BY a.started_at, a.attempt_id", (student_id,)
    ):
        obs = dict(row)
        obs["is_correct"] = bool(obs["is_correct"])
        obs["support_used"] = bool(obs["support_used"])
        obs["answer"] = _json(obs["answer"], None)
        obs["interaction_event_count"] = events.get(row["attempt_id"], 0)
        out.append(obs)
    return out


def error_observations(conn: sqlite3.Connection, student_id: str) -> list[dict]:
    """ErrorObservation. §59: ein Fehlercode ist eine Beobachtung, nie eine
    Diagnose - das Schemafeld ``is_observation_only`` haelt das fest und wird
    mitgeliefert, damit die UI es anzeigen kann."""
    return _rows(conn,
                 "SELECT e.attempt_id, e.error_code, e.detail, a.task_id, a.started_at,"
                 " t.primary_competency, t.internal_difficulty, t.representation_mode,"
                 " c.label_de, c.description, c.is_observation_only"
                 " FROM attempt_error_codes e"
                 " JOIN task_attempts a ON a.attempt_id = e.attempt_id"
                 " JOIN tasks t ON t.task_id = a.task_id"
                 " JOIN error_codes c ON c.error_code = e.error_code"
                 " WHERE a.student_id = ? ORDER BY a.started_at, e.attempt_id, e.error_code",
                 (student_id,))


def error_patterns(conn: sqlite3.Connection, student_id: str, cfg: Config) -> list[dict]:
    """ErrorPattern - aus Beobachtungen verdichtet, ohne sie zu deuten.

    ``reproduced`` nutzt ``mastery.failure_replication_required`` (§30, §41),
    denselben Schwellenwert, den das Routing fuer die Replikationsentscheidung
    verwendet. Gezaehlt wird je Fehlercode UND Kompetenz - das ist die
    Zaehlweise der Engine, nicht eine eigene.

    Ein reproduziertes Muster bleibt ein Muster. §59 und das Beispiel der
    UI-Spezifikation sind hier deckungsgleich: ein wiederholter Fehler beim
    Zehneruebergang darf als Fehlermuster erscheinen, aber nicht als
    "Stellenwertdefizit". Deshalb traegt jedes Muster die konkurrierenden
    Hypothesen bei sich, statt eine Ursache zu behaupten.
    """
    required = int(cfg.require("mastery.failure_replication_required"))
    grouped: dict[tuple[str, str], dict] = {}

    for row in conn.execute(
        "SELECT e.error_code, e.attempt_id, a.task_id, t.primary_competency,"
        " t.representation_mode, t.internal_difficulty, t.question_form,"
        " c.label_de, c.description, c.spec_section"
        " FROM attempt_error_codes e"
        " JOIN task_attempts a ON a.attempt_id = e.attempt_id"
        " JOIN tasks t ON t.task_id = a.task_id"
        " JOIN error_codes c ON c.error_code = e.error_code"
        " WHERE a.student_id = ? ORDER BY e.error_code, a.started_at", (student_id,)
    ):
        key = (row["error_code"], row["primary_competency"])
        entry = grouped.setdefault(key, {
            "error_code": row["error_code"],
            "label": row["label_de"],
            "description": row["description"],
            "spec_section": row["spec_section"],
            "competency_id": row["primary_competency"],
            "attempts": [],
            "tasks": [],
            "representations": [],
            "difficulties": [],
            "question_forms": [],
        })
        entry["attempts"].append(row["attempt_id"])
        for field, column in (("tasks", "task_id"), ("representations", "representation_mode"),
                              ("difficulties", "internal_difficulty"),
                              ("question_forms", "question_form")):
            if row[column] and row[column] not in entry[field]:
                entry[field].append(row[column])

    # Merkmale und Zusatzanforderungen der betroffenen Aufgaben (§15, §112).
    open_hyp = hypo.open_hypotheses(conn, student_id)
    out = []
    for entry in grouped.values():
        entry["observation_count"] = len(entry["attempts"])
        entry["replication_threshold"] = required
        entry["reproduced"] = len(set(entry["attempts"])) >= required
        entry["features"] = _features_of_tasks(conn, entry["tasks"])
        entry["additional_demands"] = entry["features"].get("ADDITIONAL_DEMAND", [])
        # Konkurrierende Hypothesen: alle offenen Hypothesen zur selben
        # Kompetenz. Welche zutrifft, entscheidet das Backend ueber Evidenz -
        # die UI zeigt sie nebeneinander, wie die Spezifikation verlangt.
        entry["candidate_hypotheses"] = [
            h["hypothesis_id"] for h in open_hyp
            if h["target_construct"].split(":", 1)[0] == entry["competency_id"]
        ]
        out.append(entry)

    out.sort(key=lambda e: (-e["observation_count"], e["error_code"]))
    return out


def _features_of_tasks(conn: sqlite3.Connection, task_ids: list[str]) -> dict[str, list[str]]:
    if not task_ids:
        return {}
    placeholders = ",".join("?" * len(task_ids))
    out: dict[str, list[str]] = {}
    for row in conn.execute(
        f"SELECT DISTINCT feature_kind, feature_value FROM task_features"
        f" WHERE task_id IN ({placeholders}) ORDER BY feature_kind, feature_value",
        tuple(task_ids),
    ):
        out.setdefault(row["feature_kind"], []).append(row["feature_value"])
    return out


def evidence(conn: sqlite3.Connection, student_id: str) -> list[dict]:
    """Evidence - Ebene 2 von §66.

    ``is_scored`` macht sichtbar, welche Zeilen den Status bewegen und welche
    nur Facetten und Hypothesen tragen. Die UI-Spezifikation verlangt in der
    Debug-Ansicht genau diese Unterscheidung.
    """
    out = []
    for row in conn.execute(
        "SELECT e.*, t.internal_difficulty, t.representation_mode, t.question_form"
        " FROM evidence_events e LEFT JOIN tasks t ON t.task_id = e.source_task"
        " WHERE e.student_id = ? ORDER BY e.created_at, e.evidence_id", (student_id,)
    ):
        item = dict(row)
        item["is_scored"] = item["evidence_type"] in SCORED_EVIDENCE_TYPES
        out.append(item)
    return out


def competency_states(conn: sqlite3.Connection, student_id: str, cfg: Config) -> list[dict]:
    """CompetencyState, aufgeschluesselt nach Facetten (§117/§118).

    §117 verbietet den Prozentwert. Geliefert werden Zaehlungen und
    Facettenstatus - das ist etwas anderes als eine Quote, weil es die
    Bedingungen mitnennt. Die UI bildet daraus ebenfalls keinen Anteil.
    """
    classes = _resource_class_map(cfg)
    out = []
    for row in conn.execute(
        "SELECT s.*, c.name, c.leitidee FROM student_competency_state s"
        " JOIN competencies c ON c.competency_id = s.competency_id"
        " WHERE s.student_id = ? ORDER BY s.competency_id", (student_id,)
    ):
        competency_id = row["competency_id"]
        history = attempt_history(conn, student_id, competency_id)
        state = dict(row)
        state["profile_markers"] = _json(state["profile_markers"], [])
        state["status_label"] = STATUS_LABEL.get(row["status"], row["status"])
        state["resource_class"] = classes.get(row["status"], "UNCHECKED")
        state["resource_class_label"] = RESOURCE_CLASS_LABEL[state["resource_class"]]
        state["observation_counts"] = {
            "correct": sum(1 for h in history if h["is_correct"]),
            "incorrect": sum(1 for h in history if not h["is_correct"]),
        }
        state["variation_dimensions"] = variation_dimensions(history)
        # Facetten tragen dieselbe Gruppierung wie der Knoten selbst. Sie hier
        # zu setzen und nicht im Frontend ist der Unterschied zwischen einer
        # Darstellungsregel und einer fachlichen: welcher Facettenstatus als
        # Ressource gilt, entscheidet §38/§63 - einmal, an einer Stelle.
        state["facets"] = {
            kind: [
                {"value": value,
                 "status_label": STATUS_LABEL.get(entry["status"], entry["status"]),
                 "resource_class": classes.get(entry["status"], "UNCHECKED"),
                 **{k: entry[k] for k in
                    ("status", "positive_count", "negative_count",
                     "consistency", "last_evidence")}}
                for value, entry in sorted(values.items())
            ]
            for kind, values in facets_of(conn, student_id, competency_id).items()
        }
        out.append(state)
    return out


def representation_evidence(conn: sqlite3.Connection, student_id: str,
                            cfg: Config) -> list[dict]:
    """RepresentationEvidence - die EIS-Sicht (§16).

    Nicht neu berechnet: es sind die Facetten der Art REPRESENTATION_MODE, die
    ``state.recompute`` ohnehin fuehrt, plus die Zaehlung der Beobachtungen je
    Darstellung. Die UI zeigt damit, unter welcher Darstellung was beobachtet
    wurde - nicht, welcher "Lerntyp" jemand sei (§32).

    Dass die EIS-Sicht genau die Facetten dieser Art sind, ist eine fachliche
    Festlegung und steht deshalb hier. ``status_label`` und ``resource_class``
    kommen aus derselben Quelle wie bei ``competency_states``; ohne sie muesste
    die Oberflaeche die Zeilen selbst aus den Zustaenden zusammensuchen - und
    genau das hat sie vorher getan, waehrend dieses Objekt ungelesen blieb.
    """
    classes = _resource_class_map(cfg)
    out = []
    for row in conn.execute(
        "SELECT f.*, c.name FROM student_competency_facets f"
        " JOIN competencies c ON c.competency_id = f.competency_id"
        " WHERE f.student_id = ? AND f.facet_kind = 'REPRESENTATION_MODE'"
        " ORDER BY f.competency_id, f.facet_value", (student_id,)
    ):
        item = dict(row)
        item["status_label"] = STATUS_LABEL.get(item["status"], item["status"])
        item["resource_class"] = classes.get(item["status"], "UNCHECKED")
        out.append(item)
    return out


def process_competency_evidence(conn: sqlite3.Connection, student_id: str) -> list[dict]:
    """ProcessCompetencyEvidence - §8 Prozesskompetenzen.

    Das Backend fuehrt fuer Prozesskompetenzen keinen eigenen Zustand; sie
    stehen als Aufgabeneigenschaft in ``tasks.process_competencies``. Geliefert
    wird deshalb die Beobachtungszaehlung je Prozesskompetenz und nichts
    darueber hinaus. Einen Status daraus abzuleiten waere eine neue fachliche
    Regel - genau das, was der Auftrag untersagt.
    """
    tally: dict[str, dict] = {}
    for row in conn.execute(
        "SELECT a.attempt_id, a.is_correct, t.process_competencies, t.task_id"
        " FROM task_attempts a JOIN tasks t ON t.task_id = a.task_id"
        " WHERE a.student_id = ?", (student_id,)
    ):
        for competency in _json(row["process_competencies"], []):
            entry = tally.setdefault(competency, {
                "process_competency": competency,
                "observed_correct": 0, "observed_incorrect": 0, "tasks": [],
                "note": "Zählung von Beobachtungen. Das Backend führt für "
                        "Prozesskompetenzen keinen Kompetenzstatus (§8).",
            })
            entry["observed_correct" if row["is_correct"] else "observed_incorrect"] += 1
            if row["task_id"] not in entry["tasks"]:
                entry["tasks"].append(row["task_id"])
    return sorted(tally.values(), key=lambda e: e["process_competency"])


def hypotheses_view(conn: sqlite3.Connection, student_id: str) -> list[dict]:
    """Hypothesis samt HypothesisEvidence und HypothesisTest.

    §115 verlangt fuer jede Hypothese eine Aufgabe, die sie widerlegen wuerde.
    ``falsifying_task`` ist diese Aufgabe; ist sie noch nicht bearbeitet, ist
    sie zugleich die "noch fehlende Evidenz" und die "naechste geeignete
    Kontrollaufgabe" der UI-Spezifikation. Beides muss nicht geschaetzt werden.
    """
    bearbeitet = {r["task_id"] for r in conn.execute(
        "SELECT DISTINCT task_id FROM task_attempts WHERE student_id = ?", (student_id,))}

    out = []
    for row in conn.execute(
        "SELECT * FROM student_hypotheses WHERE student_id = ?"
        " ORDER BY priority DESC, hypothesis_id", (student_id,)
    ):
        item = dict(row)
        item["description"] = hypo.describe(item)
        item["competency_id"] = item["target_construct"].split(":", 1)[0]
        item["supporting_evidence"] = _json(item["supporting_evidence"], [])
        item["contradicting_evidence"] = _json(item["contradicting_evidence"], [])
        item["evidence_balance"] = {
            "supporting": len(item["supporting_evidence"]),
            "contradicting": len(item["contradicting_evidence"]),
        }
        task = item["falsifying_task"]
        state = "NONE" if not task else ("DONE" if task in bearbeitet else "PLANNED")
        item["hypothesis_test"] = {
            "task_id": task,
            "state": state,
            # ``is_active`` beantwortet die Frage, die die Oberflaeche an drei
            # Stellen stellt: wird diese Hypothese GERADE geprueft? Das ist mehr
            # als ``state == "PLANNED"`` - eine verworfene oder geschlossene
            # Hypothese kann eine unbearbeitete Kontrollaufgabe stehen lassen.
            # Beide Haelften der Bedingung stehen hier, damit das Frontend sie
            # nicht nachbaut; ``_attach_next_question`` benutzt dieselbe Zeile.
            "is_active": state == "PLANNED" and item["status"] in ACTIVE_HYPOTHESIS_STATUS,
            "spec_section": "§115",
        }
        item["missing_evidence"] = (
            None if not task or task in bearbeitet
            else f"Kontrollaufgabe {task} ist noch nicht bearbeitet.")
        out.append(item)

    # Konkurrierende Hypothesen: welche beziehen sich auf dieselbe Kompetenz?
    by_competency: dict[str, list[str]] = {}
    for item in out:
        by_competency.setdefault(item["competency_id"], []).append(item["hypothesis_id"])
    for item in out:
        item["competing_hypotheses"] = [
            h for h in by_competency[item["competency_id"]] if h != item["hypothesis_id"]]
    return out


def routing_decisions(conn: sqlite3.Connection, student_id: str) -> list[dict]:
    """RoutingDecision - §89 Explainability Logging.

    Die UI-Spezifikation verlangt in der Debug-Ansicht sichtbar zu machen,
    welche Daten fuer eine Entscheidung benutzt wurden und welche nicht. Genau
    dafuer sind ``evidence_used``, ``hypothesis_used``, ``alternatives_
    considered`` und ``score_breakdown`` da.
    """
    out = []
    for row in conn.execute(
        "SELECT * FROM routing_decisions WHERE student_id = ?"
        " ORDER BY timestamp, decision_id", (student_id,)
    ):
        item = dict(row)
        for field, default in (("evidence_used", []), ("hypothesis_used", []),
                               ("alternatives_considered", []), ("score_breakdown", {})):
            item[field] = _json(item[field], default)
        out.append(item)
    return out


# ------------------------------------------------------------- Gesamtbild


def student_profile(conn: sqlite3.Connection, student_id: str, cfg: Config,
                    clock: Clock) -> dict:
    """StudentProfile - alles zu einer Schueler:in in einem Dokument.

    Bewusst ein Dokument statt vieler Endpunkte: die Datenmengen sind klein
    (ein Durchlauf hat Dutzende Zeilen, nicht Tausende), und die UI kann
    zwischen allen Ansichten wechseln, ohne nachzuladen. Wird das spaeter zu
    gross, wird aus diesem Dokument eine Endpunktfamilie - die Feldnamen
    bleiben.
    """
    states = competency_states(conn, student_id, cfg)
    student = conn.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    decisions = routing_decisions(conn, student_id)
    hyps = hypotheses_view(conn, student_id)

    # §89: die zuletzt protokollierte Entscheidung ist die noch offene, solange
    # ihre Aufgabe nicht bearbeitet wurde - session.submit() protokolliert die
    # naechste Auswahl am Ende jedes Durchlaufs. Die Oberflaeche berechnet hier
    # nichts nach; routing.next_task() erneut aufzurufen wuerde eine zweite
    # Entscheidungszeile schreiben, nur weil jemand eine Seite ansieht.
    pending = decisions[-1] if decisions else None
    bearbeitet = {r["task_id"] for r in conn.execute(
        "SELECT DISTINCT task_id FROM task_attempts WHERE student_id = ?", (student_id,))}
    if pending:
        pending = dict(pending)
        pending["is_pending"] = bool(
            pending["selected_task"] and pending["selected_task"] not in bearbeitet)

    _attach_next_question(conn, states, pending, hyps)

    by_class: dict[str, list[str]] = {"RESOURCE": [], "OPEN": [], "UNCHECKED": []}
    for state in states:
        by_class[state["resource_class"]].append(state["competency_id"])

    return {
        "student": dict(student) if student else {"student_id": student_id},
        "competency_states": states,
        "resource_overview": {
            key: {"label": RESOURCE_CLASS_LABEL[key], "competencies": value}
            for key, value in by_class.items()
        },
        "observations": observations(conn, student_id),
        "error_observations": error_observations(conn, student_id),
        "error_patterns": error_patterns(conn, student_id, cfg),
        "evidence": evidence(conn, student_id),
        "representation_evidence": representation_evidence(conn, student_id, cfg),
        "process_competency_evidence": process_competency_evidence(conn, student_id),
        "hypotheses": hyps,
        "routing_decisions": decisions,
        "next_decision": pending,
    }


def _attach_next_question(conn: sqlite3.Connection, states: list[dict],
                          pending: dict | None, hyps: list[dict]) -> None:
    """"Naechste diagnostische Frage" je Kompetenzknoten.

    Zwei Quellen, beide aus dem Backend, beide benannt:

    * ``ROUTING_DECISION`` - die noch offene Auswahl aus §119, sofern sie
      diesen Knoten betrifft. Es gibt hoechstens eine, weil die Engine genau
      eine naechste Aufgabe waehlt.
    * ``HYPOTHESIS_TEST`` - die Aufgabe aus ``falsifying_task`` jeder offenen
      Hypothese zu diesem Knoten (§115), solange sie nicht bearbeitet ist.

    Beide werden getrennt ausgewiesen und nicht zu einer Empfehlung verrechnet.
    Eine eigene Rangfolge zu bilden waere genau die Routinglogik, die nicht ins
    Frontend gehoert - und sie stuende hier ebenso falsch.
    """
    target = None
    if pending and pending.get("is_pending") and pending["selected_task"]:
        row = conn.execute("SELECT primary_competency FROM tasks WHERE task_id = ?",
                           (pending["selected_task"],)).fetchone()
        target = row["primary_competency"] if row else None

    by_competency: dict[str, list[dict]] = {}
    for h in hyps:
        test = h["hypothesis_test"]
        if test["is_active"]:
            by_competency.setdefault(h["competency_id"], []).append(
                {"hypothesis_id": h["hypothesis_id"], "task_id": test["task_id"],
                 "description": h["description"]})

    for state in states:
        competency_id = state["competency_id"]
        state["next_question"] = {
            "from_routing": (pending["selected_task"]
                             if target == competency_id else None),
            "routing_reason": pending.get("rule_triggered") if target == competency_id else None,
            "from_hypothesis_tests": by_competency.get(competency_id, []),
        }


def catalog(conn: sqlite3.Connection) -> dict:
    """Der schuelerunabhaengige Teil: Graph, Aufgabenbank, Vokabular."""
    return {
        "vocabulary": vocabulary(conn),
        "competency_nodes": competency_nodes(conn),
        "relations": relations(conn),
        "tasks": tasks(conn),
        "error_codes": error_codes(conn),
        "resource_class_label": RESOURCE_CLASS_LABEL,
    }


def students(conn: sqlite3.Connection) -> list[dict]:
    return _rows(conn,
                 "SELECT s.student_id, s.created_at, s.grade_reference,"
                 " (SELECT COUNT(*) FROM task_attempts a WHERE a.student_id = s.student_id)"
                 "   AS attempt_count"
                 " FROM students s ORDER BY s.student_id")
