"""Auswertung einer Antwort und Klassifikation beobachtbarer Fehler.

Sprint 4/5. Zwei streng getrennte Schritte:

  score()    Ist die Antwort richtig? Rein mechanisch, nach scoring_rule.
  classify() Welche BEOBACHTUNG liegt vor? Liefert Fehlercodes nach §59.

§29 ist bindend: "Ein Fehler ist keine Diagnose." Dieses Modul erzeugt
ausschliesslich Beobachtungen. Es setzt keinen Kompetenzstatus, eroeffnet keine
Hypothese und trifft keine Aussage ueber die Schueler:in. Das ist Aufgabe von
evidence.py und hypotheses.py.

§59 ist bindend: "Fehlercodes beschreiben Beobachtungen. Keine psychologischen
Diagnosen." Jeder Detektor unten prueft eine am Datenmaterial ablesbare
Eigenschaft der Antwort, nicht eine Eigenschaft der Person.

ERR_REPRESENTATION wird hier NICHT vergeben. §32 verbietet, aus einem
Darstellungsunterschied auf eine Eigenschaft zu schliessen, und ein
Darstellungsunterschied ist an einem einzelnen Versuch ohnehin nicht ablesbar -
er entsteht erst im Vergleich mehrerer Versuche. Den Code setzt daher nur die
Evidence Engine. Siehe ENTSCHEIDUNGEN.md D-14.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------- Normalisierung

_OP_ALIASES = {"·": "*", "×": "*", "x": "*", "÷": ":", "/": ":", "−": "-", "–": "-"}


def normalize_number(value: Any) -> int | float | None:
    """Zahl aus einer Rohantwort. None, wenn es keine ist."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip().replace(".", "").replace(",", ".")
        try:
            number = float(text)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
    return None


def normalize_expression(text: Any) -> str:
    """Rechenausdruck in eine Vergleichsform bringen.

    Kommutativitaet wird beruecksichtigt: '1*8+5*8' und '5*8+1*8' sind gleich,
    '403-200+2' behaelt seine Reihenfolge, weil Subtraktion nicht kommutativ
    ist. §49 verlangt ausdruecklich, dass das Scoring nicht unnoetig nur eine
    Schreibweise akzeptiert.
    """
    if not isinstance(text, str):
        text = str(text)
    s = text.strip().lower()
    for alias, canonical in _OP_ALIASES.items():
        s = s.replace(alias, canonical)
    s = re.sub(r"\s+", "", s)

    if "=" in s:
        return "=".join(normalize_expression(part) for part in s.split("="))

    terms = re.findall(r"[+-]?[^+-]+", s)
    if not terms:
        return s

    normalized_terms = []
    for term in terms:
        sign = ""
        body = term
        if body and body[0] in "+-":
            sign, body = ("" if body[0] == "+" else "-"), body[1:]
        if "*" in body and ":" not in body:
            factors = sorted(body.split("*"))
            body = "*".join(factors)
        normalized_terms.append(sign + body)

    if all(not t.startswith("-") for t in normalized_terms):
        normalized_terms.sort()
    return "+".join(t.lstrip("+") if not t.startswith("-") else t
                    for t in normalized_terms).replace("+-", "-")


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


# ------------------------------------------------------------------- Ergebnis


@dataclass
class ScoreResult:
    is_correct: bool
    score: float
    error_codes: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)


class UndeliverableTask(Exception):
    """Das Item darf nicht ausgeliefert werden, weil fachliche Angaben fehlen.

    §113 verlangt fuer jede Aufgabe correct_answer und scoring_rule. Ein Item
    mit correct_answer.status == UNDEFINED oder options_status == UNDEFINED ist
    nach §1 unvollstaendig; es wird nicht geraten, sondern verweigert.
    """


# --------------------------------------------------------------------- Scoring


def score(task: dict, raw_answer: Any) -> ScoreResult:
    """Wertet eine Rohantwort gegen correct_answer aus."""
    rule = task["scoring_rule"]
    correct = json.loads(task["correct_answer"]) if isinstance(task["correct_answer"], str) \
        else task["correct_answer"]
    payload = json.loads(task["task_payload"]) if isinstance(task["task_payload"], str) \
        else task["task_payload"]

    if isinstance(correct, dict) and correct.get("status") == "UNDEFINED":
        raise UndeliverableTask(
            f"{task['task_id']}: correct_answer ist UNDEFINED (§1, F-18)")
    if payload.get("options_status") == "UNDEFINED":
        raise UndeliverableTask(
            f"{task['task_id']}: Auswahloptionen sind UNDEFINED (§113, F-17)")

    handler = _SCORERS.get(rule)
    if handler is None:
        raise ValueError(f"Unbekannte scoring_rule {rule} bei {task['task_id']}")
    ok = handler(correct, raw_answer, payload)
    return ScoreResult(is_correct=ok, score=1.0 if ok else 0.0,
                       detail={"rule": rule, "expected": correct, "given": raw_answer})


def _s_exact_numeric(correct, given, payload):
    return normalize_number(given) == normalize_number(correct.get("value"))


def _s_sequence_exact(correct, given, payload):
    expected = [normalize_number(v) for v in correct.get("sequence", [])]
    got = [normalize_number(v) for v in _as_list(given)]
    return got == expected


def _s_set_exact(correct, given, payload):
    expected = {normalize_number(v) for v in correct.get("sequence", correct.get("set", []))}
    got = {normalize_number(v) for v in _as_list(given)}
    return got == expected


def _s_select_one(correct, given, payload):
    expected = correct.get("selection")
    if isinstance(expected, (int, float)) or isinstance(given, (int, float)):
        if normalize_number(given) is not None and normalize_number(expected) is not None:
            return normalize_number(given) == normalize_number(expected)
    return normalize_expression(given) == normalize_expression(expected)


def _s_select_multiple(correct, given, payload):
    expected = {normalize_expression(v) for v in _as_list(correct.get("selection"))}
    got = {normalize_expression(v) for v in _as_list(given)}
    return got == expected


def _s_any_of_accepted(correct, given, payload):
    accepted = {normalize_expression(v) for v in correct.get("accepted", [])}
    return normalize_expression(given) in accepted


def _s_expression_equivalent(correct, given, payload):
    # §49: mehrere Schreibweisen sind zulaessig. Zusaetzlich gilt das nackte
    # Ergebnis als richtig, wenn correct_answer einen Wert fuehrt - die
    # Spezifikation gibt bei ZO07-D3-S-A sowohl '58+3=61' als auch 61 an.
    if normalize_expression(given) == normalize_expression(correct.get("expression", "")):
        return True
    for alt in correct.get("accepted", []):
        if normalize_expression(given) == normalize_expression(alt):
            return True
    if "value" in correct and normalize_number(given) is not None:
        return normalize_number(given) == normalize_number(correct["value"])
    return False


def _s_interaction_count(correct, given, payload):
    return normalize_number(_count_of(given, "interactions")) == \
        normalize_number(correct.get("interactions"))


def _s_placed_object_count(correct, given, payload):
    return normalize_number(_count_of(given, "placed")) == \
        normalize_number(correct.get("placed"))


def _s_group_partition(correct, given, payload):
    """Gruppierung von Objekten. Verglichen werden alle Zahlfelder der
    Musterantwort - das deckt sowohl {groups, per_group} beim Verteilen und
    Aufteilen (§55) als auch {tens, ones} beim Buendeln (§69) ab."""
    if not isinstance(given, dict):
        return False
    expected = {k: normalize_number(v) for k, v in correct.items()
                if normalize_number(v) is not None}
    if not expected:
        return False
    return all(normalize_number(given.get(k)) == v for k, v in expected.items())


def _s_boolean(correct, given, payload):
    expected = correct.get("selection", correct.get("value"))
    return str(given).strip().casefold() == str(expected).strip().casefold()


def _count_of(given: Any, key: str) -> Any:
    if isinstance(given, dict):
        return given.get(key)
    return given


_SCORERS = {
    "EXACT_NUMERIC": _s_exact_numeric,
    "SEQUENCE_EXACT": _s_sequence_exact,
    "SET_EXACT": _s_set_exact,
    "SELECT_ONE": _s_select_one,
    "SELECT_MULTIPLE": _s_select_multiple,
    "ANY_OF_ACCEPTED": _s_any_of_accepted,
    "EXPRESSION_EQUIVALENT": _s_expression_equivalent,
    "INTERACTION_COUNT": _s_interaction_count,
    "PLACED_OBJECT_COUNT": _s_placed_object_count,
    "GROUP_PARTITION": _s_group_partition,
    "BOOLEAN": _s_boolean,
}


# ------------------------------------------------------- Fehlerklassifikation


@dataclass
class ClassificationContext:
    """Alles, was ein Detektor ausser der Antwort braucht.

    selected_by_reason ist der ROUTE_REASON, mit dem das Routing dieses Item
    ausgewaehlt hat. §31 Schritt 3 unterscheidet ausdruecklich die Pruefung
    einer Voraussetzung von der Pruefung der Kompetenz selbst; ohne diesen
    Kontext waere ERR_PREREQUISITE nicht vergebbar.
    """
    features: dict[str, set[str]] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    selected_by_reason: str | None = None

    def has(self, kind: str, value: str) -> bool:
        return value in self.features.get(kind, set())


def classify(task: dict, raw_answer: Any, result: ScoreResult,
             ctx: ClassificationContext) -> list[str]:
    """Beobachtbare Fehlercodes nach §59.

    Reihenfolge der Detektoren folgt §31: erst was direkt am Verhalten
    ablesbar ist, dann was Kontext braucht. Mehrere Codes sind zulaessig -
    eine Auslassung beim Zaehlen und eine falsche Gesamtzahl sind zwei
    Beobachtungen, nicht eine.
    """
    codes: list[str] = []

    if any(e.get("event_type") == "ANSWER_CHANGE" for e in ctx.events):
        codes.append("ERR_SELF_CORRECTED")

    counting = _counting_codes(task, ctx)
    codes.extend(counting)

    if result.is_correct:
        return _dedup(codes)

    correct = json.loads(task["correct_answer"]) if isinstance(task["correct_answer"], str) \
        else task["correct_answer"]
    payload = json.loads(task["task_payload"]) if isinstance(task["task_payload"], str) \
        else task["task_payload"]

    for detector in _DETECTORS:
        code = detector(task, raw_answer, correct, payload, ctx)
        if code:
            codes.append(code)

    specific = [c for c in codes if c not in ("ERR_SELF_CORRECTED",)]
    if not specific:
        codes.append("ERR_SINGLE")
    return _dedup(codes)


def _dedup(codes: list[str]) -> list[str]:
    seen, out = set(), []
    for c in codes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _counting_codes(task: dict, ctx: ClassificationContext) -> list[str]:
    """§42 verlangt fuer Zaehlitems ausdruecklich das Speichern von
    Klickreihenfolge, ausgelassenen Objekten und doppelten Klicks."""
    payload = json.loads(task["task_payload"]) if isinstance(task["task_payload"], str) \
        else task["task_payload"]
    total = payload.get("objects")
    if total is None or task["interaction_mode"] != "CLICK_SEQUENCE":
        return []
    clicks = [e.get("object_id") for e in ctx.events
              if e.get("event_type") == "CLICK" and e.get("object_id")]
    if not clicks:
        return []
    codes = []
    if len(set(clicks)) < total:
        codes.append("ERR_OMISSION")
    if len(clicks) != len(set(clicks)):
        codes.append("ERR_DOUBLE_COUNT")
    return codes


def _d_sequence(task, given, correct, payload, ctx):
    if task["scoring_rule"] in ("SEQUENCE_EXACT", "SET_EXACT"):
        return "ERR_SEQUENCE"
    return None


def _d_cardinality(task, given, correct, payload, ctx):
    if payload.get("ask_total_after_counting"):
        return "ERR_CARDINALITY"
    return None


def _d_zero_placeholder(task, given, correct, payload, ctx):
    """§66 Musterbeispiel: 508 wurde als 58 notiert.

    Geprueft wird, ob genau die INNEREN Nullen fehlen. Eine fehlende
    Endnull (60 als 6 beantwortet) ist keine unbesetzte Stelle, sondern eine
    Stellenwertverwechslung und gehoert zu ERR_PLACE_VALUE - sonst waeren die
    beiden Codes aus §59 nicht trennscharf.
    """
    c, a = normalize_number(correct.get("value")), normalize_number(given)
    if c is None or a is None or not isinstance(c, int) or not isinstance(a, int):
        return None
    text = str(abs(c))
    if len(text) < 3 or "0" not in text[1:-1]:
        return None
    without_interior_zeros = text[0] + text[1:-1].replace("0", "") + text[-1]
    return "ERR_ZERO_PLACEHOLDER" if without_interior_zeros == str(abs(a)) else None


def _d_place_value(task, given, correct, payload, ctx):
    if not ctx.has("STRUCTURAL_FEATURE", "PLACE_VALUE_DECOMPOSITION"):
        return None
    c, a = normalize_number(correct.get("value")), normalize_number(given)
    if not isinstance(c, int) or not isinstance(a, int) or a == c:
        return None
    if sorted(str(abs(c))) == sorted(str(abs(a))):
        return "ERR_PLACE_VALUE"
    for factor in (10, 100, 1000):
        if a * factor == c or (a != 0 and a == c * factor):
            return "ERR_PLACE_VALUE"
    if a != 0 and (str(a) in str(c) or str(c) in str(a)):
        return "ERR_PLACE_VALUE"
    return None


_ADDITIVE = {"+", "-"}
_MULTIPLICATIVE = {"*", ":"}


def _operators(expression: str) -> set[str]:
    return set(re.findall(r"[+\-*:]", normalize_expression(expression)))


def _operands(expression: str) -> list[str]:
    return sorted(re.findall(r"\d+", normalize_expression(expression)))


def _d_operation(task, given, correct, payload, ctx):
    """§59 unterscheidet ERR_OPERATION_SELECTION und ERR_OPERATION_CONCEPT.
    Abgrenzung nach ENTSCHEIDUNGEN.md D-14: gleiche Operationsklasse mit
    vertauschter Richtung ist eine Auswahlverwechslung, ein Wechsel der
    Operationsklasse betrifft die Grundvorstellung."""
    expected = correct.get("selection") or correct.get("expression")
    if not isinstance(expected, str) or not isinstance(given, str):
        return None
    if not _operators(expected):
        return None
    ops_expected, ops_given = _operators(expected), _operators(given)
    if not ops_given:
        return None
    if ops_expected == ops_given:
        if _operands(expected) != _operands(given):
            return "ERR_OPERATION_SELECTION"
        return None
    same_class = (ops_expected <= _ADDITIVE and ops_given <= _ADDITIVE) or \
                 (ops_expected <= _MULTIPLICATIVE and ops_given <= _MULTIPLICATIVE)
    return "ERR_OPERATION_SELECTION" if same_class else "ERR_OPERATION_CONCEPT"


def _answer_is_expression(task, correct) -> bool:
    expected = correct.get("selection") or correct.get("expression")
    return isinstance(expected, str) and bool(_operators(expected))


def _d_strategy(task, given, correct, payload, ctx):
    """§59 ERR_STRATEGY. Nur wo die Strategie ueberhaupt beobachtbar ist,
    also wo die Antwort selbst ein Rechenweg ist. Bei einer reinen
    Ergebniseingabe waere die Vergabe eine Inferenz - §76 sieht dafuer im MVP
    kein Verfahren vor. Siehe ENTSCHEIDUNGEN.md D-14."""
    if not _answer_is_expression(task, correct):
        return None
    if payload.get("target_calculation") or ctx.has("STRATEGY_AFFORDANCE", "COMPENSATION"):
        return "ERR_STRATEGY"
    return None


def _d_calculation(task, given, correct, payload, ctx):
    if _answer_is_expression(task, correct):
        return None
    if payload.get("operation") and normalize_number(given) is not None:
        return "ERR_CALCULATION"
    return None


def _d_language_context(task, given, correct, payload, ctx):
    """Bei einer Textaufgabe wurde eine gegebene Zahl uebernommen statt
    gerechnet - an der Antwort ablesbar, keine Zuschreibung."""
    if not ctx.has("SURFACE_FEATURE", "WORD_PROBLEM"):
        return None
    a = normalize_number(given)
    if a is None:
        return None
    givens = {normalize_number(v) for k, v in payload.items()
              if isinstance(v, (int, float)) and k != "target_count"}
    for value in payload.get("operands", []):
        givens.add(normalize_number(value))
    return "ERR_LANGUAGE_CONTEXT" if a in givens else None


def _d_transfer(task, given, correct, payload, ctx):
    return "ERR_TRANSFER" if task["task_purpose"] == "TRANSFER" else None


def _d_prerequisite(task, given, correct, payload, ctx):
    return "ERR_PREREQUISITE" if ctx.selected_by_reason == "CHECK_PREREQUISITE" else None


_DETECTORS = (
    _d_sequence,
    _d_cardinality,
    _d_zero_placeholder,
    _d_place_value,
    _d_operation,
    _d_strategy,
    _d_calculation,
    _d_language_context,
    _d_transfer,
    _d_prerequisite,
)
