"""Student State (Sprint 8) und Facetten (§117, §118).

§117 ist die zentrale Vorgabe dieses Moduls:

    Nicht:   73 % richtig -> ZO07 = 73 %
    Sondern: ZO07: basic concept = secure, two-digit symbolic = secure,
             decomposition = uncertain, compensation = secure,
             transfer = unknown, representation = stable

Diese Aufschluesselung besteht nicht aus Kompetenzknoten, sondern aus
Aufgabenmerkmalen: Darstellung (§16), Schwierigkeit (§18), Zahl-, Struktur-,
Oberflaechenmerkmale und Strategieaffordanzen (§20-23), Aufgabenzweck (§90).
Deshalb wird je Kompetenz und Merkmalswert ein eigener Status gefuehrt.

§27 ist bindend: SECURE bedeutet nicht "dauerhaft beherrscht", sondern
"aktuell ausreichend konsistente Evidenz". Der Status ist deshalb jederzeit
neu berechenbar und traegt Zeitstempel (§40).

§26 ist bindend: die Profilmarker sind keine Diagnosen. REPRESENTATION_DEPENDENT
heisst "unter dieser Darstellung war die Leistung besser als unter jener"
(§32), nicht "visuelle:r Lerner:in".
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from . import evidence
from .attempts import attempt_history
from .clock import Clock, days_between
from .config import Config

DIFFICULTIES = ("D1", "D2", "D3", "D4", "D5")

#: Facettenklassen. Der Schluessel ist ein Vokabularname (§108), damit eine
#: neue Klasse ohne Migration ergaenzbar ist.
FACET_KINDS = (
    "REPRESENTATION_MODE",
    "INTERACTION_MODE",
    "INTERNAL_DIFFICULTY",
    "TASK_PURPOSE",
    "NUMERIC_FEATURE",
    "STRUCTURAL_FEATURE",
    "SURFACE_FEATURE",
    "STRATEGY_AFFORDANCE",
)

#: EINWERTIGE Aufgabeneigenschaften: Wert gegen Wert vergleichen (§69, §100).
DEPENDENCY_MARKERS = {
    "REPRESENTATION_MODE": "REPRESENTATION_DEPENDENT",
}

#: MEHRWERTIGE Merkmale: Anwesenheit gegen Abwesenheit vergleichen (§71, §101).
#: Dieselbe Unterscheidung wie in hypotheses.py - ein Marker nach §26 und eine
#: Hypothese nach §64 beschreiben denselben Befund, nur unterschiedlich
#: ausfuehrlich. Die Erkennungsregel muss deshalb dieselbe sein.
PRESENCE_MARKERS = {
    "NUMERIC_FEATURE": "STRATEGY_DEPENDENT",
    "STRATEGY_AFFORDANCE": "STRATEGY_DEPENDENT",
    "SURFACE_FEATURE": "SURFACE_DEPENDENT",
}


def _presence_pattern(history: list[dict], facet_kind: str, feature: str,
                      min_pos: int, min_neg: int) -> bool:
    """Gelingt es mit dem Merkmal durchgaengig und ohne es durchgaengig nicht?

    §26: der daraus folgende Marker ist keine Diagnose. Er sagt, unter welcher
    Aufgabenbedingung die Leistung besser war - nicht, woran das liegt (§32).
    """
    def has(row):
        return feature in (row.get("features") or {}).get(facet_kind, ())

    with_pos = sum(1 for r in history if r["is_correct"] and has(r))
    with_neg = sum(1 for r in history if not r["is_correct"] and has(r))
    without_pos = sum(1 for r in history if r["is_correct"] and not has(r))
    without_neg = sum(1 for r in history if not r["is_correct"] and not has(r))
    return (with_pos >= min_pos and with_neg == 0
            and without_neg >= min_neg and without_pos == 0)


@dataclass
class StateResult:
    competency_id: str
    status: str
    previous_status: str | None
    counts: dict
    current_floor: str | None
    current_ceiling: str | None
    profile_markers: list[str] = field(default_factory=list)
    variation_dimensions: int = 0


def _facet_values(row: dict) -> list[tuple[str, str]]:
    """Alle Facettenwerte, die ein Versuch belegt."""
    out = [
        ("REPRESENTATION_MODE", row["representation_mode"]),
        ("INTERACTION_MODE", row["interaction_mode"]),
        ("INTERNAL_DIFFICULTY", row["internal_difficulty"]),
        ("TASK_PURPOSE", row["task_purpose"]),
    ]
    for kind in ("NUMERIC_FEATURE", "STRUCTURAL_FEATURE", "SURFACE_FEATURE",
                 "STRATEGY_AFFORDANCE"):
        for value in sorted(row["features"].get(kind, ())):
            out.append((kind, value))
    return out


def _status_from_counts(positive: int, negative: int, cfg: Config) -> str:
    """Statusregel fuer eine EINZELNE Bedingung - also fuer eine Facette.

    Eine Facette ist bereits auf eine Bedingung eingeschraenkt (eine
    Darstellung, eine Stufe, ein Merkmal), deshalb ist hier flaches Zaehlen
    richtig. Fuer die Kompetenz insgesamt gilt _status_from_history().

    Die Schwellen kommen aus system_config; §41 verbietet die feste Behauptung
    "zwei richtige Aufgaben = Kompetenz sicher". Die Konsistenzbedingung setzt
    §41 zweiten Absatz um: eine einfache Zaehlregel beruecksichtigt zufaellige
    Fehler schlecht, deshalb muss die Evidenz nicht nur zahlreich, sondern auch
    einheitlich gerichtet sein. Formel und Schwelle sind Entscheidung D-05.
    """
    need_pos = cfg.require("mastery.success_confirmation_required")
    need_neg = cfg.require("mastery.failure_replication_required")
    min_consistency = cfg.require("mastery.consistency_threshold")
    cons = evidence.consistency(positive, negative)

    if positive == 0 and negative == 0:
        return "UNKNOWN"
    if positive >= need_pos and negative == 0:
        return "SECURE"
    if negative >= need_neg and positive == 0:
        return "SUPPORT_FOCUS"
    if cons is not None and cons < min_consistency:
        return "UNCERTAIN"
    if positive >= need_pos and positive > negative:
        return "SECURE"
    if negative >= need_neg and negative > positive:
        return "SUPPORT_FOCUS"
    return "ACTIVE"


def _status_from_history(history: list[dict], cfg: Config) -> str:
    """Statusregel fuer eine KOMPETENZ, nach Schwierigkeitsstufen getrennt.

    §117 ist hier der Ausgangspunkt: "73 % richtig -> ZO07 = 73 % verliert
    Informationen." Genau das wuerde passieren, wenn man alle Stufen in einen
    Zaehler wirft. Ein Kind, das D1 sicher loest und ab D2 reproduzierbar
    scheitert, hat keine "unsichere" Kompetenz - es hat eine gefundene Grenze,
    und §99 (Testfall B) erwartet dafuer SUPPORT_FOCUS.

    Deshalb wird je Stufe gezaehlt und dann geschlossen:

      reproduzierbarer Fehler auf einer Stufe   -> SUPPORT_FOCUS
        Die Grenze ist lokalisiert, hier ist die Foerderung anzusetzen (§91).
      reproduzierbarer Erfolg, nirgends Fehler  -> SECURE
        §27: aktuell ausreichend konsistente Evidenz, nicht "dauerhaft".
      Widerspruch INNERHALB einer Stufe         -> UNCERTAIN
        §71: nicht pauschal herabstufen, sondern Merkmale vergleichen. Genau
        dieser Fall ist Testfall D (§101): dieselbe Stufe, unterschiedliche
        Zahlenstruktur, unterschiedlicher Erfolg.
      sonst                                     -> ACTIVE

    Die Unterscheidung zwischen SUPPORT_FOCUS und UNCERTAIN ist der Kern:
    stufenweise Grenze heisst Foerderbedarf, merkmalsweise Streuung innerhalb
    einer Stufe heisst offene Frage. Entscheidung D-05.
    """
    need_pos = cfg.require("mastery.success_confirmation_required")
    need_neg = cfg.require("mastery.failure_replication_required")
    min_consistency = cfg.require("mastery.consistency_threshold")

    per_level: dict[str, dict[str, int]] = {}
    for row in history:
        bucket = per_level.setdefault(row["internal_difficulty"], {"pos": 0, "neg": 0})
        bucket["pos" if row["is_correct"] else "neg"] += 1

    if not per_level:
        return "UNKNOWN"

    reproducible_failure = any(b["neg"] >= need_neg and b["pos"] == 0
                               for b in per_level.values())
    reproducible_success = any(b["pos"] >= need_pos and b["neg"] == 0
                               for b in per_level.values())
    any_failure = any(b["neg"] > 0 for b in per_level.values())
    def inconsistent(bucket: dict[str, int]) -> bool:
        if bucket["pos"] == 0 or bucket["neg"] == 0:
            return False
        cons = evidence.consistency(bucket["pos"], bucket["neg"])
        # Ausdruecklich gegen None pruefen: eine Konsistenz von genau 0.0 ist
        # der staerkste Widerspruch, nicht ein fehlender Wert.
        return cons is not None and cons < min_consistency

    mixed_within_level = any(inconsistent(b) for b in per_level.values())

    # §71 ist hier bindend: "Nicht: ADDITION = UNSAFE. Sondern Merkmale
    # vergleichen." Ein reproduzierbarer Fehler auf einer Stufe ist nur dann
    # eine Stufengrenze, wenn er nicht vollstaendig durch eine
    # Bedingungsabhaengigkeit erklaert ist. Scheitern auf D2 genau die Items
    # ohne COMPENSATION und gelingen die mit, dann ist D2 nicht unerreichbar -
    # die Aufgabenmerkmale entscheiden. Das ist der Unterschied zwischen
    # Testfall B (auch ikonisch falsch, also Grenze) und Testfall D (nur ohne
    # das Merkmal falsch, also Abhaengigkeit). Siehe ENTSCHEIDUNGEN.md D-05.
    if reproducible_failure and not _dependency_explains_failures(history, cfg):
        return "SUPPORT_FOCUS"
    if reproducible_success and not any_failure:
        return "SECURE"
    if mixed_within_level or reproducible_failure:
        return "UNCERTAIN"
    return "ACTIVE"


def _dependency_explains_failures(history: list[dict], cfg: Config) -> bool:
    """Gibt es eine Bedingung, die Erfolg und Misserfolg vollstaendig trennt?

    Geprueft werden dieselben Muster wie fuer die Profilmarker (§26) und die
    Hypothesen (§64): eine einwertige Eigenschaft Wert gegen Wert, ein
    mehrwertiges Merkmal Anwesenheit gegen Abwesenheit. Trifft eines zu, ist die
    Beobachtung eine Abhaengigkeit und keine Stufengrenze.
    """
    min_pos = cfg.require("hypothesis.representation_min_iconic_successes")
    min_neg = cfg.require("hypothesis.representation_min_symbolic_errors")

    for kind in PRESENCE_MARKERS:
        observed = {value for row in history
                    for value in (row.get("features") or {}).get(kind, ())}
        for feature in observed:
            if _presence_pattern(history, kind, feature, min_pos, min_neg):
                return True

    for kind in DEPENDENCY_MARKERS:
        tally: dict[str, dict[str, int]] = {}
        for row in history:
            value = row.get("representation_mode") if kind == "REPRESENTATION_MODE" else None
            if value is None:
                continue
            bucket = tally.setdefault(value, {"pos": 0, "neg": 0})
            bucket["pos" if row["is_correct"] else "neg"] += 1
        strong = any(b["pos"] >= min_pos and b["neg"] == 0 for b in tally.values())
        weak = any(b["neg"] >= min_neg and b["pos"] == 0 for b in tally.values())
        if strong and weak:
            return True
    return False


def recompute_facets(conn: sqlite3.Connection, student_id: str, competency_id: str,
                     cfg: Config, clock: Clock) -> dict[tuple[str, str], dict]:
    """Schreibt student_competency_facets neu. Grundlage fuer §117 und §118."""
    history = attempt_history(conn, student_id, competency_id)
    tally: dict[tuple[str, str], dict] = {}
    for row in history:
        for kind, value in _facet_values(row):
            entry = tally.setdefault((kind, value), {"pos": 0, "neg": 0, "last": None})
            if row["is_correct"]:
                entry["pos"] += 1
            else:
                entry["neg"] += 1
            entry["last"] = row["completed_at"]

    conn.execute(
        "DELETE FROM student_competency_facets WHERE student_id = ? AND competency_id = ?",
        (student_id, competency_id),
    )
    now = clock.now_iso()
    for (kind, value), entry in tally.items():
        status = _status_from_counts(entry["pos"], entry["neg"], cfg)
        conn.execute(
            "INSERT INTO student_competency_facets (student_id, competency_id, facet_kind,"
            " facet_value, status, positive_count, negative_count, consistency,"
            " last_evidence, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (student_id, competency_id, kind, value, status, entry["pos"], entry["neg"],
             evidence.consistency(entry["pos"], entry["neg"]), entry["last"], now),
        )
        entry["status"] = status
    return tally


def variation_dimensions(history: list[dict]) -> dict[str, bool]:
    """§72: Evidenz ist staerker, wenn Erfolg ueber Variation von numbers,
    representation, surface, strategy und context gezeigt wurde."""
    correct = [r for r in history if r["is_correct"]]
    if not correct:
        return {k: False for k in ("numbers", "representation", "surface", "strategy", "context")}

    def sets_of(kind: str) -> set[frozenset]:
        return {frozenset(r["features"].get(kind, ())) for r in correct}

    with_context = any("WORD_PROBLEM" in r["features"].get("SURFACE_FEATURE", ()) for r in correct)
    without_context = any("NO_CONTEXT" in r["features"].get("SURFACE_FEATURE", ())
                          or "SYMBOLIC_ONLY" in r["features"].get("SURFACE_FEATURE", ())
                          for r in correct)
    return {
        # Verschiedene Items derselben Kompetenz tragen verschiedene Zahlen (§19).
        "numbers": len({r["task_id"] for r in correct}) >= 2,
        "representation": len({r["representation_mode"] for r in correct}) >= 2,
        "surface": len(sets_of("SURFACE_FEATURE")) >= 2,
        "strategy": len(sets_of("STRATEGY_AFFORDANCE")) >= 2,
        "context": with_context and without_context,
    }


def profile_markers(conn: sqlite3.Connection, student_id: str, competency_id: str,
                    facets: dict[tuple[str, str], dict], history: list[dict],
                    cfg: Config) -> list[str]:
    """Profilmarker nach §26. Keine Diagnosen (§26 letzter Satz, §32)."""
    markers: list[str] = []
    min_pos = cfg.require("hypothesis.representation_min_iconic_successes")
    min_neg = cfg.require("hypothesis.representation_min_symbolic_errors")

    # Einwertige Eigenschaften: Wert gegen Wert (§69, §100).
    for kind, marker in DEPENDENCY_MARKERS.items():
        values = {v: e for (k, v), e in facets.items() if k == kind}
        strong = [v for v, e in values.items() if e["pos"] >= min_pos and e["neg"] == 0]
        weak = [v for v, e in values.items() if e["neg"] >= min_neg and e["pos"] == 0]
        if strong and weak:
            markers.append(marker)

    # Mehrwertige Merkmale: Anwesenheit gegen Abwesenheit (§71, §101).
    # §71 beschreibt genau dieses Muster - 49+36 und 48+37 gelingen mit
    # NEAR_ROUND_NUMBER, 37+28 und 46+27 ohne. Ein Vergleich Wert gegen Wert
    # findet das nicht, weil dieselben Items mehrere Merkmale tragen.
    for kind, marker in PRESENCE_MARKERS.items():
        observed = {value for row in history for value in row["features"].get(kind, ())}
        for feature in observed:
            if _presence_pattern(history, kind, feature, min_pos, min_neg):
                markers.append(marker)
                break

    structural = {v: e for (k, v), e in facets.items() if k == "STRUCTURAL_FEATURE"}
    if len(structural) >= 2 and all(
            e["neg"] == 0 and e["pos"] >= cfg.require("mastery.success_confirmation_required")
            for e in structural.values()):
        markers.append("STRUCTURE_STABLE")

    dims = variation_dimensions(history)
    needed = cfg.optional("testing.transfer_stable_min_variation_dimensions")
    transfer_positive = any(
        r["is_correct"] and r["task_purpose"] == "TRANSFER" for r in history)
    if needed is not None and transfer_positive and sum(dims.values()) >= needed:
        markers.append("TRANSFER_STABLE")

    correct_tasks = {r["task_id"] for r in history if r["is_correct"]}
    wrong_tasks = {r["task_id"] for r in history if not r["is_correct"]}
    if len(correct_tasks) == 1 and wrong_tasks - correct_tasks:
        markers.append("ITEM_SPECIFIC_SUCCESS")

    return markers


def _bracket(history: list[dict], cfg: Config) -> tuple[str | None, str | None]:
    """Kompetenzfenster nach §34 und §36.

    floor  hoechste Stufe, auf der ausschliesslich richtig geantwortet wurde -
           darunter muss nicht mehr geprueft werden.
    ceiling niedrigste Stufe, auf der ausschliesslich falsch geantwortet wurde -
           darueber liegt derzeit kein erreichbarer Bereich.
    """
    per_level = {d: {"pos": 0, "neg": 0} for d in DIFFICULTIES}
    for row in history:
        bucket = per_level.get(row["internal_difficulty"])
        if bucket is None:
            continue
        bucket["pos" if row["is_correct"] else "neg"] += 1

    floor = None
    for level in DIFFICULTIES:
        if per_level[level]["pos"] > 0 and per_level[level]["neg"] == 0:
            floor = level
    ceiling = None
    for level in DIFFICULTIES:
        if per_level[level]["neg"] > 0 and per_level[level]["pos"] == 0:
            ceiling = level
            break
    return floor, ceiling


def recompute(conn: sqlite3.Connection, student_id: str, competency_id: str,
              cfg: Config, clock: Clock) -> StateResult:
    """Berechnet den Zustand einer Kompetenz neu.

    Parken und Reaktivieren stehen bewusst NICHT hier, sondern in parking.py:
    §38 und §39 sind eigene Uebergaenge mit eigenen Bedingungen, und die
    Lehrkraft muss sie nach §3 uebersteuern koennen.
    """
    row = conn.execute(
        "SELECT * FROM student_competency_state WHERE student_id = ? AND competency_id = ?",
        (student_id, competency_id),
    ).fetchone()
    previous = row["status"] if row else None

    counts = evidence.counts(conn, student_id, competency_id)
    history = attempt_history(conn, student_id, competency_id)
    facets = recompute_facets(conn, student_id, competency_id, cfg, clock)

    status = _status_from_history(history, cfg)

    # §27: BLOCKED setzt die Lehrkraft (§3). Der Automat ueberschreibt das nicht.
    if previous == "BLOCKED":
        status = "BLOCKED"
    # §39: eine reaktivierte Kompetenz bleibt REACTIVATED, bis neue direkte
    # Evidenz vorliegt - sonst waere die Reaktivierung sofort wieder weg.
    elif previous == "REACTIVATED" and counts["direct_positive"] + counts["direct_negative"] == \
            _direct_count_at_reactivation(conn, student_id, competency_id):
        status = "REACTIVATED"
    elif previous == "PARKED" and counts["direct_negative"] == 0:
        status = "PARKED"

    floor, ceiling = _bracket(history, cfg)
    markers = profile_markers(conn, student_id, competency_id, facets, history, cfg)
    dims = variation_dimensions(history)

    review_days = cfg.optional("park.next_review_interval_days")
    conn.execute(
        "INSERT INTO student_competency_state (student_id, competency_id, status,"
        " direct_evidence_score, indirect_evidence_score, evidence_consistency,"
        " current_floor, current_ceiling, profile_markers, first_evidence,"
        " last_direct_evidence, last_indirect_evidence, last_review, next_review,"
        " parked_at, reactivation_reason, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
        "         (SELECT parked_at FROM student_competency_state"
        "           WHERE student_id = ? AND competency_id = ?),"
        "         (SELECT reactivation_reason FROM student_competency_state"
        "           WHERE student_id = ? AND competency_id = ?), ?)"
        " ON CONFLICT (student_id, competency_id) DO UPDATE SET"
        " status = excluded.status,"
        " direct_evidence_score = excluded.direct_evidence_score,"
        " indirect_evidence_score = excluded.indirect_evidence_score,"
        " evidence_consistency = excluded.evidence_consistency,"
        " current_floor = excluded.current_floor,"
        " current_ceiling = excluded.current_ceiling,"
        " profile_markers = excluded.profile_markers,"
        " first_evidence = COALESCE(student_competency_state.first_evidence,"
        "                           excluded.first_evidence),"
        " last_direct_evidence = excluded.last_direct_evidence,"
        " last_indirect_evidence = excluded.last_indirect_evidence,"
        " next_review = excluded.next_review,"
        " updated_at = excluded.updated_at",
        (student_id, competency_id, status, counts["direct_score"], counts["indirect_score"],
         counts["consistency"], floor, ceiling,
         json.dumps(markers, ensure_ascii=False), counts["first"],
         counts["last_direct"], counts["last_indirect"], clock.now_iso(),
         clock.plus_days_iso(review_days),
         student_id, competency_id, student_id, competency_id, clock.now_iso()),
    )

    return StateResult(competency_id=competency_id, status=status, previous_status=previous,
                       counts=counts, current_floor=floor, current_ceiling=ceiling,
                       profile_markers=markers, variation_dimensions=sum(dims.values()))


def _direct_count_at_reactivation(conn: sqlite3.Connection, student_id: str,
                                  competency_id: str) -> int:
    """Wieviel direkte Evidenz lag vor, als reaktiviert wurde? Verhindert, dass
    REACTIVATED bei der naechsten Neuberechnung ohne neue Beobachtung verfaellt."""
    row = conn.execute(
        "SELECT reactivation_reason, updated_at FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?", (student_id, competency_id)
    ).fetchone()
    if not row or not row["reactivation_reason"]:
        return -1
    return conn.execute(
        "SELECT COUNT(*) AS n FROM evidence_events WHERE student_id = ? AND competency_id = ?"
        " AND evidence_type LIKE 'DIRECT%' AND created_at <= ?",
        (student_id, competency_id, row["updated_at"]),
    ).fetchone()["n"]


def touched_competencies(conn: sqlite3.Connection, student_id: str, attempt_id: str) -> list[str]:
    """Alle Kompetenzen, fuer die dieser Versuch Evidenz erzeugt hat."""
    return [r["competency_id"] for r in conn.execute(
        "SELECT DISTINCT competency_id FROM evidence_events WHERE student_id = ?"
        " AND source_attempt = ? ORDER BY competency_id", (student_id, attempt_id))]


def load(conn: sqlite3.Connection, student_id: str) -> dict[str, dict]:
    """Vollstaendiger Zustand. §74: fuer das Routing wird daraus nur der aktive
    Teilgraph geladen, nicht alles."""
    out = {}
    for row in conn.execute(
        "SELECT * FROM student_competency_state WHERE student_id = ?", (student_id,)
    ):
        entry = dict(row)
        entry["profile_markers"] = json.loads(entry["profile_markers"])
        out[entry["competency_id"]] = entry
    return out


def facets_of(conn: sqlite3.Connection, student_id: str,
              competency_id: str) -> dict[str, dict[str, dict]]:
    """Facetten einer Kompetenz, gruppiert nach Klasse. Liefert die Darstellung,
    die §117 verlangt."""
    out: dict[str, dict[str, dict]] = {}
    for row in conn.execute(
        "SELECT * FROM student_competency_facets WHERE student_id = ? AND competency_id = ?"
        " ORDER BY facet_kind, facet_value", (student_id, competency_id)
    ):
        out.setdefault(row["facet_kind"], {})[row["facet_value"]] = dict(row)
    return out


def evidence_age_days(conn: sqlite3.Connection, student_id: str, competency_id: str,
                      clock: Clock) -> float | None:
    row = conn.execute(
        "SELECT last_direct_evidence FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?", (student_id, competency_id)
    ).fetchone()
    if not row:
        return None
    return days_between(row["last_direct_evidence"], clock.now())
