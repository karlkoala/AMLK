"""Rule Engine und Routing (Sprint 7, 10, 11).

Setzt §119 um:

    function nextTask(student):
        state = loadStudentState(student)
        activeNodes = getActiveRelevantNodes(state)
        hypotheses = getOpenHypotheses(state)
        candidates = getTasks(activeNodes)
        candidates = removeRedundantTasks(candidates)
        candidates = removeParkedCompetencies(candidates)
        candidates = filterByPrerequisites(candidates)
        for task in candidates: task.score = ...
        return highestScoringTask(candidates)

Die bindenden Grenzen:

§75  Das LLM ist nicht die Entscheidungsinstanz. Dieses Modul ist regelbasiert
     und ruft kein Sprachmodell. §76 listet auf, was ohne LLM funktionieren
     muss - Routing, Kompetenzstatus, Parallelitem-Auswahl, Skip-Level, Parken,
     Reaktivierung - und genau das steht hier.
§84  Routing wird nicht hardcodiert. Alle konkreten Uebergaenge kommen aus
     task_routes, alle Gewichte und Schwellen aus system_config. In diesem
     Modul steht keine Aufgaben-ID und keine Kompetenz-ID als Literal.
§73  Nicht uebertesten. Ziel ist nicht maximale, sondern maximal relevante
     Datenerhebung mit moeglichst wenigen Aufgaben.
§89  Jede Entscheidung wird protokolliert, mit Alternativen und Begruendung.
§121 Keine automatische Ferninferenz: eine Kette A->B->C->D->E wird genutzt, um
     ein informationsreiches Item auszuwaehlen, nicht um E zu behaupten.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from . import ids, parking
from .attempts import attempt_history, task_features
from .parking import Transition
from .clock import Clock
from .config import Config
from .hypotheses import open_hypotheses
from .state import DIFFICULTIES, facets_of

#: Status, deren Kompetenzen aktiv beprobt werden (§67: ACTIVE, UNKNOWN,
#: REACTIVATED). UNCERTAIN und SUPPORT_FOCUS gehoeren dazu, weil §30 und §91
#: dort ausdruecklich weitere Aufgaben verlangen.
ACTIVE_STATUSES = ("UNKNOWN", "ACTIVE", "REACTIVATED", "UNCERTAIN", "SUPPORT_FOCUS")

#: Status, die aus dem normalen Pool entfernt werden (§38, §3).
EXCLUDED_STATUSES = ("PARKED", "BLOCKED")

PREREQUISITE_TYPES = ("HARD_PREREQUISITE", "STRONG_PREREQUISITE")


@dataclass
class Candidate:
    task_id: str
    competency_id: str
    difficulty: str
    representation: str
    purpose: str
    #: §94 Bezugsrahmen des Items. Getrennt gefuehrt, weil der Score nach §68
    #: die Naehe zur Klassenstufe braucht, der Filter aber nur die Obergrenze.
    grade_min: int | None = None
    grade_max: int | None = None
    score: float = 0.0
    breakdown: dict = field(default_factory=dict)
    route_id: str | None = None
    reason: str | None = None
    hypothesis_id: str | None = None


@dataclass
class Decision:
    decision_id: str
    selected_task: str | None
    reason: str | None
    rule_triggered: str | None
    confidence: str
    alternatives: list[dict]
    breakdown: dict
    hypothesis_used: list[str]
    evidence_used: list[str]
    explanation: str
    stop_reason: str | None = None
    termination: dict = field(default_factory=dict)


# --------------------------------------------------------- Klassenstufe (§94)


def student_grade(conn: sqlite3.Connection, student_id: str) -> int | None:
    """Die Klassenstufe aus students.grade_reference, oder None.

    §87 fuehrt die Klassenstufe als Bezugsrahmen, §94 ausdruecklich als
    "Referenz, keine Schranke". Beides zusammen ergibt eine Richtung, nicht
    zwei: nach OBEN wird nichts angeboten, was die Stufe noch gar nicht
    behandelt hat - wer in Klasse 3 ist, bekommt keinen Satz des Pythagoras
    vorgelegt, und ein Fehlversuch dort waere auch keine Beobachtung ueber
    diese Schueler:in, sondern ueber den Lehrplan. Nach UNTEN bleibt alles
    offen, denn genau das ist die diagnostische Bewegung dieses Systems: §36
    sucht rueckwaerts, bis die Stelle gefunden ist, an der die Schwierigkeit
    beginnt. Eine Schranke nach unten wuerde §36 abschneiden.

    Ohne Angabe bleibt alles wie bisher - die Stufe ist eine Angabe der
    Lehrkraft, keine Annahme des Systems (§1).
    """
    row = conn.execute(
        "SELECT grade_reference FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    return row["grade_reference"] if row else None


def _in_grade_band(grade: int | None, grade_min: int | None) -> bool:
    """Liegt ein Knoten oder Item in dem, was diese Stufe schon kennt?"""
    if grade is None or grade_min is None:
        return True
    return grade_min <= grade


def engaged_competencies(conn: sqlite3.Connection, student_id: str) -> set[str]:
    """Knoten, auf denen bereits eine Beobachtung vorliegt.

    Die Klassenstufe entscheidet, WOMIT begonnen wird - nicht, womit eine
    begonnene Beobachtung fortgesetzt wird. Sobald auf einem Knoten ein
    Versuch liegt, ist das Argument der Stufe verbraucht: die Aufgabe wurde
    gestellt, und §30 verlangt dann das Parallelitem, §36 den Schritt
    rueckwaerts, §52 das Contrast Item. Wuerde die Stufe auch hier filtern,
    bliebe eine Beobachtung ohne ihre Replikation stehen - und §29 waere
    verletzt, der aus einem einzelnen Fehler ausdruecklich keine Diagnose
    zulaesst. Die Lehrkraft kann nach §3 jedes Item ohnehin direkt waehlen;
    dass eine so gestellte Aufgabe keine Fortsetzung faende, waere nicht
    Zurueckhaltung, sondern ein Abbruch.
    """
    return {r["primary_competency"] for r in conn.execute(
        "SELECT DISTINCT t.primary_competency FROM task_attempts a"
        " JOIN tasks t ON t.task_id = a.task_id WHERE a.student_id = ?", (student_id,))}


# ------------------------------------------------------------ Teilgraph (§74)


def active_nodes(conn: sqlite3.Connection, student_id: str, cfg: Config,
                 grade: int | None = None) -> dict[str, str]:
    """Der aktive Teilgraph. §37 und §74: aus dem globalen Graphen wird nur ein
    kleiner Teil aktiviert, bereits geklaerte Pfade werden nicht erneut geladen.

    Aufgenommen wird, was ueberhaupt Items hat. Das Feld is_mvp stand hier
    frueher als Filter; es benennt aber die Herkunft eines Knotens (MVP V1.0,
    Leitidee L1) und nicht seine Bespielbarkeit. Mit dem Aufgabenbestand fuer
    die Klassen 5 bis 10 faellt beides auseinander: jene Knoten sind
    ausdruecklich nicht Teil von MVP V1.0 und tragen deshalb is_mvp = 0 (§1:
    kein Feld behauptet etwas, das nicht stimmt), haben aber Items. Der Filter
    fragt jetzt nach dem, worauf es ankommt. Fuer den MVP-Bestand aendert sich
    nichts - dort hatte jeder Knoten mit Items auch is_mvp = 1.
    """
    state = {
        r["competency_id"]: r["status"] for r in conn.execute(
            "SELECT competency_id, status FROM student_competency_state WHERE student_id = ?",
            (student_id,))
    }
    engaged = engaged_competencies(conn, student_id)
    with_items = {
        r["competency_id"] for r in conn.execute(
            "SELECT DISTINCT c.competency_id, c.grade_reference_min FROM competencies c"
            " JOIN tasks t ON t.primary_competency = c.competency_id")
        if r["competency_id"] in engaged
        or _in_grade_band(grade, r["grade_reference_min"])
    }

    active: dict[str, str] = {}
    for competency in with_items:
        status = state.get(competency, "UNKNOWN")
        if status in ACTIVE_STATUSES:
            active[competency] = status

    # §74: relevante Nachbarn eines aktiven Knotens gehoeren dazu, damit die
    # Rueckwaertssuche aus §36 ueberhaupt Kandidaten hat.
    neighbours: dict[str, str] = {}
    for competency in list(active):
        for row in conn.execute(
            "SELECT source_competency FROM relations WHERE target_competency = ?"
            f" AND relation_type IN ({','.join('?' * len(PREREQUISITE_TYPES))})",
            (competency, *PREREQUISITE_TYPES),
        ):
            neighbour = row["source_competency"]
            if neighbour in with_items and neighbour not in active:
                status = state.get(neighbour, "UNKNOWN")
                if status not in EXCLUDED_STATUSES:
                    neighbours[neighbour] = status
    active.update(neighbours)
    return active


def trigger_prerequisite_reactivation(conn: sqlite3.Connection, student_id: str,
                                      cfg: Config, clock: Clock) -> list[str]:
    """§39 dritter Grund: NEW_TARGET_REQUIRES_PREREQUISITE zusammen mit
    EXISTING_EVIDENCE_INSUFFICIENT. Wird geprueft, bevor Kandidaten gebildet
    werden, damit ein reaktivierter Knoten sofort in den Pool kommt."""
    reactivated = []
    for competency in list(active_nodes(conn, student_id, cfg)):
        for row in conn.execute(
            "SELECT source_competency FROM relations WHERE target_competency = ?"
            f" AND relation_type IN ({','.join('?' * len(PREREQUISITE_TYPES))})",
            (competency, *PREREQUISITE_TYPES),
        ):
            transition = parking.check_reactivation(
                conn, student_id, row["source_competency"], cfg, clock,
                new_target_requires=True)
            if transition:
                reactivated.append(transition.competency_id)
    return reactivated


# ------------------------------------------------------------- Routen (§83/§84)


def trigger_review_reactivation(conn: sqlite3.Connection, student_id: str,
                                cfg: Config, clock: Clock) -> list[Transition]:
    """§40 Wiedervorlage. Prueft alle geparkten Knoten auf Reaktivierung.

    Ohne diesen Durchgang koennte eine geparkte Kompetenz nie zurueckkommen:
    §38 entfernt sie aus dem Aufgabenpool, also entsteht dort keine neue direkte
    Evidenz, die sie nach §39 zurueckholen wuerde. Die Wiedervorlage bricht
    diesen Zirkel - genau dafuer fuehrt §40 die Felder last_review und
    next_review.

    Geprueft werden alle drei Gruende aus §39; welcher greift, entscheidet
    parking.check_reactivation.
    """
    out = []
    for row in conn.execute(
        "SELECT competency_id FROM student_competency_state"
        " WHERE student_id = ? AND status = 'PARKED' ORDER BY competency_id",
        (student_id,),
    ).fetchall():
        transition = parking.check_reactivation(
            conn, student_id, row["competency_id"], cfg, clock)
        if transition:
            out.append(transition)
    return out


def matching_routes(conn: sqlite3.Connection, student_id: str, source_task: str,
                    is_correct: bool, error_codes: list[str],
                    repeated: bool) -> list[dict]:
    """Routen, die nach dem letzten Versuch greifen.

    Die Bedingungen entsprechen dem Vokabular ROUTE_CONDITION. WRONG_REPLICATED
    und WRONG_SAME_ERROR_CODE setzen §30 um: erst die Wiederholung macht aus dem
    Fehler ein Muster.
    """
    conditions = {"ANY"}
    conditions.add("CORRECT" if is_correct else "WRONG")
    if not is_correct and repeated:
        conditions.add("WRONG_REPLICATED")
        conditions.add("WRONG_SAME_ERROR_CODE")

    rows = conn.execute(
        "SELECT * FROM task_routes WHERE source_task = ? AND enabled = 1"
        " ORDER BY priority DESC, route_id", (source_task,)
    ).fetchall()

    state = {
        r["competency_id"]: r["status"] for r in conn.execute(
            "SELECT competency_id, status FROM student_competency_state WHERE student_id = ?",
            (student_id,))
    }
    open_types = {h["hypothesis_type"] for h in open_hypotheses(conn, student_id)}

    out = []
    for row in rows:
        if row["condition"] not in conditions:
            continue
        # Erweiterung gegenueber §83, siehe ENTSCHEIDUNGEN.md D-08.
        if row["requires_status"]:
            target = row["target_competency"] or _competency_of(conn, row["target_task"])
            if state.get(target) != row["requires_status"]:
                continue
        if row["requires_hypothesis"] and row["requires_hypothesis"] not in open_types:
            continue
        out.append(dict(row))
    return out


def _drop_satisfied_routes(conn: sqlite3.Connection, student_id: str,
                           routes: list[dict]) -> list[dict]:
    """Eine Route, deren Zielaufgabe schon gestellt wurde, ist erledigt.

    Zweck einer Route ist eine NEUE Beobachtung - §30 verlangt fuer die
    Replikation ausdruecklich ein Parallelitem, nicht dieselbe Aufgabe. Eine
    Ausnahme gilt fuer REACTIVATED: dort ist die Wiederholungspruefung nach §39
    genau der Zweck.
    """
    administered = {r["task_id"] for r in conn.execute(
        "SELECT DISTINCT task_id FROM task_attempts WHERE student_id = ?", (student_id,))}
    status = {r["competency_id"]: r["status"] for r in conn.execute(
        "SELECT competency_id, status FROM student_competency_state WHERE student_id = ?",
        (student_id,))}
    out = []
    for route in routes:
        target = route.get("target_task")
        if target and target in administered:
            competency = _competency_of(conn, target)
            if status.get(competency) != "REACTIVATED":
                continue
        out.append(route)
    return out


def _competency_of(conn: sqlite3.Connection, task_id: str | None) -> str | None:
    if not task_id:
        return None
    row = conn.execute(
        "SELECT primary_competency FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    return row["primary_competency"] if row else None


# ------------------------------------------------------ Kandidaten und Filter


def _undeliverable(conn: sqlite3.Connection) -> set[str]:
    """Items, die nach §113 nicht ausgeliefert werden duerfen (F-17, F-18)."""
    out = set()
    for row in conn.execute("SELECT task_id, task_payload, correct_answer FROM tasks"):
        payload = json.loads(row["task_payload"])
        answer = json.loads(row["correct_answer"])
        if payload.get("options_status") == "UNDEFINED":
            out.add(row["task_id"])
        elif isinstance(answer, dict) and answer.get("status") == "UNDEFINED":
            out.add(row["task_id"])
    return out


def candidates(conn: sqlite3.Connection, student_id: str, cfg: Config,
               nodes: dict[str, str], forced_competencies: set[str],
               forced_tasks: set[str] | None = None,
               exclusions: dict | None = None,
               grade: int | None = None) -> list[Candidate]:
    """§119: getTasks, removeRedundant, removeParked, filterByPrerequisites.

    forced_competencies hebt die Sperren auf Knotenebene auf (PARKED, SECURE,
    Itemobergrenze), forced_tasks nur die Wiederholungssperre fuer genau das
    Item, auf das eine Route zeigt. Die Trennung ist wichtig: ein Routenziel
    darf nicht die ganze Kompetenz fuer Wiederholungen oeffnen.
    """
    forced_tasks = forced_tasks or set()
    engaged = engaged_competencies(conn, student_id)
    pool_nodes = set(nodes) | forced_competencies
    if not pool_nodes:
        return []

    placeholders = ",".join("?" * len(pool_nodes))
    rows = conn.execute(
        f"SELECT task_id, primary_competency, internal_difficulty, representation_mode,"
        f" task_purpose, prerequisites, grade_reference_min, grade_reference_max"
        f" FROM tasks WHERE primary_competency IN ({placeholders})", tuple(sorted(pool_nodes))
    ).fetchall()

    undeliverable = _undeliverable(conn)
    state = {
        r["competency_id"]: dict(r) for r in conn.execute(
            "SELECT * FROM student_competency_state WHERE student_id = ?", (student_id,))
    }
    answered_correctly = {
        r["task_id"] for r in conn.execute(
            "SELECT DISTINCT task_id FROM task_attempts WHERE student_id = ? AND is_correct = 1",
            (student_id,))
    }
    max_items = cfg.require("testing.max_items_per_node")
    administered_per_node = {
        r["primary_competency"]: r["n"] for r in conn.execute(
            "SELECT t.primary_competency, COUNT(*) AS n FROM task_attempts a"
            " JOIN tasks t ON t.task_id = a.task_id WHERE a.student_id = ?"
            " GROUP BY t.primary_competency", (student_id,))
    }

    administered_tasks = {
        r["task_id"] for r in conn.execute(
            "SELECT DISTINCT task_id FROM task_attempts WHERE student_id = ?", (student_id,))
    }
    falsifying_tasks = {
        r["falsifying_task"] for r in conn.execute(
            "SELECT falsifying_task FROM student_hypotheses WHERE student_id = ?"
            " AND status IN ('OPEN', 'SUPPORTED', 'WEAKENED')"
            " AND falsifying_task IS NOT NULL", (student_id,))
    }
    tally_cache: dict[str, dict] = {}

    out: list[Candidate] = []
    def exclude(row, reason):
        if exclusions is not None:
            exclusions.setdefault(row["primary_competency"], {}).setdefault(reason, []).append(row["task_id"])
    for row in rows:
        competency = row["primary_competency"]
        if row["task_id"] in undeliverable:
            exclude(row, "UNDELIVERABLE")
            continue
        # §94: die Klassenstufe begrenzt nach oben, nie nach unten. Siehe
        # student_grade(). Ausgenommen sind ein Routenziel - fordert eine
        # fachliche Regel ein bestimmtes Item an, entscheidet die Regel - und
        # jeder Knoten, auf dem schon eine Beobachtung liegt (siehe
        # engaged_competencies).
        if (row["task_id"] not in forced_tasks and competency not in engaged
                and not _in_grade_band(grade, row["grade_reference_min"])):
            exclude(row, "ABOVE_GRADE_REFERENCE")
            continue
        status = state.get(competency, {}).get("status", "UNKNOWN")
        # removeParkedCompetencies (§38) - ausser der Knoten ist Routenziel.
        if status in EXCLUDED_STATUSES and competency not in forced_competencies:
            exclude(row, "STATUS_EXCLUDED")
            continue
        # §73: nicht uebertesten.
        if competency not in forced_competencies:
            if status == "SECURE":
                exclude(row, "ALREADY_SECURE")
                continue
            if administered_per_node.get(competency, 0) >= max_items:
                exclude(row, "NODE_TASK_LIMIT")
                continue
        # removeRedundantTasks: bereits richtig geloest.
        if row["task_id"] in answered_correctly:
            exclude(row, "ALREADY_CORRECT")
            continue
        # Bereits gestellte Aufgaben werden nicht wiederholt - eine zweite
        # Falschantwort auf dasselbe Item ist keine unabhaengige Beobachtung
        # und wuerde §30 (Replikation ueber ein Parallelitem) aushebeln.
        # Ausnahmen: eine Route zielt darauf, es ist das widerlegende Item einer
        # offenen Hypothese (§115), oder die Kompetenz ist REACTIVATED und wird
        # nach §39 erneut geprueft.
        if row["task_id"] in administered_tasks:
            if not (row["task_id"] in forced_tasks
                    or row["task_id"] in falsifying_tasks
                    or status == "REACTIVATED"):
                exclude(row, "ALREADY_ADMINISTERED")
                continue
        # §36 und §98: unterhalb einer abgeschlossenen Stufe liegt keine
        # Information mehr. "Moeglichst wenige Aufgaben stellen, die moeglichst
        # viel Information liefern."
        if competency not in forced_competencies:
            if competency not in tally_cache:
                tally_cache[competency] = level_tally(conn, student_id, competency)
            settled = settled_levels(tally_cache[competency], cfg)
            secured = [level for level in DIFFICULTIES
                       if level in settled and tally_cache[competency][level]["pos"] > 0]
            if secured and _difficulty_index(row["internal_difficulty"]) \
                    < _difficulty_index(secured[-1]):
                exclude(row, "BELOW_SECURED_LEVEL")
                continue
        # filterByPrerequisites: was nachweislich nicht erreichbar ist, wird
        # nicht angeboten (§31, §91 - erst zugaenglicher Einstieg, dann Aufbau).
        if _prerequisite_blocked(conn, row, state, competency):
            exclude(row, "PREREQUISITE_BLOCKED")
            continue
        out.append(Candidate(task_id=row["task_id"], competency_id=competency,
                             difficulty=row["internal_difficulty"],
                             representation=row["representation_mode"],
                             purpose=row["task_purpose"],
                             grade_min=row["grade_reference_min"],
                             grade_max=row["grade_reference_max"]))
    return out


def _prerequisite_blocked(conn: sqlite3.Connection, row: sqlite3.Row,
                          state: dict, competency: str) -> bool:
    declared = json.loads(row["prerequisites"])
    for prerequisite in declared:
        if state.get(prerequisite, {}).get("status") == "SUPPORT_FOCUS":
            return True
    for rel in conn.execute(
        "SELECT source_competency FROM relations WHERE target_competency = ?"
        " AND relation_type = 'HARD_PREREQUISITE'", (competency,)
    ):
        if state.get(rel["source_competency"], {}).get("status") == "SUPPORT_FOCUS":
            return True
    return False


# --------------------------------------------------------------- Score (§68)


def _difficulty_index(difficulty: str) -> int:
    return DIFFICULTIES.index(difficulty)


def level_tally(conn: sqlite3.Connection, student_id: str,
                competency_id: str) -> dict[str, dict[str, int]]:
    """Richtig und falsch je Schwierigkeitsstufe. §117: nicht aggregieren."""
    tally = {d: {"pos": 0, "neg": 0} for d in DIFFICULTIES}
    for row in conn.execute(
        "SELECT t.internal_difficulty AS d, a.is_correct FROM task_attempts a"
        " JOIN tasks t ON t.task_id = a.task_id"
        " WHERE a.student_id = ? AND t.primary_competency = ?",
        (student_id, competency_id),
    ):
        tally[row["d"]]["pos" if row["is_correct"] else "neg"] += 1
    return tally


def settled_levels(tally: dict[str, dict[str, int]], cfg: Config) -> set[str]:
    """Stufen, auf denen die Evidenz ausreicht. §41, §73."""
    need = cfg.require("mastery.success_confirmation_required")
    fail = cfg.require("mastery.failure_replication_required")
    return {level for level, b in tally.items()
            if (b["pos"] >= need and b["neg"] == 0) or (b["neg"] >= fail and b["pos"] == 0)}


def _available_levels(conn: sqlite3.Connection, student_id: str,
                      competency_id: str) -> set[str]:
    """Stufen, auf denen es noch nicht gestellte, auslieferbare Items gibt."""
    undeliverable = _undeliverable(conn)
    administered = {r["task_id"] for r in conn.execute(
        "SELECT DISTINCT task_id FROM task_attempts WHERE student_id = ?", (student_id,))}
    out = set()
    for row in conn.execute(
        "SELECT task_id, internal_difficulty FROM tasks WHERE primary_competency = ?",
        (competency_id,),
    ):
        if row["task_id"] not in undeliverable and row["task_id"] not in administered:
            out.add(row["internal_difficulty"])
    return out


def target_difficulty(conn: sqlite3.Connection, student_id: str, competency_id: str,
                      cfg: Config, last: dict | None) -> str:
    """§34 Skip-Level, §35 nur als konfigurierbare Heuristik, §96 Startlogik.

    Drei Regeln in dieser Reihenfolge:

    1. §34 Sprungtabelle, wenn der letzte Versuch diese Kompetenz betraf.
    2. BESTAETIGUNG: gibt es eine Stufe mit Erfolg, aber noch nicht genug
       Erfolgen (§41 success_confirmation_required), wird dort bestaetigt -
       und zwar auf der HOECHSTEN solchen Stufe, auf der noch Items uebrig
       sind. §98 (Testfall A) erwartet genau das: nach D3 richtig und D5
       richtig wird die Sicherung auf D3 abgeschlossen, nicht nach D1
       abgestiegen ("Keine unnoetigen D1/D2-Aufgaben").
    3. §36 Fenstermitte zwischen gesicherter Unter- und Obergrenze.

    §96: ohne Daten wird nicht mit der leichtesten Aufgabe begonnen.
    """
    start = cfg.require("routing.start_difficulty")
    tally = level_tally(conn, student_id, competency_id)
    if not any(b["pos"] or b["neg"] for b in tally.values()):
        return start

    if cfg.require("routing.skip_level_enabled"):
        skip_map = cfg.require("routing.skip_level_map")
        if last and last.get("competency_id") == competency_id:
            entry = skip_map.get(last["difficulty"])
            if entry:
                jump = entry.get("success" if last["is_correct"] else "failure")
                if jump and jump in _available_levels(conn, student_id, competency_id):
                    return jump

    need = cfg.require("mastery.success_confirmation_required")
    available = _available_levels(conn, student_id, competency_id)
    to_confirm = [level for level in DIFFICULTIES
                  if 0 < tally[level]["pos"] < need and tally[level]["neg"] == 0
                  and level in available]
    if to_confirm:
        return to_confirm[-1]

    row = conn.execute(
        "SELECT current_floor, current_ceiling FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?", (student_id, competency_id)
    ).fetchone()
    if row and (row["current_floor"] or row["current_ceiling"]):
        low = _difficulty_index(row["current_floor"]) + 1 if row["current_floor"] else 0
        high = _difficulty_index(row["current_ceiling"]) - 1 if row["current_ceiling"] \
            else len(DIFFICULTIES) - 1
        if low > high:
            # Fenster geschlossen: die Grenze ist gefunden, es bleibt die Stufe
            # der Obergrenze als Pruefpunkt (§36).
            return row["current_ceiling"] or row["current_floor"] or start
        return DIFFICULTIES[(low + high) // 2]
    return start


def _replication_pending(conn: sqlite3.Connection, student_id: str, last: dict,
                         cfg: Config) -> bool:
    """§30: steht die Wiederholung des Fehlers noch aus?

    Gezaehlt werden die Fehlversuche auf der betroffenen Kompetenz, die
    mindestens einen Fehlercode mit dem letzten teilen. Erreicht die Zahl
    mastery.failure_replication_required, ist das Muster festgestellt und die
    Replikation abgeschlossen - weiteres Replizieren waere Uebertesten (§73).

    ERR_SELF_CORRECTED bleibt aussen vor: es beschreibt den Bearbeitungsverlauf,
    nicht das Fehlermuster, und wuerde sonst beliebige Fehler zu 'aehnlich'
    machen.
    """
    codes = set(last.get("error_codes") or ()) - {"ERR_SELF_CORRECTED"}
    if not codes:
        return False
    required = cfg.require("mastery.failure_replication_required")
    row = conn.execute(
        "SELECT COUNT(DISTINCT a.attempt_id) AS n FROM task_attempts a"
        " JOIN tasks t ON t.task_id = a.task_id"
        " JOIN attempt_error_codes e ON e.attempt_id = a.attempt_id"
        " WHERE a.student_id = ? AND a.is_correct = 0 AND t.primary_competency = ?"
        f" AND e.error_code IN ({','.join('?' * len(codes))})",
        (student_id, last["competency_id"], *sorted(codes)),
    ).fetchone()
    return (row["n"] if row else 0) < int(required)


def score_candidates(conn: sqlite3.Connection, student_id: str, cfg: Config,
                     pool: list[Candidate], nodes: dict[str, str],
                     hypotheses: list[dict], routes: list[dict],
                     last: dict | None, grade: int | None = None) -> list[Candidate]:
    """TASK_SCORE nach §68.

        TASK_SCORE = information_need + hypothesis_discrimination
                     + boundary_value + transfer_value - redundancy - cost

    §68: "Die Gewichte sind konfigurierbar. Keine wissenschaftliche Validierung
    behaupten." Alle sechs Gewichte und der Routenbonus stehen in system_config.
    """
    w = {
        "information_need": cfg.require("score.weight_information_need"),
        "hypothesis_discrimination": cfg.require("score.weight_hypothesis_discrimination"),
        "boundary_value": cfg.require("score.weight_boundary_value"),
        "transfer_value": cfg.require("score.weight_transfer_value"),
        "redundancy": cfg.require("score.weight_redundancy"),
        "estimated_cost": cfg.require("score.weight_estimated_cost"),
        "route": cfg.require("score.weight_route_bonus"),
        "facet_novelty": cfg.require("score.weight_facet_novelty"),
        "confirmation": cfg.require("score.weight_confirmation"),
        "family_completion": cfg.require("score.weight_family_completion"),
        "replication": cfg.require("score.weight_replication"),
        "grade_fit": cfg.require("score.weight_grade_fit"),
    }
    need_by_status = cfg.require("score.information_need_by_status")
    cost_reference = cfg.require("score.cost_reference_seconds")

    route_by_task = {}
    route_by_competency = {}
    for route in routes:
        if route["target_task"]:
            route_by_task.setdefault(route["target_task"], route)
        elif route["target_competency"]:
            route_by_competency.setdefault(route["target_competency"], route)

    # §29/§30: "TASK A WRONG ... fuehrt nicht zu COMPETENCY = NOT_MASTERED,
    # sondern zunaechst zu OBSERVATION = ERROR. Dann: Parallelitem." §67 fuehrt
    # "1 replicate error" als erste Prioritaet, §31 das Parallelitem als Rang 2
    # von 12 - noch vor Voraussetzung, Strategie und Darstellung.
    #
    # tasks.parallel_item_id trug diese Beziehung bisher nur als Datenfeld: der
    # Score las es nirgends. Fuenf Items hatten eine ausdrueckliche
    # REPLICATE_ERROR-Route, die uebrigen dreizehn trafen ihr Parallelitem nur,
    # wenn der ergebnisblinde family_completion-Bonus zufaellig reichte - bei
    # ZO07-D2-S-A/-S-B und ZO13-D3-S-A reichte er nicht. Schlimmer noch: nach
    # einem Fehler faellt information_need des betroffenen Knotens von 1.0
    # (UNKNOWN) auf 0.7 (ACTIVE), der eben gescheiterte Knoten wurde also
    # abgewertet statt repliziert. Ohne Replikation loest _is_repeated_pattern
    # nie aus, und §30 verlangt ein reproduzierbares Muster, bevor eine
    # Hypothese entstehen darf - die Diagnostik lief fuer diese Items leer.
    # Der Bonus gilt nur, SOLANGE der Fehler noch nicht repliziert ist. §30
    # verlangt die Wiederholung, um ein Muster festzustellen - ist das Muster
    # festgestellt, ist die Replikation erledigt und §31 geht weiter zu Rang 3,
    # der Voraussetzung. Ohne diese Schranke repliziert das System auf jeder
    # Stufe erneut und testet nach §73 ueber: Testfall B lief dadurch von vier
    # auf sieben Aufgaben, ohne eine einzige zusaetzliche Beobachtung.
    #
    # Die Schranke ist mastery.failure_replication_required (§41, §30) und
    # zaehlt je Kompetenz, nicht je Familie: repliziert wird der Fehler, nicht
    # das Item. Zwei Fehler mit demselben Code auf ZO06 sind ein Muster, auch
    # wenn sie in verschiedenen Familien liegen.
    replication_target = None
    if last and not last["is_correct"] and _replication_pending(conn, student_id, last, cfg):
        row = conn.execute("SELECT parallel_item_id FROM tasks WHERE task_id = ?",
                           (last["task_id"],)).fetchone()
        replication_target = row["parallel_item_id"] if row else None

    falsifying = {h["falsifying_task"]: h for h in hypotheses if h["falsifying_task"]}
    hypothesis_competencies = {h["target_construct"].split(":", 1)[0]: h for h in hypotheses}

    targets = {c.competency_id: target_difficulty(conn, student_id, c.competency_id, cfg, last)
               for c in pool}
    need_pos = cfg.require("mastery.success_confirmation_required")
    confirmation_targets = {
        c.competency_id: _levels_awaiting_confirmation(
            level_tally(conn, student_id, c.competency_id), need_pos)
        for c in pool
    }

    for candidate in pool:
        breakdown: dict[str, float] = {}
        status = nodes.get(candidate.competency_id, "UNKNOWN")

        breakdown["information_need"] = w["information_need"] * float(
            need_by_status.get(status, need_by_status.get("UNKNOWN", 1.0)))
        breakdown["facet_novelty"] = w["facet_novelty"] * _facet_novelty(
            conn, student_id, candidate)

        discrimination, hypothesis_id = _discrimination(
            conn, candidate, falsifying, hypothesis_competencies)
        breakdown["hypothesis_discrimination"] = w["hypothesis_discrimination"] * discrimination
        candidate.hypothesis_id = hypothesis_id

        distance = abs(_difficulty_index(candidate.difficulty)
                       - _difficulty_index(targets[candidate.competency_id]))
        breakdown["boundary_value"] = w["boundary_value"] * (
            1.0 - distance / (len(DIFFICULTIES) - 1))

        # §41: SECURE darf erst behauptet werden, wenn die Beobachtung bestaetigt
        # ist. Solange eine Stufe auf ihre Bestaetigung wartet, ist das Item auf
        # genau dieser Stufe das wertvollste - §98 erwartet deshalb ausdruecklich
        # keine unnoetigen Aufgaben auf anderen Stufen.
        #
        # Der Bonus greift nur, wenn die Bestaetigungsstufe auch die ZIELSTUFE
        # ist. Damit hat der Sprung aus §34 Vorrang: §98 fuehrt "Start D3 -> D5"
        # vor, also erst die Obergrenze suchen, dann bestaetigen. Ohne diese
        # Kopplung wuerde die Bestaetigung den Sprung verhindern.
        awaits_confirmation = candidate.difficulty in confirmation_targets.get(
            candidate.competency_id, ())
        at_target = candidate.difficulty == targets[candidate.competency_id]
        breakdown["confirmation"] = w["confirmation"] * (
            1.0 if awaits_confirmation and at_target else 0.0)

        # §25, §52, §58: die diagnostische Einheit ist die Aufgabenfamilie, nicht
        # das Einzelitem. Eine halb bearbeitete Contrast-Familie liefert keinen
        # Vergleich - §52 sagt ausdruecklich, dass daraus nicht auf "Addition
        # sicher/unsicher" geschlossen werden darf.
        breakdown["family_completion"] = w["family_completion"] * _family_completion(
            conn, student_id, candidate)

        breakdown["transfer_value"] = w["transfer_value"] * _transfer_value(
            conn, student_id, candidate, cfg)

        # §87/§94: die angegebene Klassenstufe ist der Bezugsrahmen, aus dem
        # heraus gesucht wird. Der Filter in candidates() nimmt nur weg, was
        # oberhalb liegt; welcher der verbliebenen Einstiege der naheliegende
        # ist, entscheidet dieser Summand. Ohne ihn begaenne eine Zehntklaesslerin
        # beim Punktezaehlen, weil ein unberuehrter Knoten den hoechsten
        # information_need traegt - fachlich die falsche Richtung: §36 sucht
        # rueckwaerts, und rueckwaerts faengt oben an. Das Gewicht steht wie
        # alle uebrigen in system_config (§68, §84); ohne Stufenangabe ist der
        # Summand 0 und nichts aendert sich.
        breakdown["grade_fit"] = w["grade_fit"] * _grade_fit(candidate, grade)

        breakdown["redundancy"] = -w["redundancy"] * _redundancy(
            conn, student_id, candidate, cfg)

        breakdown["estimated_cost"] = -w["estimated_cost"] * _cost(
            conn, candidate.task_id, cost_reference)

        route = route_by_task.get(candidate.task_id) \
            or route_by_competency.get(candidate.competency_id)

        # Der generische Fall von §30. Er greift nur, wenn keine Route dieses
        # Item ohnehin schon traegt - sonst wuerde dieselbe Prioritaet aus §67
        # zweimal bezahlt. Wo der Inhalt eine Route gesetzt hat, gilt der
        # Inhalt; wo er schweigt, gilt die Regel aus §30.
        if candidate.task_id == replication_target and not route:
            breakdown["replication"] = w["replication"]
            candidate.reason = "REPLICATE_ERROR"

        if route:
            # §67 Priorisierung: eine konkrete Route aus §69/§70/§83/§92/§93
            # schlaegt die generische Bewertung. Die Prioritaet der Route
            # skaliert den Bonus, damit REPLICATE_ERROR (100) vor
            # CEILING_SEARCH (50) kommt.
            breakdown["route"] = w["route"] * (route["priority"] / 100.0)
            candidate.route_id = route["route_id"]
            candidate.reason = route["reason"]

        candidate.breakdown = {k: round(v, 4) for k, v in breakdown.items()}
        candidate.score = round(sum(breakdown.values()), 4)
        if candidate.reason is None:
            candidate.reason = _implicit_reason(candidate, discrimination, status)

    pool.sort(key=lambda c: (-c.score, _difficulty_index(c.difficulty), c.task_id))
    return pool


def _facet_novelty(conn: sqlite3.Connection, student_id: str, candidate: Candidate) -> float:
    """Anteil der Merkmalswerte dieses Items, zu denen noch keine Beobachtung
    vorliegt. Setzt §19 und §71 um: zwei Aufgaben derselben Kompetenz sind nicht
    austauschbar, also ist ein Item mit unbekannten Merkmalen informativer."""
    features = task_features(conn, candidate.task_id)
    values = {(k, v) for k, vs in features.items() for v in vs}
    values.add(("REPRESENTATION_MODE", candidate.representation))
    values.add(("INTERNAL_DIFFICULTY", candidate.difficulty))
    if not values:
        return 0.0
    known = facets_of(conn, student_id, candidate.competency_id)
    unseen = sum(1 for kind, value in values if value not in known.get(kind, {}))
    return unseen / len(values)


def _discrimination(conn: sqlite3.Connection, candidate: Candidate,
                    falsifying: dict, hypothesis_competencies: dict) -> tuple[float, str | None]:
    """§67 Prioritaet 2: Hypothesen unterscheiden. §115: das widerlegende Item
    ist das wertvollste, weil nur es die Hypothese kippen kann."""
    if candidate.task_id in falsifying:
        return 1.0, falsifying[candidate.task_id]["hypothesis_id"]
    hypothesis = hypothesis_competencies.get(candidate.competency_id)
    if hypothesis is None:
        return 0.0, None
    if candidate.purpose == "CONTRAST":
        return 0.6, hypothesis["hypothesis_id"]
    return 0.3, hypothesis["hypothesis_id"]


def _grade_fit(candidate: Candidate, grade: int | None) -> float:
    """Naehe eines Items zur angegebenen Klassenstufe (§87, §94).

    1.0, solange die Stufe im Bezugsrahmen des Items liegt; darunter faellt
    der Wert linear ab, Stufe fuer Stufe. Der Abfall ist eine Reihenfolge,
    keine Bewertung: ein weiter unten liegendes Item ist nicht weniger wert,
    es ist nur der spaetere Schritt der Rueckwaertssuche aus §36. Items ohne
    Bezugsrahmen bekommen keinen Vorzug und keinen Abschlag.
    """
    if grade is None or candidate.grade_max is None:
        return 0.0
    if candidate.grade_min is not None and grade < candidate.grade_min:
        return 0.0  # oberhalb der Stufe - candidates() hat das bereits entfernt
    if grade <= candidate.grade_max:
        return 1.0
    return max(0.0, 1.0 - (grade - candidate.grade_max) / 10.0)


def _transfer_value(conn: sqlite3.Connection, student_id: str, candidate: Candidate,
                    cfg: Config) -> float:
    """§72 und §91: Transfer erst, wenn die Kompetenz belegt ist. §54: ein
    Ceiling-Item ist nur oberhalb einer gesicherten Stufe informativ."""
    if candidate.purpose not in ("TRANSFER", "CEILING"):
        return 0.0
    row = conn.execute(
        "SELECT direct_evidence_score, current_floor FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?",
        (student_id, candidate.competency_id)).fetchone()
    if not row or (row["direct_evidence_score"] or 0) <= 0:
        return 0.0
    if candidate.purpose == "TRANSFER":
        already = conn.execute(
            "SELECT COUNT(*) AS n FROM evidence_events WHERE student_id = ?"
            " AND competency_id = ? AND evidence_type = 'TRANSFER_EVIDENCE'",
            (student_id, candidate.competency_id)).fetchone()["n"]
        return 0.0 if already else 1.0
    floor = row["current_floor"]
    if not floor:
        return 0.0
    return 1.0 if _difficulty_index(candidate.difficulty) > _difficulty_index(floor) else 0.0


def _levels_awaiting_confirmation(tally: dict[str, dict[str, int]],
                                  need_pos: int) -> tuple[str, ...]:
    """Stufen mit Erfolg, aber noch nicht genug Erfolgen (§41)."""
    return tuple(level for level, b in tally.items()
                 if 0 < b["pos"] < need_pos and b["neg"] == 0)


def _family_completion(conn: sqlite3.Connection, student_id: str,
                       candidate: Candidate) -> float:
    """1.0, wenn das Item eine angefangene diagnostische Familie vervollstaendigt.

    Gilt fuer CONTRAST_ITEM, PARALLEL_ITEM und REPRESENTATION_VARIATION: bei
    allen drei entsteht der diagnostische Wert erst aus dem Vergleich (§25,
    §52, §58, §116).
    """
    row = conn.execute(
        "SELECT f.task_family_id, f.family_type FROM tasks t"
        " JOIN task_families f ON f.task_family_id = t.task_family_id"
        " WHERE t.task_id = ?", (candidate.task_id,)).fetchone()
    if not row or row["family_type"] not in (
            "CONTRAST_ITEM", "PARALLEL_ITEM", "REPRESENTATION_VARIATION"):
        return 0.0
    administered = conn.execute(
        "SELECT COUNT(DISTINCT a.task_id) AS n FROM task_attempts a"
        " JOIN tasks t ON t.task_id = a.task_id"
        " WHERE a.student_id = ? AND t.task_family_id = ?",
        (student_id, row["task_family_id"])).fetchone()["n"]
    return 1.0 if administered > 0 else 0.0


def _redundancy(conn: sqlite3.Connection, student_id: str, candidate: Candidate,
                cfg: Config) -> float:
    """§73: Ziel ist maximal relevante, nicht maximale Datenerhebung.
    §41 max_same_level_items begrenzt Items derselben Stufe.

    Items DERSELBEN Aufgabenfamilie werden nicht mitgezaehlt: §116 verlangt fuer
    ein Parallel- oder Contrast-Item ausdruecklich gleiche Stufe und gleiche
    Darstellung. Wuerde die Redundanzstrafe das treffen, wuerde sie genau die
    Wiederholung bestrafen, die §25 und §30 fordern.
    """
    same_level = conn.execute(
        "SELECT COUNT(*) AS n FROM task_attempts a JOIN tasks t ON t.task_id = a.task_id"
        " WHERE a.student_id = ? AND t.primary_competency = ?"
        " AND t.internal_difficulty = ? AND t.representation_mode = ?"
        " AND (t.task_family_id IS NULL OR t.task_family_id <> COALESCE("
        "        (SELECT task_family_id FROM tasks WHERE task_id = ?), ''))",
        (student_id, candidate.competency_id, candidate.difficulty,
         candidate.representation, candidate.task_id)).fetchone()["n"]
    limit = cfg.require("mastery.max_same_level_items")
    return min(1.0, same_level / limit) if limit else 0.0


def _cost(conn: sqlite3.Connection, task_id: str, reference: float) -> float:
    row = conn.execute(
        "SELECT estimated_time_seconds FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    seconds = row["estimated_time_seconds"]
    if seconds is None:
        # §81 fuehrt das Feld, §42-57 fuellen es nicht. Neutraler Mittelwert
        # statt einer geratenen Dauer.
        return 0.5
    return min(1.0, seconds / reference)


def _implicit_reason(candidate: Candidate, discrimination: float, status: str) -> str:
    if discrimination >= 1.0:
        return "DISCRIMINATE_HYPOTHESIS"
    if candidate.purpose == "TRANSFER":
        return "TRANSFER_CHECK"
    if candidate.purpose == "CEILING":
        return "CEILING_SEARCH"
    if status == "SUPPORT_FOCUS":
        return "SUPPORT_ROUTE"
    if status == "REACTIVATED":
        return "UPDATE_EVIDENCE"
    return "LOCATE_BOUNDARY"


# ------------------------------------------------------------ Entscheidung (§89)


def next_task(conn: sqlite3.Connection, student_id: str, cfg: Config, clock: Clock,
              last: dict | None = None, focus: set[str] | None = None) -> Decision:
    """§119. Liefert immer eine Entscheidung - auch die Entscheidung, nicht
    weiter zu testen (§73).

    focus schraenkt den aktiven Teilgraphen auf die genannten Kompetenzen ein.
    Das ist die Umsetzung von §3: "Die Lehrkraft kann Aufgaben auswaehlen,
    Aufgaben sperren, Foerderpfade veraendern, Systementscheidungen
    uebersteuern." Ohne focus entscheidet das System frei ueber alle aktiven
    Knoten (§37, §74). Voraussetzungen eines Fokusknotens bleiben zugaenglich,
    sonst waere die Rueckwaertssuche aus §36 abgeschnitten.
    """
    trigger_review_reactivation(conn, student_id, cfg, clock)
    trigger_prerequisite_reactivation(conn, student_id, cfg, clock)

    grade = student_grade(conn, student_id)
    nodes = active_nodes(conn, student_id, cfg, grade)
    if focus:
        # Strikt: nur die genannten Knoten. Voraussetzungen kommen nicht
        # automatisch hinzu - mit einem dichten Graphen (§11) waere das halbe
        # Netz drin und die Einschraenkung wirkungslos. Eine Voraussetzung
        # erreicht der Pool weiterhin ueber eine Route mit
        # reason CHECK_PREREQUISITE (§69, §70), also genau dann, wenn eine
        # fachliche Regel sie verlangt - nicht schon, weil sie existiert.
        nodes = {k: v for k, v in nodes.items() if k in focus}
    hypotheses = open_hypotheses(conn, student_id)

    routes: list[dict] = []
    if last:
        routes = matching_routes(conn, student_id, last["task_id"], last["is_correct"],
                                 last.get("error_codes", []), last.get("repeated", False))
        routes = _drop_satisfied_routes(conn, student_id, routes)
    forced = {r["target_competency"] for r in routes if r["target_competency"]}
    forced |= {_competency_of(conn, r["target_task"]) for r in routes if r["target_task"]}
    forced.discard(None)
    forced_tasks = {r["target_task"] for r in routes if r["target_task"]}

    exclusions: dict = {}
    pool = candidates(conn, student_id, cfg, nodes, forced, forced_tasks, exclusions, grade)
    pool = score_candidates(conn, student_id, cfg, pool, nodes, hypotheses, routes,
                            last, grade)

    max_alternatives = cfg.require("routing.decision_log_alternatives")
    alternatives = [{"task_id": c.task_id, "score": c.score, "reason": c.reason,
                     "route_id": c.route_id} for c in pool[:max_alternatives]]

    if not pool:
        termination = _termination_state(conn, student_id, cfg, focus, exclusions,
                                         hypotheses, grade)
        stop = termination["stop_reason"]
        decision = Decision(
            decision_id=ids.next_id(conn, "routing_decisions", student_id),
            selected_task=None, reason=None, rule_triggered=stop, confidence="HIGH" if termination["diagnostically_complete"] else "LOW",
            alternatives=[], breakdown={}, hypothesis_used=[h["hypothesis_id"] for h in hypotheses],
            evidence_used=[], stop_reason=stop,
            explanation=_explain_stop(stop), termination=termination)
        _log(conn, student_id, decision, last, clock)
        return decision

    winner = pool[0]
    margin = winner.score - (pool[1].score if len(pool) > 1 else 0.0)
    confidence = _confidence(winner, margin, cfg)

    decision = Decision(
        decision_id=ids.next_id(conn, "routing_decisions", student_id),
        selected_task=winner.task_id, reason=winner.reason,
        rule_triggered=winner.route_id or f"SCORE:{winner.reason}",
        confidence=confidence, alternatives=alternatives, breakdown=winner.breakdown,
        hypothesis_used=[winner.hypothesis_id] if winner.hypothesis_id else [],
        evidence_used=_evidence_used(conn, student_id, winner.competency_id),
        explanation=_explain(conn, student_id, winner, margin, hypotheses, last))
    _log(conn, student_id, decision, last, clock)
    return decision


def _confidence(winner: Candidate, margin: float, cfg: Config) -> str:
    """§88 verlangt eine Konfidenzangabe LOW/MEDIUM/HIGH in der
    Lehrkraftansicht. Sie beschreibt die Sicherheit der AUSWAHL, nicht die
    Sicherheit einer Aussage ueber die Schueler:in."""
    high = cfg.require("routing.confidence_high_margin")
    medium = cfg.require("routing.confidence_medium_margin")
    if winner.route_id and margin >= high:
        return "HIGH"
    if winner.route_id or margin >= high:
        return "MEDIUM"
    return "MEDIUM" if margin >= medium else "LOW"


def _evidence_used(conn: sqlite3.Connection, student_id: str, competency_id: str) -> list[str]:
    return [r["evidence_id"] for r in conn.execute(
        "SELECT evidence_id FROM evidence_events WHERE student_id = ? AND competency_id = ?"
        " ORDER BY created_at DESC, evidence_id DESC LIMIT 5", (student_id, competency_id))]


def _explain(conn: sqlite3.Connection, student_id: str, winner: Candidate, margin: float,
             hypotheses: list[dict], last: dict | None) -> str:
    """Begruendung im Format von §88.

        System:     ZO09 SUPPORT_FOCUS
        Reason:     2 structurally similar symbolic errors + 2 correct iconic items
        Hypothesis: representation-related difference
        Confidence: LOW/MEDIUM/HIGH
        Next:       mixed representation task
    """
    parts = [f"Naechste Aufgabe {winner.task_id} fuer {winner.competency_id}"
             f" ({winner.difficulty}, {winner.representation})."]
    if winner.route_id:
        row = conn.execute(
            "SELECT reason, spec_section, notes FROM task_routes WHERE route_id = ?",
            (winner.route_id,)).fetchone()
        parts.append(f"Ausgeloest durch Route {winner.route_id} ({row['reason']},"
                     f" {row['spec_section']}).")
    else:
        parts.append(f"Ausgewaehlt nach Score, Begruendung {winner.reason}.")
    if winner.hypothesis_id:
        hypothesis = next((h for h in hypotheses
                           if h["hypothesis_id"] == winner.hypothesis_id), None)
        if hypothesis:
            from .hypotheses import describe
            parts.append(f"Offene Hypothese: {describe(hypothesis)}")
    if last:
        parts.append(f"Vorherige Aufgabe {last['task_id']}:"
                     f" {'richtig' if last['is_correct'] else 'falsch'}.")
    top = ", ".join(f"{k}={v}" for k, v in sorted(winner.breakdown.items()) if v)
    parts.append(f"Score {winner.score} (Abstand zur naechsten Alternative"
                 f" {round(margin, 4)}); Summanden: {top}.")
    return " ".join(parts)


def _termination_state(conn, student_id, cfg, focus, exclusions, hypotheses, grade=None):
    states = {r["competency_id"]: r["status"] for r in conn.execute(
        "SELECT competency_id,status FROM student_competency_state WHERE student_id=?", (student_id,))}
    # Der Pruefumfang ist das, worueber ueberhaupt eine Aussage faellig waere.
    # Mit einer Klassenstufe gehoert dazu, was diese Stufe schon kennt (§94) -
    # nicht der ganze Katalog. Ohne Stufenangabe bleibt es der MVP-Umfang.
    targets = set(focus) if focus else {r["competency_id"] for r in conn.execute(
        "SELECT competency_id FROM competencies WHERE is_mvp = 1"
        " OR (? IS NOT NULL AND grade_reference_min IS NOT NULL"
        "     AND grade_reference_min <= ?)", (grade, grade))}
    open_areas, blocked = [], []
    for cid in sorted(targets):
        status = states.get(cid, "UNKNOWN")
        if status in ("SECURE", "PARKED"):
            continue
        reasons = exclusions.get(cid, {})
        if not reasons:
            count = conn.execute("SELECT COUNT(*) FROM tasks WHERE primary_competency=?", (cid,)).fetchone()[0]
            reason = "NO_ITEMS" if not count else ("BLOCKED" if status == "BLOCKED" else "NOT_IN_CANDIDATE_SCOPE")
            reasons = {reason: []}
        entry = {"competency_id": cid, "status": status, "exclusion_reasons": reasons}
        (blocked if status == "BLOCKED" else open_areas).append(entry)
    remaining_hypotheses = [h["hypothesis_id"] for h in hypotheses
                           if h["target_construct"].split(":",1)[0] in targets]
    complete = bool(targets) and not open_areas and not blocked and not remaining_hypotheses
    reason_codes = {k for a in open_areas+blocked for k in a["exclusion_reasons"]}
    if complete:
        reason = "ALL_NODES_SUFFICIENTLY_INFORMED"
    elif "NODE_TASK_LIMIT" in reason_codes:
        reason = "NODE_TASK_LIMIT_REACHED"
    elif blocked and not open_areas:
        reason = "TARGETS_BLOCKED"
    else:
        reason = "NO_ELIGIBLE_CANDIDATES"
    return {"stop_reason": reason, "technical_ended": True,
            "diagnostically_complete": complete, "scope": sorted(targets),
            "open_areas": open_areas, "blocked_areas": blocked,
            "open_hypotheses": remaining_hypotheses}


def _explain_stop(stop: str) -> str:
    if stop == "ALL_NODES_SUFFICIENTLY_INFORMED":
        return "§73: Alle Ziele im angegebenen Prüfumfang sind gesichert oder geparkt; keine offene Hypothesenprüfung. Keine Aussage über nicht geprüfte Inhalte."
    if stop == "NODE_TASK_LIMIT_REACHED":
        return "Keine auswählbare Folgeaufgabe; mindestens ein offener Bereich hat das Aufgabenlimit erreicht. Die Diagnostik ist nicht vollständig abgeschlossen."
    if stop == "TARGETS_BLOCKED":
        return "Verbleibende Ziele sind gesperrt. Dies ist ein technischer Abschluss, kein Kompetenznachweis."
    return "Keine geeignete Folgeaufgabe verfügbar. Offene Bereiche und Ausschlussgründe bleiben ausgewiesen; ausreichende diagnostische Information ist nicht bestätigt."


def _log(conn: sqlite3.Connection, student_id: str, decision: Decision,
         last: dict | None, clock: Clock) -> None:
    """§89 Explainability Logging."""
    conn.execute(
        "INSERT INTO routing_decisions (decision_id, student_id, timestamp, previous_task,"
        " selected_task, rule_triggered, evidence_used, hypothesis_used,"
        " alternatives_considered, score_breakdown, confidence)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (decision.decision_id, student_id, clock.now_iso(),
         last["task_id"] if last else None, decision.selected_task,
         decision.rule_triggered, json.dumps(decision.evidence_used),
         json.dumps(decision.hypothesis_used),
         json.dumps(decision.alternatives, ensure_ascii=False),
         json.dumps({**decision.breakdown, **({"_termination": decision.termination} if decision.termination else {})}), decision.confidence))
