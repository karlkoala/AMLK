"""Die sechs Testfaelle aus §98 bis §103 und die Definition of Done aus §123.

Das ist die eigentliche Abnahme. §123 Kriterium 20 verlangt, dass "die sechs
Testfaelle unterschiedliche erwartete Pfade erzeugen" - nicht dass einzelne
Funktionen laufen.

§124, der wichtigste Satz fuer die Entwicklung, ist der Pruefmassstab:

    Baue kein Quizsystem, das richtige und falsche Antworten zaehlt. Baue einen
    Kompetenzgraphen, der mit moeglichst wenigen gezielt ausgewaehlten Aufgaben
    herausfindet, was eine Schueler:in sicher kann, wo eine Schwierigkeit
    beginnt, unter welchen Bedingungen sie auftritt, welche mathematische
    Voraussetzung dafuer relevant sein koennte und welcher naechste Datenpunkt
    den groessten zusaetzlichen Informationswert besitzt.
"""

import json

import pytest

from mathkomp import hypotheses, simulation, state, teacher
from mathkomp.config import Config


@pytest.fixture(scope="module")
def cfg(conn):
    return Config(conn)


@pytest.fixture(scope="module")
def alle(conn, cfg):
    """Alle sechs Testfaelle einmal durchgespielt."""
    return simulation.run_all(conn, cfg)


def status_of(conn, student_id, competency_id):
    row = conn.execute(
        "SELECT status, reactivation_reason FROM student_competency_state"
        " WHERE student_id = ? AND competency_id = ?", (student_id, competency_id)).fetchone()
    return (row["status"], row["reactivation_reason"]) if row else (None, None)


# ---------------------------------------------------------------- Testfall A


def test_a_hohe_kompetenz(alle, conn):
    """§98: Start D3 -> D5 -> Transfer -> SECURE -> PARKED.
    Erwartung ausdruecklich: keine unnoetigen D1/D2-Aufgaben."""
    trace = alle["A"]
    assert all(s.is_correct for s in trace.steps)
    assert trace.difficulties[0] == "D3", "§96: Start auf mittlerer Stufe"
    assert "D5" in trace.difficulties, "§34: D3 richtig -> D5"
    assert "TRANSFER" in [s.purpose for s in trace.steps], "§98 nennt Transfer"
    assert "D1" not in trace.difficulties, "§98: keine unnoetigen D1-Aufgaben"
    assert "D2" not in trace.difficulties, "§98: keine unnoetigen D2-Aufgaben"
    status, _ = status_of(conn, "SIM-A", "ZO09_MULTIPLICATION")
    assert status == "PARKED", "§38: SECURE -> PARKED"
    assert len(trace.steps) <= 5, "§73/§36: moeglichst wenige Aufgaben"


# ---------------------------------------------------------------- Testfall B


def test_b_grundlegende_schwierigkeit(alle, conn):
    """§99: D3 falsch -> Parallelitem falsch -> D1 -> Voraussetzung ->
    Rueckwaertsnavigation -> SUPPORT_FOCUS."""
    trace = alle["B"]
    assert trace.steps[0].is_correct is False
    assert trace.steps[1].is_correct is False
    assert trace.steps[1].purpose == "VERIFY", "§30: Fehler ueber Parallelitem replizieren"

    gruende = [s.selected_by for s in trace.steps]
    assert any("CHECK_PREREQUISITE" in (s.next_reason or "") for s in trace.steps), \
        "§31 Schritt 3: Voraussetzung pruefen"
    besuchte = trace.task_ids
    assert any(t.startswith("ZO06-1-") for t in besuchte), \
        "§69: Buendelung als Voraussetzung geprueft (Rueckwaertsnavigation)"

    status, _ = status_of(conn, "SIM-B", "ZO06_PLACE_VALUE")
    assert status == "SUPPORT_FOCUS", "§99 Erwartung"
    # §36: die Grenze wurde lokalisiert.
    row = conn.execute(
        "SELECT current_floor, current_ceiling FROM student_competency_state"
        " WHERE student_id = 'SIM-B' AND competency_id = 'ZO06_PLACE_VALUE'").fetchone()
    assert row["current_ceiling"] is not None


def test_b_voraussetzung_wird_eigenstaendig_belegt(alle, conn):
    """§99/§69: die gepruefte Voraussetzung erhaelt ihren eigenen Status -
    Buendelung gelingt, Stellenwert nicht. Genau diese Trennung macht den
    Unterschied zu einem Quizsystem (§124)."""
    buendelung, _ = status_of(conn, "SIM-B", "ZO06_1_BUNDLING")
    stellenwert, _ = status_of(conn, "SIM-B", "ZO06_PLACE_VALUE")
    assert buendelung in ("SECURE", "PARKED")
    assert stellenwert == "SUPPORT_FOCUS"


# ---------------------------------------------------------------- Testfall C


def test_c_repraesentation(alle, conn):
    """§100: SYMBOL falsch -> Parallel SYMBOL falsch -> IMAGE richtig ->
    Parallel IMAGE richtig -> REPRESENTATION_HYPOTHESIS.

    Zwischen dem symbolischen und dem ikonischen Teil liegt ein zusaetzlicher
    Schritt, den §31 verlangt: die Seed-Items fragen nach dem Wert einer ZIFFER,
    das ikonische Gegenstueck nach dem Wert einer STELLE. §31 nennt Aufgabentyp
    (Schritt 7) und Darstellung (Schritt 8) als getrennte Pruefebenen, und §116
    verlangt, nur eine Variable zu aendern. Also wird erst die Frageform
    gewechselt und symbolisch geblieben, dann die Darstellung.
    """
    trace = alle["C"]
    reihenfolge = [(s.representation, s.is_correct) for s in trace.steps[:6]]
    assert reihenfolge[0] == ("MATHEMATICAL_SYMBOL", False)
    assert reihenfolge[1] == ("MATHEMATICAL_SYMBOL", False)
    # §31 Schritt 7: Frageform gewechselt, noch symbolisch.
    assert reihenfolge[2] == ("MATHEMATICAL_SYMBOL", False)
    assert reihenfolge[3] == ("MATHEMATICAL_SYMBOL", False)
    # §31 Schritt 8: jetzt wechselt nur die Darstellung.
    assert reihenfolge[4] == ("IMAGE", True)
    assert reihenfolge[5] == ("IMAGE", True)
    assert [s.selected_by for s in trace.steps][2] == "R003"
    assert [s.selected_by for s in trace.steps][4] == "R032"
    assert "REPRESENTATION_HYPOTHESIS" in trace.hypothesis_types()

    offen = [h for h in hypotheses.open_hypotheses(conn, "SIM-C")
             if h["hypothesis_type"] == "REPRESENTATION_HYPOTHESIS"]
    assert offen, "§100 Erwartung"
    # §116: der Vergleich lief auf derselben Stufe.
    assert "MIXED_LEVELS" not in offen[0]["target_construct"]
    # §115: widerlegbar.
    assert offen[0]["falsifying_task"]


def test_c_kein_lerntyp_wird_behauptet(alle, conn):
    """§32: aus IMAGE richtig und SYMBOL falsch folgt NICHT 'visuelle:r
    Lerner:in'. Die Formulierung muss bedingungsbezogen bleiben."""
    for h in hypotheses.open_hypotheses(conn, "SIM-C"):
        text = hypotheses.describe(h).lower()
        for verboten in ("lerner", "lerntyp", "visuell", "begabung", "intelligenz",
                         "aufmerksam", "konzentration", "adhs"):
            assert verboten not in text, f"{verboten} in: {text}"


def test_c_darstellungsabhaengigkeit_als_marker(alle, conn):
    """§26 REPRESENTATION_DEPENDENT ist ein Marker, keine Diagnose."""
    row = conn.execute(
        "SELECT profile_markers FROM student_competency_state"
        " WHERE student_id = 'SIM-C' AND competency_id = 'ZO06_PLACE_VALUE'").fetchone()
    assert "REPRESENTATION_DEPENDENT" in json.loads(row["profile_markers"])


# ---------------------------------------------------------------- Testfall D


def test_d_zahlenabhaengigkeit(alle, conn):
    """§101: Addition wird NICHT pauschal herabgestuft. Erwartet werden
    Merkmalsvergleich, Hypothese und Contrast Item."""
    trace = alle["D"]
    assert "STRATEGY_DEPENDENCY_HYPOTHESIS" in trace.hypothesis_types()

    offen = [h for h in hypotheses.open_hypotheses(conn, "SIM-D")
             if h["hypothesis_type"] == "STRATEGY_DEPENDENCY_HYPOTHESIS"]
    assert offen
    assert any("COMPENSATION" in h["target_construct"] for h in offen), \
        "§71 nennt COMPENSATION_AVAILABLE fuer die erfolgreiche Seite"

    # §52: die Contrast Family wurde durchgearbeitet.
    kontraste = [s for s in trace.steps if s.purpose == "CONTRAST"]
    assert len(kontraste) >= 4


def test_d_facetten_zeigen_das_muster(alle, conn):
    """§117: statt eines Prozentwerts eine Aufschluesselung nach Bedingungen.

    Unter COMPENSATION ist die Leistung sicher, ohne nicht. Und die Facetten
    zeigen zugleich, warum NEAR_ROUND_NUMBER das falsche Kontrastmerkmal war:
    dort stehen Erfolge UND Fehler, weil nach der operandensymmetrischen Regel
    auch 37+28 einen runden Anker traegt (F-25).
    """
    facets = state.facets_of(conn, "SIM-D", "ZO07_ADDITION")
    strategie = facets.get("STRATEGY_AFFORDANCE", {})
    assert strategie["COMPENSATION"]["negative_count"] == 0
    assert strategie["COMPENSATION"]["positive_count"] >= 2
    assert strategie["COMPENSATION"]["status"] == "SECURE"

    numeric = facets.get("NUMERIC_FEATURE", {})
    assert numeric["NEAR_ROUND_NUMBER"]["negative_count"] > 0, \
        "F-25: das Merkmal trennt die Contrast Family nicht"


def test_d_marker_strategieabhaengig(alle, conn):
    """§26 STRATEGY_DEPENDENT."""
    row = conn.execute(
        "SELECT profile_markers FROM student_competency_state"
        " WHERE student_id = 'SIM-D' AND competency_id = 'ZO07_ADDITION'").fetchone()
    assert "STRATEGY_DEPENDENT" in json.loads(row["profile_markers"])


# ---------------------------------------------------------------- Testfall E


def test_e_gleiche_antwort_unterschiedliche_pfade(alle, conn):
    """§102, der schaerfste Testfall: zwei Schueler:innen geben auf dasselbe
    Item dieselbe falsche Antwort und muessen auf unterschiedliche Lernpfade
    geraten. 'Gleiche Ausgangsantwort darf zu unterschiedlichen Lernpfaden
    fuehren.'"""
    e1, e2 = alle["E1"], alle["E2"]

    # Gleicher Einstieg, gleiche erste Beobachtung.
    assert e1.task_ids[0] == e2.task_ids[0]
    assert e1.steps[0].is_correct is False and e2.steps[0].is_correct is False
    assert e1.steps[0].error_codes == e2.steps[0].error_codes

    # Ab dem ikonischen Item trennen sich die Wege.
    assert e1.task_ids != e2.task_ids

    # A: Darstellungsroute.
    assert "REPRESENTATION_HYPOTHESIS" in e1.hypothesis_types()
    # B: Grundvorstellungsroute.
    assert "REPRESENTATION_HYPOTHESIS" not in e2.hypothesis_types()
    assert any(t.startswith("ZO09-GV-") for t in e2.task_ids), \
        "§70: Grundvorstellung Multiplikation pruefen"
    assert "ERR_OPERATION_CONCEPT" in e2.error_codes(), \
        "§59/§70: die Operationsklasse wurde verwechselt"

    # Unterschiedlicher Endzustand.
    s1, _ = status_of(conn, "SIM-E1", "ZO09_MULTIPLICATION")
    s2, _ = status_of(conn, "SIM-E2", "ZO09_MULTIPLICATION")
    assert s1 != s2
    assert s2 == "SUPPORT_FOCUS", "§70: SUPPORT_FOCUS = MULTIPLICATION_CONCEPT"


# ---------------------------------------------------------------- Testfall F


def test_f_wiederaktivierung(alle, conn):
    """§103: ZO06 = PARKED, spaeter Stellenwertfehler, PARKED -> REACTIVATED
    -> VERIFY."""
    phase1, phase2 = alle["F1"], alle["F2"]
    assert any("PARKED" in t for t in phase1.transitions()), "§38"

    status, grund = status_of(conn, "SIM-F", "ZO06_PLACE_VALUE")
    assert grund in ("EVIDENCE_TOO_OLD", "CONTRADICTORY_EVIDENCE"), "§39"
    assert phase2.steps, "nach der Reaktivierung wird erneut geprueft"
    assert phase2.steps[0].purpose in ("VERIFY", "RECHECK", "SCREEN", "CONTRAST")
    assert status != "PARKED", "die Kompetenz ist zurueck im Pool"


def test_f_pfad_wird_nicht_geloescht(alle, conn):
    """§122: 'Ein Pfad wird nicht endgueltig geloescht. Er wird PARKED und kann
    spaeter reaktiviert werden.' Die Historie muss vollstaendig bleiben."""
    row = conn.execute(
        "SELECT parked_at, first_evidence FROM student_competency_state"
        " WHERE student_id = 'SIM-F' AND competency_id = 'ZO06_PLACE_VALUE'").fetchone()
    assert row["parked_at"] is not None, "der Parkzeitpunkt bleibt erhalten"
    assert row["first_evidence"] is not None, "§40: first_evidence bleibt erhalten"


# --------------------------------------------- Kriterium 20 aus §123


def test_sechs_testfaelle_erzeugen_unterschiedliche_pfade(alle):
    """§123 Kriterium 20 woertlich: 'die sechs Testfaelle erzeugen
    unterschiedliche erwartete Pfade'."""
    pfade = {name: tuple(trace.task_ids)
             for name, trace in alle.items() if name != "F2"}
    assert len(set(pfade.values())) == len(pfade), \
        f"Pfade nicht paarweise verschieden: {pfade}"


def test_jeder_testfall_endet_begruendet(alle):
    """§73 und §89: auch das Aufhoeren ist eine begruendete Entscheidung."""
    for name, trace in alle.items():
        assert trace.stop_reason, name


def test_jede_entscheidung_ist_nachvollziehbar(alle, conn):
    """§88: 'Warum hat das System diesen Pfad gewaehlt?'"""
    for student in ("SIM-A", "SIM-B", "SIM-C", "SIM-D", "SIM-E1", "SIM-E2", "SIM-F"):
        rows = conn.execute(
            "SELECT * FROM routing_decisions WHERE student_id = ?", (student,)).fetchall()
        assert rows, student
        for row in rows:
            assert row["rule_triggered"]
            assert row["confidence"] in ("LOW", "MEDIUM", "HIGH")
            assert json.loads(row["score_breakdown"]) or row["selected_task"] is None


def test_lehrkraftansicht_fuer_jeden_testfall(alle, conn, cfg):
    """§106: die Ansicht muss fuer jeden Verlauf lesbar sein, §117: ohne
    Prozentwert."""
    from mathkomp.clock import FixedClock
    for student in ("SIM-A", "SIM-B", "SIM-C", "SIM-D", "SIM-E1", "SIM-E2", "SIM-F"):
        text = teacher.render(teacher.report(conn, student, cfg, FixedClock()))
        assert "%" not in text, student
        assert "Status" in text
        profil = teacher.profile_summary(conn, student)
        assert student in profil


# --------------------------------------------- Definition of Done (§123)


def test_definition_of_done(alle, conn, cfg):
    """Die 20 Kriterien aus §123, jedes gegen eine pruefbare Tatsache."""
    def q(sql, *params):
        return conn.execute(sql, params).fetchone()[0]

    kriterien = {}

    # 1. Kompetenzknoten koennen importiert werden.
    kriterien[1] = q("SELECT COUNT(*) FROM competencies") >= 50
    # 2. Relationen funktionieren datenbankbasiert.
    kriterien[2] = q("SELECT COUNT(*) FROM relations") > 0 and q(
        "SELECT COUNT(*) FROM relations WHERE relation_type IS NULL") == 0
    # 3. Aufgaben besitzen Metadaten.
    kriterien[3] = q("SELECT COUNT(*) FROM task_features") > 0
    # 4. Aufgabenfamilien funktionieren.
    kriterien[4] = q("SELECT COUNT(*) FROM task_families") > 0
    # 5. Parallelitems sind verfuegbar.
    kriterien[5] = q("SELECT COUNT(*) FROM tasks WHERE parallel_item_id IS NOT NULL") > 0
    # 6. Fehler werden als Beobachtungen gespeichert.
    kriterien[6] = q("SELECT COUNT(*) FROM attempt_error_codes") > 0
    # 7. Fehler erzeugen nicht automatisch Diagnosen: es gibt Versuche mit
    #    Fehlercode, zu denen KEINE Hypothese existiert.
    kriterien[7] = q(
        "SELECT COUNT(*) FROM task_attempts a"
        " JOIN attempt_error_codes e ON e.attempt_id = a.attempt_id"
        " WHERE NOT EXISTS (SELECT 1 FROM student_hypotheses h"
        "                   WHERE h.student_id = a.student_id)") > 0
    # 8. Schwierigkeit navigiert hoch und runter.
    stufen = [s.difficulty for trace in alle.values() for s in trace.steps]
    kriterien[8] = len(set(stufen)) >= 3
    # 9. Skip-Level funktioniert: D3 richtig -> D5 (§34).
    kriterien[9] = "D5" in alle["A"].difficulties and "D4" not in alle["A"].difficulties
    # 10. Darstellung kann gewechselt werden.
    kriterien[10] = q(
        "SELECT COUNT(*) FROM routing_decisions WHERE rule_triggered IN"
        " (SELECT route_id FROM task_routes WHERE reason = 'CHANGE_REPRESENTATION')") > 0
    # 11. Zahlenstruktur wird beruecksichtigt.
    kriterien[11] = q(
        "SELECT COUNT(*) FROM student_competency_facets"
        " WHERE facet_kind = 'NUMERIC_FEATURE'") > 0
    # 12. Strategy Variation funktioniert.
    kriterien[12] = q(
        "SELECT COUNT(*) FROM student_hypotheses"
        " WHERE hypothesis_type = 'STRATEGY_DEPENDENCY_HYPOTHESIS'") > 0
    # 13. Contrast Items koennen ausgeloest werden.
    kriterien[13] = q(
        "SELECT COUNT(*) FROM routing_decisions d JOIN tasks t"
        " ON t.task_id = d.selected_task WHERE t.task_purpose = 'CONTRAST'") > 0
    # 14. Voraussetzungen werden rueckwaerts untersucht.
    kriterien[14] = q(
        "SELECT COUNT(*) FROM routing_decisions WHERE rule_triggered IN"
        " (SELECT route_id FROM task_routes WHERE reason = 'CHECK_PREREQUISITE')") > 0
    # 15. Kompetenzen werden geparkt.
    kriterien[15] = q(
        "SELECT COUNT(*) FROM student_competency_state WHERE parked_at IS NOT NULL") > 0
    # 16. Kompetenzen werden reaktiviert.
    kriterien[16] = q(
        "SELECT COUNT(*) FROM student_competency_state"
        " WHERE reactivation_reason IS NOT NULL") > 0
    # 17. Ein individueller aktiver Teilgraph entsteht.
    aktive = {row["student_id"]: row["n"] for row in conn.execute(
        "SELECT student_id, COUNT(*) AS n FROM student_competency_state"
        " GROUP BY student_id")}
    kriterien[17] = len(set(aktive.values())) > 1 and all(
        n < q("SELECT COUNT(*) FROM competencies") for n in aktive.values())
    # 18. Routing funktioniert ohne LLM.
    kriterien[18] = cfg.require("routing.llm_in_decision_path") is False
    # 19. Entscheidungen werden protokolliert.
    kriterien[19] = q("SELECT COUNT(*) FROM routing_decisions") > 0
    # 20. Die sechs Testfaelle erzeugen unterschiedliche Pfade.
    pfade = {n: tuple(t.task_ids) for n, t in alle.items() if n != "F2"}
    kriterien[20] = len(set(pfade.values())) == len(pfade)

    offen = sorted(k for k, erfuellt in kriterien.items() if not erfuellt)
    assert not offen, f"§123 Kriterien nicht erfuellt: {offen}"
    assert len(kriterien) == 20


def test_kein_llm_im_entscheidungspfad(alle):
    """§75/§76: 'Das LLM darf nicht die zentrale Routing-Engine sein.'

    Geprueft wird der Syntaxbaum, nicht der Text: die Modulkommentare SPRECHEN
    ueber das LLM-Verbot, und ein Textscan wuerde genau daran haengen.
    """
    import ast
    from pathlib import Path
    from mathkomp import routing

    verbotene_module = {"openai", "anthropic", "httpx", "requests", "urllib",
                        "http", "socket", "aiohttp"}
    for modul in ("routing.py", "state.py", "evidence.py", "hypotheses.py",
                  "parking.py", "scoring.py", "session.py", "attempts.py"):
        pfad = Path(routing.__file__).parent / modul
        baum = ast.parse(pfad.read_text(encoding="utf-8"))
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Import):
                for alias in knoten.names:
                    wurzel = alias.name.split(".")[0]
                    assert wurzel not in verbotene_module, f"{modul}: import {alias.name}"
            elif isinstance(knoten, ast.ImportFrom) and knoten.module:
                wurzel = knoten.module.split(".")[0]
                assert wurzel not in verbotene_module, f"{modul}: from {knoten.module}"
