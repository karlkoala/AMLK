"""Simulation der sechs Testfaelle (Sprint 12, §98 bis §103).

§123 Kriterium 20: "die sechs Testfaelle erzeugen unterschiedliche erwartete
Pfade." Das ist die eigentliche Abnahme des MVP - nicht ob einzelne Funktionen
laufen, sondern ob dasselbe System bei unterschiedlichem Antwortverhalten
unterschiedliche, fachlich begruendete Wege waehlt.

Eine Antwortpolitik entscheidet je Aufgabe, ob richtig oder falsch geantwortet
wird. Die falsche Antwort wird nicht zufaellig gewaehlt, sondern plausibel: bei
508 wird 58 geantwortet (das Musterbeispiel aus §66), bei einer Zaehlaufgabe
wird ein Objekt uebersprungen. Nur so entstehen die Fehlercodes aus §59, an
denen sich das Routing entscheidet.

§102 ist der schaerfste Testfall: zwei Schueler:innen geben auf dasselbe Item
dieselbe falsche Antwort und muessen trotzdem auf unterschiedliche Lernpfade
geraten. Wenn das nicht funktioniert, ist das System ein Quizsystem (§124).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable

from . import attempts, renderer, teacher
from .attempts import Submission, task_features
from .clock import Clock, FixedClock
from .config import Config
from .routing import Decision
from .session import Session, Turn

#: Eine Politik bekommt die Aufgabe und ihre Merkmale und sagt, ob die
#: Schueler:in sie richtig loest.
Policy = Callable[[dict, dict[str, set[str]]], bool]


# ------------------------------------------------------------ Antwortbildung


def correct_answer_for(task: dict) -> Any:
    """Die richtige Antwort in der Form, die die Oberflaeche abgeben wuerde."""
    correct = json.loads(task["correct_answer"])
    rule = task["scoring_rule"]
    if rule == "EXACT_NUMERIC":
        return correct["value"]
    if rule in ("SEQUENCE_EXACT", "SET_EXACT"):
        return correct["sequence"]
    if rule in ("SELECT_ONE", "SELECT_MULTIPLE", "BOOLEAN"):
        return correct["selection"]
    if rule == "ANY_OF_ACCEPTED":
        return correct["accepted"][0]
    if rule == "EXPRESSION_EQUIVALENT":
        return correct.get("expression", correct.get("value"))
    if rule == "INTERACTION_COUNT":
        return {"interactions": correct["interactions"]}
    if rule == "PLACED_OBJECT_COUNT":
        return {"placed": correct["placed"]}
    if rule == "GROUP_PARTITION":
        return {k: v for k, v in correct.items() if isinstance(v, (int, float))}
    raise ValueError(f"Unbekannte scoring_rule {rule}")


def plausible_wrong_answer(conn: sqlite3.Connection, task: dict,
                           features: dict[str, set[str]]) -> Any:
    """Eine falsche Antwort, die einem benennbaren Muster folgt.

    Die Reihenfolge ist wichtig: zuerst die strukturell bedeutsamen Fehler aus
    §52, §66 und §50, dann allgemeinere. Eine zufaellige Falschantwort wuerde
    nur ERR_SINGLE erzeugen und das Routing nichts lernen lassen.
    """
    correct = json.loads(task["correct_answer"])
    payload = json.loads(task["task_payload"])
    rule = task["scoring_rule"]

    # Innerhalb einer Contrast-Familie ist die naheliegende Verwechslung die
    # Antwort des Partneritems. §50 stellt genau dafuer "Wie viele Zehner sind
    # in 430?" (43) und "Welche Ziffer steht an der Zehnerstelle?" (3)
    # gegenueber - wer die Frage verwechselt, antwortet mit der anderen Zahl.
    partner = _contrast_partner_answer(conn, task, correct)
    if partner is not None:
        return partner

    if rule == "EXACT_NUMERIC":
        value = correct["value"]
        text = str(abs(int(value))) if isinstance(value, int) else None
        # §66: die unbesetzte Stelle wird nicht notiert - 508 wird 58.
        if text and len(text) >= 3 and "0" in text[1:-1]:
            return int(text[0] + text[1:-1].replace("0", "") + text[-1])
        # §50: der Stellenwert wird mit der Ziffer verwechselt - 60 wird 6.
        if "PLACE_VALUE_DECOMPOSITION" in features.get("STRUCTURAL_FEATURE", ()) \
                and isinstance(value, int) and value >= 10 and value % 10 == 0:
            return value // 10
        # Zweistellige Ziffernvertauschung, sonst Abweichung um eins.
        if isinstance(value, int) and value >= 10:
            digits = str(value)
            swapped = int(digits[:-2] + digits[-1] + digits[-2]) if len(digits) >= 2 else value
            if swapped != value:
                return swapped
        return (value + 1) if isinstance(value, (int, float)) else value

    if rule in ("SEQUENCE_EXACT", "SET_EXACT"):
        sequence = list(correct["sequence"])
        sequence[-1] = sequence[-1] + 1
        return sequence

    if rule in ("SELECT_ONE", "BOOLEAN"):
        options = payload.get("options") or []
        expected = correct["selection"]
        for option in options:
            if str(option) != str(expected):
                return option
        return f"NICHT-{expected}"

    if rule == "SELECT_MULTIPLE":
        options = payload.get("options") or []
        expected = {str(v) for v in correct["selection"]}
        wrong = [o for o in options if str(o) not in expected]
        return [wrong[0]] if wrong else []

    if rule == "ANY_OF_ACCEPTED":
        return "0+0"

    if rule == "EXPRESSION_EQUIVALENT":
        expression = str(correct.get("expression", ""))
        # Operation vertauschen: erzeugt ERR_OPERATION_SELECTION statt ERR_SINGLE.
        for old, new in (("+", "-"), ("*", ":"), ("-", "+"), (":", "*")):
            if old in expression:
                return expression.replace(old, new, 1)
        return "0"

    if rule == "INTERACTION_COUNT":
        return {"interactions": max(0, correct["interactions"] - 1)}
    if rule == "PLACED_OBJECT_COUNT":
        return {"placed": max(0, correct["placed"] - 1)}
    if rule == "GROUP_PARTITION":
        # Die Felder vertauschen: beim Verteilen und Aufteilen (§55) ist genau
        # das die naheliegende Verwechslung, beim Buendeln der Stellenwertdreher.
        numeric = {k: v for k, v in correct.items() if isinstance(v, (int, float))}
        keys = sorted(numeric)
        if len(keys) >= 2 and numeric[keys[0]] != numeric[keys[1]]:
            return {keys[0]: numeric[keys[1]], keys[1]: numeric[keys[0]]}
        return {k: v + 1 for k, v in numeric.items()}
    raise ValueError(f"Unbekannte scoring_rule {rule}")


def _contrast_partner_answer(conn: sqlite3.Connection, task: dict, correct: dict) -> Any:
    """Die richtige Antwort eines Partneritems derselben Contrast-Familie."""
    if not task["task_family_id"]:
        return None
    family = conn.execute(
        "SELECT family_type FROM task_families WHERE task_family_id = ?",
        (task["task_family_id"],)).fetchone()
    if not family or family["family_type"] != "CONTRAST_ITEM":
        return None
    for row in conn.execute(
        "SELECT correct_answer, scoring_rule FROM tasks WHERE task_family_id = ?"
        " AND task_id <> ? ORDER BY task_id", (task["task_family_id"], task["task_id"])
    ):
        if row["scoring_rule"] != task["scoring_rule"]:
            continue
        other = json.loads(row["correct_answer"])
        if other.get("value") is not None and other.get("value") != correct.get("value"):
            return other["value"]
        if (other.get("selection") is not None
                and other.get("selection") != correct.get("selection")):
            return other["selection"]
    return None


def events_for(task: dict, spec: dict, correct: bool) -> list[dict]:
    """Interaktionsereignisse nach §61.

    Bei Zaehlaufgaben verlangt §42 ausdruecklich Klickreihenfolge, ausgelassene
    Objekte und doppelte Klicks. Eine falsche Antwort wird deshalb durch ein
    uebersprungenes Objekt erzeugt, nicht nur durch eine falsche Zahl - sonst
    entstehen ERR_OMISSION und ERR_DOUBLE_COUNT nie.
    """
    mode = task["interaction_mode"]
    events: list[dict] = []
    payload = json.loads(task["task_payload"])
    total = payload.get("objects")

    if mode == "CLICK_SEQUENCE" and total:
        clicked = total if correct else max(0, total - 1)
        for i in range(clicked):
            events.append({"event_type": "CLICK", "object_id": f"obj{i + 1}"})
    elif mode == "DRAG":
        events.append({"event_type": "DRAG", "object_id": "obj1"})
        events.append({"event_type": "DROP", "object_id": "obj1"})
    elif mode == "SELECT":
        events.append({"event_type": "SELECT", "object_id": "option"})
    events.append({"event_type": "SUBMIT"})
    return events


# ---------------------------------------------------------------- Politiken


def policy_high_competence(task: dict, features: dict) -> bool:
    """§98 Testfall A. Loest alles."""
    return True


def policy_basic_difficulty(task: dict, features: dict) -> bool:
    """§99 Testfall B. Loest nur die elementarste Stufe."""
    return task["internal_difficulty"] == "D1"


def policy_representation(task: dict, features: dict) -> bool:
    """§100 Testfall C. Symbolisch nicht, ikonisch und handelnd ja.

    §33 ist mitgedacht: unter Unterstuetzung gelingt auch die symbolische
    Aufgabe - so wird die Leiter IMAGE -> MIXED -> SYMBOL+SUPPORT -> SYMBOL
    ueberhaupt beobachtbar. Der Marker heisst deshalb REPRESENTATION_DEPENDENT
    und nicht 'visuelle:r Lerner:in' (§32).
    """
    return task["representation_mode"] != "MATHEMATICAL_SYMBOL"


def policy_number_dependency(task: dict, features: dict) -> bool:
    """§101 Testfall D. Der Erfolg haengt daran, ob der Ausgleich in der
    natuerlichen Richtung moeglich ist.

    §71 beschreibt das Muster: 49+36 und 48+37 gelingen, 37+28 und 46+27 nicht.
    Als Merkmal nennt §71 fuer die erfolgreiche Seite "NEAR_ROUND_NUMBER,
    COMPENSATION_AVAILABLE". Getrennt werden die vier Items nur durch das
    zweite: nach der operandensymmetrischen Regel traegt auch 37+28 einen
    runden Anker (28 ist 2 von 30), aber der Ausgleich muesste dort den
    Ausgangswert nach unten anpassen (37+28 = 35+30) statt nach oben
    (49+36 = 50+35). Siehe ENTSCHEIDUNGEN.md D-19 und F-25.

    Erwartung: das System stuft Addition NICHT pauschal herab, sondern
    vergleicht Merkmale und waehlt ein Contrast Item.
    """
    if "TWO_DIGIT_ADDITION" not in features.get("STRUCTURAL_FEATURE", ()):
        return True
    return "COMPENSATION" in features.get("STRATEGY_AFFORDANCE", ())


def policy_multiplication_representation(task: dict, features: dict) -> bool:
    """§102 Testfall E, Schueler:in A. Symbolisch nicht, ikonisch ja."""
    return task["representation_mode"] != "MATHEMATICAL_SYMBOL"


def policy_multiplication_concept(task: dict, features: dict) -> bool:
    """§102 Testfall E, Schueler:in B. Auch ikonisch und beim Gruppieren nicht."""
    return False


# ------------------------------------------------------------------- Ablauf


@dataclass
class Step:
    turn_index: int
    task_id: str
    competency_id: str
    difficulty: str
    representation: str
    purpose: str
    is_correct: bool
    error_codes: list[str]
    selected_by: str | None
    confidence: str | None
    state_changes: list[tuple[str, str | None, str]] = field(default_factory=list)
    hypothesis_actions: list[str] = field(default_factory=list)
    transitions: list[str] = field(default_factory=list)
    next_task: str | None = None
    next_reason: str | None = None
    explanation: str = ""


@dataclass
class Trace:
    student_id: str
    policy_name: str
    steps: list[Step] = field(default_factory=list)
    stop_reason: str | None = None

    @property
    def task_ids(self) -> list[str]:
        return [s.task_id for s in self.steps]

    @property
    def difficulties(self) -> list[str]:
        return [s.difficulty for s in self.steps]

    @property
    def representations(self) -> list[str]:
        return [s.representation for s in self.steps]

    def error_codes(self) -> set[str]:
        return {c for s in self.steps for c in s.error_codes}

    def hypothesis_types(self) -> set[str]:
        return {h.split(":", 1)[0] for s in self.steps for h in s.hypothesis_actions}

    def transitions(self) -> list[str]:
        return [t for s in self.steps for t in s.transitions]


def run(conn: sqlite3.Connection, student_id: str, policy: Policy, clock: Clock,
        focus: set[str] | None = None, max_turns: int = 20,
        session: Session | None = None, support_after_symbolic_failures: int = 0,
        cfg: Config | None = None, first_task: str | None = None) -> tuple[Trace, Session]:
    """Laesst eine Politik gegen die Engine spielen.

    support_after_symbolic_failures setzt §33 um: nach so vielen symbolischen
    Fehlversuchen wird Unterstuetzung angeboten. 0 schaltet das ab.

    first_task setzt die Einstiegsaufgabe. §3: "Die Lehrkraft kann Aufgaben
    auswaehlen." Die Testfaelle in §98 bis §103 beginnen jeweils an einem
    benannten Item; nur mit gesetztem Einstieg sind sie reproduzierbar. Ab der
    zweiten Aufgabe entscheidet ausschliesslich die Engine.
    """
    session = session or Session(conn, student_id, clock, cfg=cfg, focus=focus)
    trace = Trace(student_id=student_id,
                  policy_name=getattr(policy, "__name__", "policy"))
    symbolic_failures = 0

    for index in range(max_turns):
        if index == 0 and first_task:
            decision = Decision(
                decision_id="-", selected_task=first_task, reason="TEACHER_SELECTED",
                rule_triggered="§3 Lehrkraftauswahl", confidence="HIGH",
                alternatives=[], breakdown={}, hypothesis_used=[], evidence_used=[],
                explanation="Einstiegsaufgabe von der Lehrkraft gewaehlt (§3).")
        else:
            decision = session.next_task()
        if decision.selected_task is None:
            trace.stop_reason = decision.stop_reason
            break

        task = attempts.load_task(conn, decision.selected_task)
        features = task_features(conn, task["task_id"])
        # Der Renderer muss das Item ausliefern koennen (§113).
        spec = renderer.render(task)

        wants_correct = policy(task, features)
        support = (support_after_symbolic_failures
                   and not wants_correct
                   and task["representation_mode"] == "MATHEMATICAL_SYMBOL"
                   and symbolic_failures >= support_after_symbolic_failures)
        if support:
            wants_correct = True  # §33: unter Unterstuetzung gelingt es.

        answer = correct_answer_for(task) if wants_correct \
            else plausible_wrong_answer(conn, task, features)
        submission = Submission(
            task_id=task["task_id"], answer=answer,
            events=events_for(task, spec, wants_correct),
            time_seconds=None, support_used=bool(support),
            selected_by_reason=decision.reason, selected_by_rule=decision.rule_triggered)

        clock_advance(clock)
        turn = session.submit(submission)

        if not turn.is_correct and task["representation_mode"] == "MATHEMATICAL_SYMBOL":
            symbolic_failures += 1

        trace.steps.append(Step(
            turn_index=index, task_id=task["task_id"],
            competency_id=task["primary_competency"],
            difficulty=task["internal_difficulty"],
            representation=task["representation_mode"],
            purpose=task["task_purpose"],
            is_correct=turn.is_correct, error_codes=turn.error_codes,
            selected_by=decision.rule_triggered, confidence=decision.confidence,
            state_changes=turn.state_changes,
            hypothesis_actions=[f"{a.hypothesis_type}:{a.action}"
                                for a in turn.hypothesis_actions],
            transitions=[f"{t.competency_id}:{t.from_status}->{t.to_status}"
                         f"{'(' + t.reason + ')' if t.reason else ''}"
                         for t in turn.transitions],
            next_task=turn.next_decision.selected_task if turn.next_decision else None,
            next_reason=turn.next_decision.reason if turn.next_decision else None,
            explanation=turn.next_decision.explanation if turn.next_decision else ""))

        if turn.next_decision and turn.next_decision.selected_task is None:
            trace.stop_reason = turn.next_decision.stop_reason
            break

    return trace, session


def clock_advance(clock: Clock) -> None:
    if isinstance(clock, FixedClock):
        clock.advance(minutes=2)


def render_trace(trace: Trace) -> str:
    lines = [f"TESTFALL {trace.policy_name}  Schueler:in {trace.student_id}", ""]
    for step in trace.steps:
        mark = "richtig" if step.is_correct else "FALSCH "
        lines.append(f"{step.turn_index + 1:>2}. {step.task_id:<24}"
                     f" {step.difficulty} {step.representation:<20} {step.purpose:<9} {mark}")
        if step.error_codes:
            lines.append(f"      Beobachtung  {', '.join(step.error_codes)}")
        for competency, before, after in step.state_changes:
            lines.append(f"      Status       {competency}: {before} -> {after}")
        for action in step.hypothesis_actions:
            lines.append(f"      Hypothese    {action}")
        for transition in step.transitions:
            lines.append(f"      Uebergang    {transition}")
        if step.next_task:
            lines.append(f"      Naechste     {step.next_task} ({step.next_reason},"
                         f" Konfidenz {step.confidence})")
    if trace.stop_reason:
        lines.append("")
        lines.append(f"Ende: {trace.stop_reason}  (§73 - nicht uebertesten)")
    return "\n".join(lines)


# ------------------------------------------------- Die sechs Testfaelle (§98-§103)


def testfall_a(conn: sqlite3.Connection, cfg: Config) -> Trace:
    """§98 Hohe Kompetenz. Erwartung: keine unnoetigen D1/D2-Aufgaben,
    Aufstieg bis D5, Transfer, dann SECURE und PARKED."""
    clock = FixedClock()
    trace, _ = run(conn, "SIM-A", policy_high_competence, clock,
                   focus={"ZO09_MULTIPLICATION"}, max_turns=14, cfg=cfg,
                   first_task="ZO09-REL-D3-S-A")
    return trace


def testfall_b(conn: sqlite3.Connection, cfg: Config) -> Trace:
    """§99 Grundlegende Schwierigkeit. Erwartung: D3 falsch, Parallelitem
    falsch, Abstieg, Voraussetzungspruefung, Rueckwaertsnavigation,
    SUPPORT_FOCUS."""
    clock = FixedClock()
    trace, _ = run(conn, "SIM-B", policy_basic_difficulty, clock,
                   focus={"ZO06_PLACE_VALUE", "ZO06_1_BUNDLING"}, max_turns=14, cfg=cfg,
                   first_task="ZO06-D2-S-A")
    return trace


def testfall_c(conn: sqlite3.Connection, cfg: Config) -> Trace:
    """§100 Repraesentation. Erwartung: zwei symbolische Fehlversuche, zwei
    ikonische Erfolge, REPRESENTATION_HYPOTHESIS, dann gemischte bzw.
    unterstuetzte Darstellung (§33)."""
    clock = FixedClock()
    # §96 gibt D3 als Startstufe vor. Der Darstellungsvergleich in ZO06 liegt
    # nach der Reparatur aus Entscheidung D-11 auf D2 (FAM_ZO06_D2_SYMBOLIC
    # gegen FAM_ZO06_D2_ICONIC, gleiche Frageform, gleiches Antwortformat).
    # §3 erlaubt der Lehrkraft, Systementscheidungen zu uebersteuern; hier wird
    # die Startstufe abgesenkt, damit §69 vollstaendig durchlaufen wird.
    local = Config(conn)
    local.override("routing.start_difficulty", "D2")
    trace, _ = run(conn, "SIM-C", policy_representation, clock,
                   focus={"ZO06_PLACE_VALUE"}, max_turns=16, cfg=local,
                   first_task="ZO06-D2-S-A")
    return trace


def testfall_d(conn: sqlite3.Connection, cfg: Config) -> Trace:
    """§101 Zahlen- und Strategieabhaengigkeit. Erwartung: Addition wird NICHT
    pauschal herabgestuft, Merkmale werden verglichen, eine
    STRATEGY_DEPENDENCY_HYPOTHESIS entsteht, ein Contrast Item wird gewaehlt."""
    clock = FixedClock()
    trace, _ = run(conn, "SIM-D", policy_number_dependency, clock,
                   focus={"ZO07_ADDITION"}, max_turns=16, cfg=cfg,
                   first_task="ZO07-D3-S-E")
    return trace


def testfall_e(conn: sqlite3.Connection, cfg: Config) -> tuple[Trace, Trace]:
    """§102 Gleiche Ausgangsantwort, unterschiedliche Ursache. Erwartung:
    Schueler:in A auf die Darstellungsroute, Schueler:in B auf die
    Grundvorstellungsroute."""
    trace_a, _ = run(conn, "SIM-E1", policy_multiplication_representation,
                     FixedClock(), focus={"ZO09_MULTIPLICATION"}, max_turns=14, cfg=cfg,
                     first_task="ZO09-D2-S-A")
    trace_b, _ = run(conn, "SIM-E2", policy_multiplication_concept,
                     FixedClock(), focus={"ZO09_MULTIPLICATION"}, max_turns=14, cfg=cfg,
                     first_task="ZO09-D2-S-A")
    return trace_a, trace_b


def testfall_f(conn: sqlite3.Connection, cfg: Config) -> tuple[Trace, Trace]:
    """§103 Wiederaktivierung. Phase 1: ZO06 wird gesichert und geparkt.
    Phase 2: spaeter treten Stellenwertfehler auf, ZO06 wird REACTIVATED und
    mit task_purpose VERIFY erneut geprueft."""
    clock = FixedClock()
    phase1, session = run(conn, "SIM-F", policy_high_competence, clock,
                          focus={"ZO06_PLACE_VALUE"}, max_turns=10, cfg=cfg,
                          first_task="ZO06-D2-S-A")
    # §39/§40: Zeit vergeht. Der Abstand liegt ueber park.evidence_too_old_days,
    # damit die Wiedervorlage aus §40 die Kompetenz mit dem Grund
    # EVIDENCE_TOO_OLD zurueckholt. §39 nennt genau diesen Grund; ohne
    # Wiedervorlage koennte ein geparkter Knoten nie zurueckkommen, weil §38 ihn
    # aus dem Aufgabenpool entfernt.
    clock.advance(days=int(cfg.require("park.evidence_too_old_days")) + 10)

    def wrong_on_place_value(task: dict, features: dict) -> bool:
        return task["primary_competency"] != "ZO06_PLACE_VALUE"

    session.focus = {"ZO06_PLACE_VALUE"}
    phase2, _ = run(conn, "SIM-F", wrong_on_place_value, clock,
                    focus={"ZO06_PLACE_VALUE"}, max_turns=8, session=session, cfg=cfg)
    return phase1, phase2


def run_all(conn: sqlite3.Connection, cfg: Config | None = None) -> dict[str, Any]:
    """Alle sechs Testfaelle. Grundlage fuer §123 Kriterium 20."""
    cfg = cfg or Config(conn)
    e1, e2 = testfall_e(conn, cfg)
    f1, f2 = testfall_f(conn, cfg)
    return {
        "A": testfall_a(conn, cfg),
        "B": testfall_b(conn, cfg),
        "C": testfall_c(conn, cfg),
        "D": testfall_d(conn, cfg),
        "E1": e1, "E2": e2,
        "F1": f1, "F2": f2,
    }
