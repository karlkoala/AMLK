"""Hypothesen (§64, §115) - Ebene 3 von §66.

Eine Hypothese entsteht NIE aus einem einzelnen Fehler. §29: "Ein Fehler ist
keine Diagnose." §30: erst die Replikation macht aus einem Fehler ein
reproduzierbares Muster. §14: "Erst mehrere unabhaengige Beobachtungen koennen
eine entsprechende Hypothese aktivieren."

§115 Grundsatz der Widerlegbarkeit ist bindend und hier technisch erzwungen:
eine Hypothese wird nur eroeffnet, wenn ein Item existiert, das sie widerlegen
kann. Ist keines vorhanden, wird die Hypothese nicht eroeffnet - das ist ein
Befund ueber die Aufgabenbank, keine Ausnahme.

    Schlecht: "Schueler:in hat moeglicherweise Schwierigkeiten mit Mathematik."
    Gut:      "Die Leistung koennte bei symbolischer Darstellung niedriger sein
               als bei ikonischer Darstellung."

§32 ist bindend: aus IMAGE richtig und SYMBOL falsch folgt NICHT "visuelle:r
Lerner:in", sondern nur eine Aussage ueber die Leistung unter diesen beiden
Bedingungen. Die Formulierungen in target_construct halten sich daran.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from . import ids
from .attempts import attempt_history, load_task, task_features
from .clock import Clock
from .config import Config
from .state import facets_of

#: EINWERTIGE Aufgabeneigenschaften: jedes Item hat genau einen Wert, die Werte
#: schliessen sich aus. Hier wird Wert gegen Wert verglichen (§69, §100).
DEPENDENCY_HYPOTHESES = {
    "REPRESENTATION_MODE": "REPRESENTATION_HYPOTHESIS",
}

#: MEHRWERTIGE Merkmale: ein Item traegt eine Menge von Merkmalen (§82). Hier
#: ist nicht Wert gegen Wert zu vergleichen, sondern ANWESENHEIT gegen
#: ABWESENHEIT eines Merkmals. §71 beschreibt genau das: 49+36 und 48+37
#: gelingen (mit NEAR_ROUND_NUMBER), 37+28 und 46+27 nicht (ohne). Ein
#: Wert-gegen-Wert-Vergleich wuerde das nicht finden, weil 49+36 sowohl
#: COMPENSATION als auch DECOMPOSITION nahelegt.
PRESENCE_HYPOTHESES = {
    "NUMERIC_FEATURE": "STRATEGY_DEPENDENCY_HYPOTHESIS",
    "STRATEGY_AFFORDANCE": "STRATEGY_DEPENDENCY_HYPOTHESIS",
    "SURFACE_FEATURE": "SURFACE_DEPENDENCY_HYPOTHESIS",
}

#: Fehlercode, aus dem nach Replikation ein Hypothesentyp folgt (§66).
ERROR_HYPOTHESES = {
    "ERR_ZERO_PLACEHOLDER": "ZERO_PLACEHOLDER_HYPOTHESIS",
}


@dataclass
class HypothesisAction:
    hypothesis_id: str
    hypothesis_type: str
    target_construct: str
    status: str
    action: str            # OPENED | SUPPORTED | WEAKENED | REJECTED | UNCHANGED
    falsifying_task: str | None
    spec_section: str


def _existing(conn: sqlite3.Connection, student_id: str, hypothesis_type: str,
              target_construct: str):
    return conn.execute(
        "SELECT * FROM student_hypotheses WHERE student_id = ? AND hypothesis_type = ?"
        " AND target_construct = ?", (student_id, hypothesis_type, target_construct)
    ).fetchone()


def _pick_falsifying(conn: sqlite3.Connection, student_id: str, competency_id: str,
                     facet_kind: str, weak_value: str) -> str | None:
    """§115: ein Item, das die Hypothese widerlegen koennte.

    Fuer eine Darstellungshypothese ist das ein Item in der SCHWACHEN
    Darstellung - gelingt es, ist die Hypothese widerlegt. Noch nicht gestellte
    Items haben Vorrang; ist keines uebrig, ist eine Wiederholungspruefung
    zulaessig (§39 RECHECK), weil sonst die Hypothese nach §115 gar nicht
    eroeffnet werden duerfte.
    """
    if facet_kind == "REPRESENTATION_MODE":
        sql = ("SELECT t.task_id FROM tasks t WHERE t.primary_competency = ?"
               " AND t.representation_mode = ?")
        params = (competency_id, weak_value)
    else:
        sql = ("SELECT t.task_id FROM tasks t JOIN task_features f ON f.task_id = t.task_id"
               " WHERE t.primary_competency = ? AND f.feature_kind = ? AND f.feature_value = ?")
        params = (competency_id, facet_kind, weak_value)

    candidates = [r["task_id"] for r in conn.execute(sql, params)]
    if not candidates:
        return None
    administered = {r["task_id"] for r in attempt_history(conn, student_id, competency_id)}
    fresh = [t for t in candidates if t not in administered]
    return sorted(fresh)[0] if fresh else sorted(candidates)[0]


def _open_or_update(conn: sqlite3.Connection, student_id: str, hypothesis_type: str,
                    target_construct: str, falsifying_task: str | None,
                    supporting: list[str], contradicting: list[str], priority: int,
                    cfg: Config, clock: Clock, spec_section: str) -> HypothesisAction:
    supporting = sorted(set(supporting))
    contradicting = sorted(set(contradicting))
    supporting = [a for a in supporting if a not in contradicting]
    require_falsifiable = cfg.require("hypothesis.require_falsifying_task")
    row = _existing(conn, student_id, hypothesis_type, target_construct)
    now = clock.now_iso()

    if row is None:
        if require_falsifiable and not falsifying_task:
            # §115: nicht widerlegbar, also nicht eroeffnen.
            return HypothesisAction("-", hypothesis_type, target_construct, "NOT_OPENED",
                                    "BLOCKED_NOT_FALSIFIABLE", None, spec_section)
        hypothesis_id = ids.next_id(conn, "student_hypotheses", student_id)
        conn.execute(
            "INSERT INTO student_hypotheses (hypothesis_id, student_id, hypothesis_type,"
            " target_construct, status, supporting_evidence, contradicting_evidence,"
            " falsifying_task, priority, created_at, last_updated)"
            " VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?)",
            (hypothesis_id, student_id, hypothesis_type, target_construct,
             json.dumps(supporting), json.dumps(contradicting), falsifying_task,
             priority, now, now))
        return HypothesisAction(hypothesis_id, hypothesis_type, target_construct, "OPEN",
                                "OPENED", falsifying_task, spec_section)

    if row["status"] in ("REJECTED", "CLOSED"):
        return HypothesisAction(row["hypothesis_id"], hypothesis_type, target_construct,
                                row["status"], "UNCHANGED", row["falsifying_task"],
                                spec_section)

    if (supporting == sorted(json.loads(row["supporting_evidence"]))
            and contradicting == sorted(json.loads(row["contradicting_evidence"]))
            and (not falsifying_task or falsifying_task == row["falsifying_task"])):
        return HypothesisAction(row["hypothesis_id"], hypothesis_type, target_construct,
                                row["status"], "UNCHANGED", row["falsifying_task"], spec_section)

    if contradicting and len(contradicting) >= cfg.require("mastery.success_confirmation_required"):
        status, action = "REJECTED", "REJECTED"
    elif contradicting:
        status, action = "WEAKENED", "WEAKENED"
    elif row["status"] == "OPEN" and len(supporting) > len(json.loads(row["supporting_evidence"])):
        status, action = "SUPPORTED", "SUPPORTED"
    else:
        status, action = row["status"], "UNCHANGED"

    conn.execute(
        "UPDATE student_hypotheses SET status = ?, supporting_evidence = ?,"
        " contradicting_evidence = ?, falsifying_task = ?, last_updated = ?"
        " WHERE hypothesis_id = ?",
        (status, json.dumps(supporting), json.dumps(contradicting),
         falsifying_task or row["falsifying_task"], now, row["hypothesis_id"]))
    return HypothesisAction(row["hypothesis_id"], hypothesis_type, target_construct,
                            status, action, falsifying_task or row["falsifying_task"],
                            spec_section)


def _open_new(conn, student_id, hypothesis_type, target_construct, falsifying_task,
              supporting, contradicting, priority, cfg, clock, spec_section):
    old = _existing(conn, student_id, hypothesis_type, target_construct)
    if old:
        return HypothesisAction(old["hypothesis_id"], hypothesis_type, target_construct,
                                old["status"], "UNCHANGED", old["falsifying_task"], spec_section)
    return _open_or_update(conn, student_id, hypothesis_type, target_construct,
                          falsifying_task, supporting, contradicting, priority, cfg, clock, spec_section)


def _compatible_task(conn, student_id, competency, condition, predicate):
    candidates = []
    for row in conn.execute("SELECT * FROM tasks WHERE primary_competency = ?", (competency,)):
        task = dict(row)
        task["features"] = task_features(conn, task["task_id"])
        if (condition is None or _comparison_key(task) == condition) and predicate(task):
            candidates.append(task["task_id"])
    return _pick_fresh(conn, student_id, competency, set(candidates))


def _refresh_existing(conn, student_id, changed_competency, cfg, clock):
    """Update established hypotheses independently of their opening thresholds.

    Evidence is rebuilt from attempt IDs, never incremented. Existing support
    anchors determine the comparison key; ambiguous legacy anchors are left
    unchanged rather than treating incomparable answers as counterevidence.
    """
    actions = []
    for h in open_hypotheses(conn, student_id):
        target = h["target_construct"]
        competency = target.split(":", 1)[0]
        prerequisite = target.split(":requires:", 1)[1] if ":requires:" in target else None
        if changed_competency not in (competency, prerequisite):
            continue
        history = attempt_history(conn, student_id, competency)
        old_ids = set(json.loads(h["supporting_evidence"])) | set(json.loads(h["contradicting_evidence"]))
        supporting, contradicting = [], []
        falsifying = h["falsifying_task"]
        kind = h["hypothesis_type"]
        if prerequisite:
            if not falsifying:
                continue
            control = load_task(conn, falsifying)
            relevant = [r for r in attempt_history(conn, student_id, prerequisite)
                        if _comparison_key(r) == _comparison_key(control) and not r["support_used"]]
            # Failures of the target are suggestive; direct prerequisite probes
            # are the actual evidence for or against the proposed explanation.
            supporting = [r["attempt_id"] for r in history if not r["is_correct"]]
            supporting += [r["attempt_id"] for r in relevant if not r["is_correct"]]
            contradicting = [r["attempt_id"] for r in relevant if r["is_correct"]]
        elif kind == "ZERO_PLACEHOLDER_HYPOTHESIS":
            relevant_tasks = _tasks_at_risk_for(conn, competency, "ERR_ZERO_PLACEHOLDER")
            supporting = [r["attempt_id"] for r in history if "ERR_ZERO_PLACEHOLDER" in r["error_codes"]]
            contradicting = [r["attempt_id"] for r in history if r["task_id"] in relevant_tasks
                             and r["is_correct"] and not r["support_used"]]
        else:
            anchors = [r for r in history if r["attempt_id"] in old_ids]
            conditions = {_comparison_key(r) for r in anchors}
            if len(conditions) != 1:
                continue
            condition = next(iter(conditions))
            scoped = [r for r in history if _comparison_key(r) == condition and not r["support_used"]]
            _, facet, body = target.split(":", 2)
            weak, strong = body.split("@", 1)[0].split("<", 1)
            if kind == "REPRESENTATION_HYPOTHESIS":
                is_weak = lambda r: r["representation_mode"] == weak
                is_strong = lambda r: r["representation_mode"] == strong
            else:
                feature = strong[len("with("):-1]
                is_weak = lambda r: feature not in r["features"].get(facet, ())
                is_strong = lambda r: feature in r["features"].get(facet, ())
            supporting = [r["attempt_id"] for r in scoped
                          if (is_weak(r) and not r["is_correct"]) or (is_strong(r) and r["is_correct"])]
            contradicting = [r["attempt_id"] for r in scoped
                             if (is_weak(r) and r["is_correct"]) or (is_strong(r) and not r["is_correct"])]
            # Stable matching control, not an arbitrary easier/different question.
            if not falsifying or _comparison_key(load_task(conn, falsifying)) != condition:
                falsifying = _compatible_task(conn, student_id, competency, condition, is_weak)
        actions.append(_open_or_update(conn, student_id, kind, target, falsifying,
                        supporting, contradicting, h["priority"], cfg, clock, "§64, §115"))
    return actions


def detect(conn: sqlite3.Connection, student_id: str, competency_id: str,
           cfg: Config, clock: Clock) -> list[HypothesisAction]:
    """Prueft alle Hypothesentypen fuer eine Kompetenz."""
    actions: list[HypothesisAction] = _refresh_existing(conn, student_id, competency_id, cfg, clock)
    actions.extend(_detect_dependency(conn, student_id, competency_id, cfg, clock))
    actions.extend(_detect_presence_dependency(conn, student_id, competency_id, cfg, clock))
    actions.extend(_detect_error_pattern(conn, student_id, competency_id, cfg, clock))
    actions.extend(_detect_prerequisite(conn, student_id, competency_id, cfg, clock))
    return [a for a in actions if a.action != "UNCHANGED"]


def _detect_presence_dependency(conn: sqlite3.Connection, student_id: str,
                                competency_id: str, cfg: Config,
                                clock: Clock) -> list[HypothesisAction]:
    """§71 Zahlenabhaengige Leistung, §25 Strategy Variation und Surface Variation.

    Verglichen wird, ob ein Merkmal vorhanden ist oder nicht - auf DERSELBEN
    Schwierigkeitsstufe (§116). §71 fuehrt genau diesen Fall vor:

        49+36 richtig   48+37 richtig    -> NEAR_ROUND_NUMBER
        37+28 falsch    46+27 falsch     -> kein runder Anker

    und schliesst daraus ausdruecklich NICHT "ADDITION = UNSAFE", sondern
    eroeffnet eine STRATEGY_DEPENDENCY_HYPOTHESIS und waehlt ein Contrast Item.
    """
    min_pos = cfg.require("hypothesis.representation_min_iconic_successes")
    min_neg = cfg.require("hypothesis.representation_min_symbolic_errors")
    same_level_required = cfg.require("hypothesis.require_same_difficulty_for_dependency")
    history = attempt_history(conn, student_id, competency_id)
    out: list[HypothesisAction] = []

    for facet_kind, hypothesis_type in PRESENCE_HYPOTHESES.items():
        observed = sorted({value for row in history
                           for value in row["features"].get(facet_kind, ())})
        for feature in observed:
            level = _presence_level(history, facet_kind, feature, min_pos, min_neg)
            if same_level_required and level is None:
                continue
            if level is None and not _presence_aggregate(
                    history, facet_kind, feature, min_pos, min_neg):
                continue
            construct = (f"{competency_id}:{facet_kind}:without({feature})"
                         f"<with({feature})@{level[0] if level else 'MIXED_LEVELS'}")
            scoped = [r for r in history if level is None or _comparison_key(r) == level]
            supporting = [r["attempt_id"] for r in scoped
                          if (feature in r["features"].get(facet_kind, ()))
                          == bool(r["is_correct"])]
            contradicting = [r["attempt_id"] for r in scoped
                             if r["is_correct"]
                             and feature not in r["features"].get(facet_kind, ())]
            falsifying = _compatible_task(conn, student_id, competency_id, level,
                lambda t: feature not in t["features"].get(facet_kind, ()))
            out.append(_open_new(
                conn, student_id, hypothesis_type, construct, falsifying,
                supporting, contradicting, priority=92, cfg=cfg, clock=clock,
                spec_section="§71, §101"))
    return out


def _presence_level(history: list[dict], facet_kind: str, feature: str,
                    min_pos: int, min_neg: int) -> tuple[str, str, str] | None:
    """Stufe, auf der Anwesenheit durchgaengig gelingt und Abwesenheit nicht."""
    per_condition: dict[tuple[str, str], dict[str, int]] = {}
    for row in history:
        has = feature in row["features"].get(facet_kind, ())
        bucket = per_condition.setdefault(_comparison_key(row),
                                          {"with_pos": 0, "with_neg": 0,
                                           "without_pos": 0, "without_neg": 0})
        key = ("with_" if has else "without_") + ("pos" if row["is_correct"] else "neg")
        bucket[key] += 1
    for condition, b in sorted(per_condition.items()):
        if (b["with_pos"] >= min_pos and b["with_neg"] == 0
                and b["without_neg"] >= min_neg and b["without_pos"] == 0):
            return condition
    return None


def _presence_aggregate(history: list[dict], facet_kind: str, feature: str,
                        min_pos: int, min_neg: int) -> bool:
    with_pos = sum(1 for r in history if r["is_correct"]
                   and feature in r["features"].get(facet_kind, ()))
    with_neg = sum(1 for r in history if not r["is_correct"]
                   and feature in r["features"].get(facet_kind, ()))
    without_pos = sum(1 for r in history if r["is_correct"]
                      and feature not in r["features"].get(facet_kind, ()))
    without_neg = sum(1 for r in history if not r["is_correct"]
                      and feature not in r["features"].get(facet_kind, ()))
    return (with_pos >= min_pos and with_neg == 0
            and without_neg >= min_neg and without_pos == 0)


def _pick_falsifying_without(conn: sqlite3.Connection, student_id: str,
                             competency_id: str, facet_kind: str,
                             feature: str) -> str | None:
    """§115: ein Item OHNE das Merkmal. Gelingt es, ist die Hypothese widerlegt."""
    candidates = [r["task_id"] for r in conn.execute(
        "SELECT t.task_id FROM tasks t WHERE t.primary_competency = ?"
        " AND NOT EXISTS (SELECT 1 FROM task_features f WHERE f.task_id = t.task_id"
        "                 AND f.feature_kind = ? AND f.feature_value = ?)",
        (competency_id, facet_kind, feature))]
    if not candidates:
        return None
    administered = {r["task_id"] for r in attempt_history(conn, student_id, competency_id)}
    fresh = [t for t in candidates if t not in administered]
    return sorted(fresh)[0] if fresh else sorted(candidates)[0]


def _values_of(row: dict, facet_kind: str) -> list[str]:
    if facet_kind == "REPRESENTATION_MODE":
        return [row["representation_mode"]]
    return sorted(row["features"].get(facet_kind, ()))


def _comparison_key(row: dict) -> tuple[str, str, str]:
    """Die Bedingungen, die fuer einen sauberen Vergleich konstant sein muessen.

    §116 Grundsatz der minimalen Veraenderung: nur EINE relevante Variable darf
    variieren. Konstant zu halten sind drei Dinge:

      Schwierigkeitsstufe  sonst kann der Unterschied an der Stufe liegen (F-21)
      Antwortformat        eine Zahl eingeben und eine Zerlegung auswaehlen sind
                           verschiedene Anforderungen
      Frageform            "Welchen Wert hat die Ziffer 6 in 364?" verlangt
                           zusaetzlich, die Stelle zu lokalisieren; "Welchen Wert
                           haben die Zehnerstangen zusammen?" nennt sie. Ohne
                           diese Bedingung waere die Frageform eine unbeobachtete
                           zweite Variable (Kritikbefund 6, D-28).
    """
    return (row["internal_difficulty"], row["scoring_rule"], row["question_form"])


def _tally_by_value_and_level(history: list[dict], facet_kind: str) -> dict:
    """Beobachtungen je Merkmalswert UND Vergleichsbedingung."""
    tally: dict[tuple[str, tuple[str, str]], dict[str, int]] = {}
    for row in history:
        for value in _values_of(row, facet_kind):
            bucket = tally.setdefault((value, _comparison_key(row)), {"pos": 0, "neg": 0})
            bucket["pos" if row["is_correct"] else "neg"] += 1
    return tally


def _detect_dependency(conn: sqlite3.Connection, student_id: str, competency_id: str,
                       cfg: Config, clock: Clock) -> list[HypothesisAction]:
    """§69, §71, §100: eine Bedingung gelingt zuverlaessig, eine andere nicht.

    Die Schwellen kommen aus §88 ("2 structurally similar symbolic errors +
    2 correct iconic items") und §100 (Testfall C zeigt genau zwei symbolische
    Fehlversuche und zwei ikonische Erfolge).

    ENTSCHEIDEND: verglichen wird nur INNERHALB derselben Schwierigkeitsstufe.
    §116 verlangt den Grundsatz der minimalen Veraenderung, §32 verbietet die
    Ueberinterpretation eines Darstellungsunterschieds. Wer zwei symbolische
    Fehler auf D3 mit zwei ikonischen Erfolgen auf D1 vergleicht, kann den
    Unterschied nicht der Darstellung zuschreiben - er koennte an der Stufe
    liegen. Die Engine eroeffnet deshalb keine Hypothese, solange kein Paar auf
    gleicher Stufe vorliegt. Genau das ist der Befund F-21 ueber die
    Aufgabenbank, und er bleibt so sichtbar statt in einer zu fruehen Hypothese
    zu verschwinden. Abschaltbar ueber
    hypothesis.require_same_difficulty_for_dependency. Entscheidung D-24.
    """
    min_pos = cfg.require("hypothesis.representation_min_iconic_successes")
    min_neg = cfg.require("hypothesis.representation_min_symbolic_errors")
    same_level_required = cfg.require("hypothesis.require_same_difficulty_for_dependency")
    history = attempt_history(conn, student_id, competency_id)
    facets = facets_of(conn, student_id, competency_id)
    out: list[HypothesisAction] = []

    for facet_kind, hypothesis_type in DEPENDENCY_HYPOTHESES.items():
        tally = _tally_by_value_and_level(history, facet_kind)
        values = facets.get(facet_kind, {})
        strong = sorted(v for v, e in values.items()
                        if e["positive_count"] >= min_pos and e["negative_count"] == 0)
        weak = sorted(v for v, e in values.items()
                      if e["negative_count"] >= min_neg and e["positive_count"] == 0)

        for weak_value in weak:
            for strong_value in strong:
                if weak_value == strong_value:
                    continue
                level = _common_level(tally, weak_value, strong_value, min_neg, min_pos)
                if same_level_required and level is None:
                    continue
                construct = (f"{competency_id}:{facet_kind}:{weak_value}<{strong_value}"
                             f"@{level[0] if level else 'MIXED_LEVELS'}")
                # §32: eine Aussage ueber die Leistung unter Bedingungen, nicht
                # ueber die Person.
                scoped = [r for r in history if level is None or _comparison_key(r) == level]
                supporting = [r["attempt_id"] for r in scoped
                    if (r["representation_mode"] == weak_value and not r["is_correct"])
                    or (r["representation_mode"] == strong_value and r["is_correct"])]
                contradicting = []
                falsifying = _compatible_task(conn, student_id, competency_id, level,
                    lambda t: t["representation_mode"] == weak_value)
                out.append(_open_new(
                    conn, student_id, hypothesis_type, construct, falsifying,
                    supporting, contradicting, priority=90, cfg=cfg, clock=clock,
                    spec_section="§69, §71, §100"))
    return out


def _common_level(tally: dict, weak_value: str, strong_value: str,
                  min_neg: int, min_pos: int) -> tuple[str, str, str] | None:
    """Eine Bedingung, unter der der Vergleich sauber ist (§116).

    Liefert den Vergleichsschlüssel, wenn Stufe, Frageform und Antwortformat auf beiden
    Seiten uebereinstimmen.
    """
    for (value, condition), bucket in sorted(tally.items()):
        if value != weak_value or bucket["neg"] < min_neg or bucket["pos"] > 0:
            continue
        other = tally.get((strong_value, condition))
        if other and other["pos"] >= min_pos and other["neg"] == 0:
            return condition
    return None


def _attempt_ids(conn: sqlite3.Connection, student_id: str, competency_id: str,
                 facet_kind: str, facet_value: str, correct: bool) -> list[str]:
    history = attempt_history(conn, student_id, competency_id)
    out = []
    for row in history:
        if row["is_correct"] != correct:
            continue
        if facet_kind == "REPRESENTATION_MODE":
            hit = row["representation_mode"] == facet_value
        else:
            hit = facet_value in row["features"].get(facet_kind, ())
        if hit:
            out.append(row["attempt_id"])
    return out


def _detect_error_pattern(conn: sqlite3.Connection, student_id: str, competency_id: str,
                          cfg: Config, clock: Clock) -> list[HypothesisAction]:
    """§66: der Fehlercode allein erzeugt keine Hypothese. Erst nach
    Replikation - genau das zeigt §66 am Beispiel 508 als 58."""
    need = cfg.require("mastery.failure_replication_required")
    history = attempt_history(conn, student_id, competency_id)
    out: list[HypothesisAction] = []

    for code, hypothesis_type in ERROR_HYPOTHESES.items():
        hits = [r for r in history if code in r["error_codes"]]
        if len(hits) < need:
            continue
        construct = f"{competency_id}:{code}"
        # Widerlegbar und bestaetigbar ist die Hypothese nur an Items, an denen
        # der Fehler ueberhaupt auftreten KANN. Ein ikonisches Zehner-Einer-Item
        # ohne unbesetzte Stelle sagt nichts ueber ERR_ZERO_PLACEHOLDER aus -
        # es als widersprechende Evidenz zu zaehlen, wuerde die Hypothese
        # grundlos verwerfen. Entscheidung D-14.
        relevant = _tasks_at_risk_for(conn, competency_id, code)
        falsifying = _pick_fresh(conn, student_id, competency_id, relevant)
        contradicting = [r["attempt_id"] for r in history
                         if r["is_correct"] and r["task_id"] in relevant]
        out.append(_open_new(
            conn, student_id, hypothesis_type, construct, falsifying,
            [r["attempt_id"] for r in hits], contradicting,
            priority=95, cfg=cfg, clock=clock, spec_section="§66"))
    return out


def _tasks_at_risk_for(conn: sqlite3.Connection, competency_id: str,
                       error_code: str) -> set[str]:
    """Items, an denen der Fehlercode ueberhaupt auftreten kann.

    Fuer ERR_ZERO_PLACEHOLDER sind das Items, deren richtige Antwort eine
    unbesetzte Stelle enthaelt - genau der Fall 508 aus §66.
    """
    if error_code != "ERR_ZERO_PLACEHOLDER":
        return {r["task_id"] for r in conn.execute(
            "SELECT task_id FROM tasks WHERE primary_competency = ?", (competency_id,))}
    out = set()
    for row in conn.execute(
        "SELECT task_id, correct_answer FROM tasks WHERE primary_competency = ?",
        (competency_id,),
    ):
        answer = json.loads(row["correct_answer"])
        value = answer.get("value")
        if isinstance(value, int):
            text = str(abs(value))
            if len(text) >= 3 and "0" in text[1:-1]:
                out.add(row["task_id"])
    return out


def _pick_fresh(conn: sqlite3.Connection, student_id: str, competency_id: str,
                candidates: set[str]) -> str | None:
    if not candidates:
        return None
    administered = {r["task_id"] for r in attempt_history(conn, student_id, competency_id)}
    fresh = sorted(candidates - administered)
    return fresh[0] if fresh else sorted(candidates)[0]


def _detect_prerequisite(conn: sqlite3.Connection, student_id: str, competency_id: str,
                         cfg: Config, clock: Clock) -> list[HypothesisAction]:
    """§31 Schritt 3: nach reproduzierbarem Fehler die direkte Voraussetzung
    pruefen. Die Hypothese benennt die Voraussetzung, nicht die Person."""
    need = cfg.require("mastery.failure_replication_required")
    row = conn.execute(
        "SELECT status FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?", (student_id, competency_id)
    ).fetchone()
    if not row or row["status"] != "SUPPORT_FOCUS":
        return []

    history = attempt_history(conn, student_id, competency_id)
    wrong = [r for r in history if not r["is_correct"]]
    if len(wrong) < need:
        return []

    out: list[HypothesisAction] = []
    for rel in conn.execute(
        "SELECT source_competency, relation_type, evidence_status FROM relations"
        " WHERE target_competency = ? AND relation_type IN"
        " ('HARD_PREREQUISITE', 'STRONG_PREREQUISITE')", (competency_id,)
    ):
        prerequisite = rel["source_competency"]
        state = conn.execute(
            "SELECT status FROM student_competency_state"
            " WHERE student_id = ? AND competency_id = ?", (student_id, prerequisite)
        ).fetchone()
        if state and state["status"] in ("SECURE", "PARKED"):
            continue  # Voraussetzung ist belegt, die Hypothese waere schon widerlegt.
        falsifying = conn.execute(
            "SELECT task_id FROM tasks WHERE primary_competency = ?"
            " ORDER BY internal_difficulty, task_id LIMIT 1", (prerequisite,)
        ).fetchone()
        out.append(_open_new(
            conn, student_id, "PREREQUISITE_HYPOTHESIS",
            f"{competency_id}:requires:{prerequisite}",
            falsifying["task_id"] if falsifying else None,
            [r["attempt_id"] for r in wrong], [],
            priority=80, cfg=cfg, clock=clock, spec_section="§31, §69, §70"))
    return out


def open_hypotheses(conn: sqlite3.Connection, student_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM student_hypotheses WHERE student_id = ?"
        " AND status IN ('OPEN', 'SUPPORTED', 'WEAKENED')"
        " ORDER BY priority DESC, hypothesis_id", (student_id,))]


def describe(hypothesis: dict) -> str:
    """Formulierung fuer die Lehrkraftansicht (§88, §115).

    Bewusst konditional und bedingungsbezogen. §115 nennt als gutes Beispiel
    ausdruecklich: "Die Leistung koennte bei symbolischer Darstellung niedriger
    sein als bei ikonischer Darstellung."
    """
    construct = hypothesis["target_construct"]
    kind = hypothesis["hypothesis_type"]
    if kind == "REPRESENTATION_HYPOTHESIS" and construct.count(":") >= 2:
        competency, _, rest = construct.split(":", 2)
        rest, _, level = rest.partition("@")
        weak, strong = rest.split("<") if "<" in rest else (rest, "?")
        auf = f" auf Stufe {level}" if level and level != "MIXED_LEVELS" else ""
        return (f"Bei {competency} koennte die Leistung unter der Darstellung {weak}"
                f" niedriger sein als unter {strong}{auf}.")
    if kind == "STRATEGY_DEPENDENCY_HYPOTHESIS" and "<" in construct:
        competency = construct.split(":", 1)[0]
        body, _, level = construct.rsplit(":", 1)[1].partition("@")
        weak, strong = body.split("<")
        auf = f" auf Stufe {level}" if level and level != "MIXED_LEVELS" else ""
        if strong.startswith("with(") and weak.startswith("without("):
            merkmal = strong[len("with("):-1]
            return (f"Bei {competency} koennte der Erfolg am Merkmal {merkmal} haengen:"
                    f" Aufgaben mit diesem Merkmal gelangen{auf}, Aufgaben ohne es"
                    " nicht. Das ist noch keine Aussage ueber die Addition insgesamt.")
        return (f"Bei {competency} koennte der Erfolg davon abhaengen, ob die Aufgabe"
                f" {strong} nahelegt; ohne diese Affordanz ({weak}) war die Leistung"
                f" niedriger{auf}.")
    if kind == "SURFACE_DEPENDENCY_HYPOTHESIS" and "<" in construct:
        competency = construct.split(":", 1)[0]
        body, _, level = construct.rsplit(":", 1)[1].partition("@")
        weak, strong = body.split("<")
        auf = f" auf Stufe {level}" if level and level != "MIXED_LEVELS" else ""
        return (f"Bei {competency} koennte die Leistung von der Aufgabenoberflaeche"
                f" abhaengen: unter {weak} niedriger als unter {strong}{auf}.")
    if kind == "ZERO_PLACEHOLDER_HYPOTHESIS":
        competency = construct.split(":", 1)[0]
        return (f"Bei {competency} koennte eine unbesetzte Stelle nicht mit 0 markiert"
                " werden; der Fehler trat wiederholt auf.")
    if kind == "PREREQUISITE_HYPOTHESIS" and ":requires:" in construct:
        competency, prerequisite = construct.split(":requires:")
        return (f"Die Schwierigkeit bei {competency} koennte mit der Voraussetzung"
                f" {prerequisite} zusammenhaengen; diese ist noch nicht belegt.")
    return f"Offene Hypothese: {kind} zu {construct}."
