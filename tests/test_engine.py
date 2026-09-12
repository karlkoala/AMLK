"""Engine-Tests: Sprint 4 bis 11.

Geprueft wird nicht, dass die Funktionen laufen, sondern dass sie die Grenzen
der Spezifikation einhalten - besonders §29 (ein Fehler ist keine Diagnose),
§121 (keine automatische Ferninferenz), §32 (kein Lerntyp), §62 (Zeit ist kein
Indikator) und §117 (kein Prozentwert).
"""

import json

import pytest

from mathkomp import (attempts, evidence, hypotheses, parking, renderer, routing,
                      scoring, state)
from mathkomp.attempts import Submission
from mathkomp.clock import FixedClock
from mathkomp.config import Config
from mathkomp.session import Session


@pytest.fixture
def cfg(conn):
    return Config(conn)


@pytest.fixture
def clock():
    return FixedClock()


def task(conn, task_id):
    return attempts.load_task(conn, task_id)


# --------------------------------------------------------- Sprint 4: Scoring


def test_normalisierung_akzeptiert_mehrere_schreibweisen():
    """§49: das Scoring darf nicht unnoetig nur eine Schreibweise akzeptieren."""
    assert scoring.normalize_expression("5*8 + 1*8") == scoring.normalize_expression("1*8+5*8")
    assert scoring.normalize_expression("10·6 + 7·6") == scoring.normalize_expression("7*6+10*6")
    # Subtraktion ist nicht kommutativ, die Reihenfolge muss erhalten bleiben.
    assert scoring.normalize_expression("403-200+2") != scoring.normalize_expression("403+200-2")


def test_zahlenantwort_wird_ausgewertet(conn):
    result = scoring.score(task(conn, "ZO07-D2-S-A"), 65)
    assert result.is_correct
    assert scoring.score(task(conn, "ZO07-D2-S-A"), 64).is_correct is False


def test_mehrere_akzeptierte_antworten(conn):
    """§49 ZO05-D4-S-A: mehrere Zerlegungen sind mathematisch sinnvoll."""
    item = task(conn, "ZO05-D4-S-A")
    assert item["scoring_rule"] == "ANY_OF_ACCEPTED"
    accepted = json.loads(item["correct_answer"])["accepted"]
    assert len(accepted) >= 2
    for answer in accepted:
        assert scoring.score(item, answer).is_correct, answer


def test_nullstellenfehler_wird_als_beobachtung_erkannt(conn):
    """§66 Musterbeispiel: 508 wird als 58 notiert."""
    item = task(conn, "ZO06-D3-S-A")
    result = scoring.score(item, 58)
    ctx = scoring.ClassificationContext(features=attempts.task_features(conn, item["task_id"]))
    codes = scoring.classify(item, 58, result, ctx)
    assert "ERR_ZERO_PLACEHOLDER" in codes


def test_endnull_ist_kein_nullstellenfehler(conn):
    """Abgrenzung nach D-14: 60 als 6 beantwortet ist ERR_PLACE_VALUE, nicht
    ERR_ZERO_PLACEHOLDER - sonst waeren die beiden Codes aus §59 nicht
    trennscharf."""
    item = task(conn, "ZO06-D2-S-A")
    result = scoring.score(item, 6)
    ctx = scoring.ClassificationContext(features=attempts.task_features(conn, item["task_id"]))
    codes = scoring.classify(item, 6, result, ctx)
    assert "ERR_PLACE_VALUE" in codes
    assert "ERR_ZERO_PLACEHOLDER" not in codes


def test_ausgelassenes_objekt_wird_erkannt(conn):
    """§42 verlangt ausdruecklich das Speichern ausgelassener Objekte."""
    item = task(conn, "ZP01-D1-I-A")
    events = [{"event_type": "CLICK", "object_id": f"obj{i}"} for i in range(1, 6)]
    result = scoring.score(item, 5)
    ctx = scoring.ClassificationContext(
        features=attempts.task_features(conn, item["task_id"]), events=events)
    codes = scoring.classify(item, 5, result, ctx)
    assert "ERR_OMISSION" in codes


def test_doppelt_gezaehltes_objekt_wird_erkannt(conn):
    item = task(conn, "ZP01-D1-I-A")
    events = [{"event_type": "CLICK", "object_id": o}
              for o in ("o1", "o2", "o3", "o4", "o5", "o5")]
    result = scoring.score(item, 6)
    ctx = scoring.ClassificationContext(
        features=attempts.task_features(conn, item["task_id"]), events=events)
    codes = scoring.classify(item, 6, result, ctx)
    assert "ERR_DOUBLE_COUNT" in codes


def test_selbstkorrektur_wird_auch_bei_richtiger_antwort_erfasst(conn):
    """§61 fuehrt ANSWER_CHANGE als Ereignistyp; §59 ERR_SELF_CORRECTED ist
    kein Fehler im engeren Sinn."""
    item = task(conn, "ZO07-D2-S-A")
    result = scoring.score(item, 65)
    ctx = scoring.ClassificationContext(
        features=attempts.task_features(conn, item["task_id"]),
        events=[{"event_type": "ANSWER_CHANGE"}, {"event_type": "SUBMIT"}])
    codes = scoring.classify(item, 65, result, ctx)
    assert codes == ["ERR_SELF_CORRECTED"]


def test_darstellungscode_wird_nie_aus_einem_versuch_vergeben(conn):
    """§32: aus einem Darstellungsunterschied folgt kein Lerntyp, und aus einem
    EINZELNEN Versuch folgt gar kein Darstellungsunterschied (D-14)."""
    for task_id in ("ZO06-D2-S-A", "ZO06-D2-I-A", "ZO09-D2-S-A"):
        item = task(conn, task_id)
        result = scoring.score(item, -999)
        ctx = scoring.ClassificationContext(
            features=attempts.task_features(conn, task_id))
        assert "ERR_REPRESENTATION" not in scoring.classify(item, -999, result, ctx)


def test_jede_falsche_antwort_erzeugt_mindestens_eine_beobachtung(conn):
    """§66 Ebene 1: eine falsche Antwort ohne Beobachtung waere nicht
    interpretierbar. ERR_SINGLE ist der Auffangcode (D-14)."""
    from mathkomp import simulation
    for row in conn.execute("SELECT task_id FROM tasks ORDER BY task_id"):
        item = task(conn, row["task_id"])
        features = attempts.task_features(conn, item["task_id"])
        wrong = simulation.plausible_wrong_answer(conn, item, features)
        result = scoring.score(item, wrong)
        if result.is_correct:
            continue
        ctx = scoring.ClassificationContext(features=features)
        codes = scoring.classify(item, wrong, result, ctx)
        assert codes, item["task_id"]


# -------------------------------------------------------- Sprint 4: Renderer


def test_renderer_trennt_darstellung_von_bedienform(conn):
    """§17: zwei unterschiedliche Variablen."""
    spec = renderer.render(task(conn, "ZO06-D2-I-A"))
    assert spec["representation"]["mode"] == "IMAGE"
    assert spec["interaction"]["mode"] == "ENTER"
    assert "mode" not in set(spec["representation"]) & set(spec["interaction"]) - {"mode"}


def test_renderer_verweigert_unvollstaendiges_item(conn):
    """§113: ein Item ohne Distraktoren wird nicht ausgeliefert."""
    conn.execute(
        "UPDATE tasks SET task_payload = json_set(task_payload, '$.options_status',"
        " 'UNDEFINED') WHERE task_id = 'ZO07-GV-D1-I-A'")
    with pytest.raises(scoring.UndeliverableTask):
        renderer.render(task(conn, "ZO07-GV-D1-I-A"))
    conn.rollback()


def test_jedes_item_ist_auslieferbar(conn):
    """Nach D-09 und D-10 darf kein Item mehr an §113 scheitern."""
    nicht_auslieferbar = []
    for row in conn.execute("SELECT task_id FROM tasks ORDER BY task_id"):
        try:
            renderer.render(task(conn, row["task_id"]))
        except scoring.UndeliverableTask as exc:
            nicht_auslieferbar.append(str(exc))
    assert nicht_auslieferbar == []


def test_zaehlaufgabe_verlangt_objekt_ids(conn):
    """§42: Klickreihenfolge, ausgelassene Objekte, doppelte Klicks."""
    spec = renderer.render(task(conn, "ZP01-D1-I-A"))
    assert spec["interaction"]["record_object_ids"] is True
    assert "CLICK" in spec["required_events"]


# -------------------------------------------------------- Sprint 6: Evidenz


def test_richtige_antwort_erzeugt_indirekt_positive_evidenz_auf_voraussetzung(
        conn, cfg, clock):
    """§121: die Kette wird genutzt, um ein Item auszuwaehlen - und indirekte
    Evidenz reicht genau einen Schritt (§31)."""
    session = Session(conn, "EV-1", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=60))
    rows = list(conn.execute(
        "SELECT competency_id, evidence_type FROM evidence_events WHERE student_id = 'EV-1'"))
    types = {(r["competency_id"], r["evidence_type"]) for r in rows}
    assert ("ZO06_PLACE_VALUE", "DIRECT_POSITIVE") in types
    assert any(t == "INDIRECT_POSITIVE" for _, t in types)
    conn.rollback()


def test_falsche_antwort_erzeugt_keine_indirekt_negative_evidenz_auf_voraussetzung(
        conn, cfg, clock):
    """§29 und §121: aus 'Aufgabe falsch' folgt NICHT 'Voraussetzung fehlt'.
    Der Fehler loest nach §30 ein Parallelitem aus, keine Ferninferenz."""
    session = Session(conn, "EV-2", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=6))
    prerequisites = {r["source_competency"] for r in conn.execute(
        "SELECT source_competency FROM relations WHERE target_competency ="
        " 'ZO06_PLACE_VALUE' AND relation_type IN"
        " ('HARD_PREREQUISITE','STRONG_PREREQUISITE')")}
    negatives = {r["competency_id"] for r in conn.execute(
        "SELECT competency_id FROM evidence_events WHERE student_id = 'EV-2'"
        " AND evidence_type = 'INDIRECT_NEGATIVE'")}
    assert not (negatives & prerequisites)
    conn.rollback()


def test_unterstuetzte_loesung_erhaelt_eigenen_evidenztyp(conn, cfg, clock):
    """§33: Leistung mit und ohne Unterstuetzung sind verschiedene
    Beobachtungen."""
    session = Session(conn, "EV-3", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=60, support_used=True))
    rows = list(conn.execute(
        "SELECT evidence_type, strength FROM evidence_events WHERE student_id = 'EV-3'"))
    assert any(r["evidence_type"] == "SUPPORT_EVIDENCE" for r in rows)
    direct = next(r for r in rows if r["evidence_type"] == "DIRECT_POSITIVE")
    assert direct["strength"] < cfg.require("evidence.weight_direct")
    conn.rollback()


def test_konsistenz_null_bei_haelftigem_widerspruch():
    assert evidence.consistency(2, 2) == 0.0
    assert evidence.consistency(3, 0) == 1.0
    assert evidence.consistency(0, 0) is None


# -------------------------------------------- Sprint 8: Zustand und Facetten


def test_status_trennt_stufengrenze_von_merkmalsstreuung(conn, cfg, clock):
    """§99 gegen §101: eine reproduzierbare Grenze auf einer Stufe ist
    SUPPORT_FOCUS, Streuung innerhalb einer Stufe ist UNCERTAIN. §117: die
    Stufen werden nicht zu einem Wert aggregiert."""
    grenze = [{"internal_difficulty": "D2", "is_correct": 0},
              {"internal_difficulty": "D2", "is_correct": 0}]
    streuung = [{"internal_difficulty": "D3", "is_correct": 1},
                {"internal_difficulty": "D3", "is_correct": 1},
                {"internal_difficulty": "D3", "is_correct": 0},
                {"internal_difficulty": "D3", "is_correct": 0}]
    assert state._status_from_history(grenze, cfg) == "SUPPORT_FOCUS"
    assert state._status_from_history(streuung, cfg) == "UNCERTAIN"
    assert state._status_from_history([], cfg) == "UNKNOWN"


def test_facetten_statt_prozentwert(conn, cfg, clock):
    """§117: nicht '73 % richtig', sondern Status je Bedingung."""
    session = Session(conn, "FA-1", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=6))
    session.submit(Submission(task_id="ZO06-D2-I-A", answer=60))
    facets = state.facets_of(conn, "FA-1", "ZO06_PLACE_VALUE")
    assert facets["REPRESENTATION_MODE"]["MATHEMATICAL_SYMBOL"]["negative_count"] == 1
    assert facets["REPRESENTATION_MODE"]["IMAGE"]["positive_count"] == 1
    assert "INTERNAL_DIFFICULTY" in facets
    conn.rollback()


def test_kompetenzfenster_wird_eingegrenzt(conn, cfg, clock):
    """§34 und §36: Unter- und Obergrenze bilden das Kompetenzfenster."""
    session = Session(conn, "FE-1", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D1-I-A", answer=47))
    session.submit(Submission(task_id="ZO06-D1-I-B", answer=63))
    session.submit(Submission(task_id="ZO06-D4-S-A", answer=4))
    session.submit(Submission(task_id="ZO06-D4-S-B", answer=43))
    row = conn.execute(
        "SELECT current_floor, current_ceiling FROM student_competency_state"
        " WHERE student_id = 'FE-1' AND competency_id = 'ZO06_PLACE_VALUE'").fetchone()
    assert row["current_floor"] == "D1"
    assert row["current_ceiling"] == "D4"
    conn.rollback()


# ------------------------------------------------- Sprint 6/10: Hypothesen


def test_hypothese_braucht_gleiche_bedingungen(conn, cfg, clock):
    """§116 und §32: ein Vergleich, der neben der Darstellung noch etwas anderes
    aendert, laesst den Unterschied nicht der Darstellung zuordnen (D-24, D-28).

    Zwei Faelle, beide muessen blockieren.
    """
    # 1. Verschiedene Stufen: symbolisch D2, ikonisch D1.
    session = Session(conn, "HY-1", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-C", answer=6))
    session.submit(Submission(task_id="ZO06-D2-S-D", answer=7))
    session.submit(Submission(task_id="ZO06-D1-I-A", answer=47))
    session.submit(Submission(task_id="ZO06-D1-I-B", answer=63))
    offen = [h for h in hypotheses.open_hypotheses(conn, "HY-1")
             if h["hypothesis_type"] == "REPRESENTATION_HYPOTHESIS"]
    assert offen == [], "verschiedene Schwierigkeitsstufen"
    conn.rollback()

    # 2. Gleiche Stufe, aber verschiedene Frageform: die Seed-Items fragen nach
    #    dem Wert einer ZIFFER, das ikonische Gegenstueck nach dem Wert einer
    #    STELLE (Kritikbefund 6).
    session = Session(conn, "HY-1b", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=6))
    session.submit(Submission(task_id="ZO06-D2-S-B", answer=7))
    session.submit(Submission(task_id="ZO06-D2-I-A", answer=60))
    session.submit(Submission(task_id="ZO06-D2-I-B", answer=70))
    offen = [h for h in hypotheses.open_hypotheses(conn, "HY-1b")
             if h["hypothesis_type"] == "REPRESENTATION_HYPOTHESIS"]
    assert offen == [], "verschiedene Frageform"
    conn.rollback()


def test_hypothese_entsteht_bei_gleicher_stufe(conn, cfg, clock):
    """§88 und §100: zwei symbolische Fehler und zwei ikonische Erfolge auf
    derselben Stufe, mit demselben Antwortformat UND derselben Frageform,
    eroeffnen die Darstellungshypothese.

    Verwendet werden ZO06-D2-S-C/-S-D, nicht die Seed-Items ZO06-D2-S-A/-S-B:
    diese fragen nach dem Wert einer ZIFFER, das ikonische Gegenstueck nach dem
    Wert einer STELLE. Der Vergleich waere nach §116 konfundiert - genau das
    prueft test_hypothese_braucht_gleiche_bedingungen.
    """
    session = Session(conn, "HY-2", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-C", answer=6))
    session.submit(Submission(task_id="ZO06-D2-S-D", answer=7))
    session.submit(Submission(task_id="ZO06-D2-I-A", answer=60))
    session.submit(Submission(task_id="ZO06-D2-I-B", answer=70))
    offen = [h for h in hypotheses.open_hypotheses(conn, "HY-2")
             if h["hypothesis_type"] == "REPRESENTATION_HYPOTHESIS"]
    assert len(offen) == 1
    assert offen[0]["falsifying_task"] is not None
    beschreibung = hypotheses.describe(offen[0])
    # §32: eine Aussage ueber Bedingungen, nicht ueber die Person.
    for verboten in ("Lerner", "Begabung", "Aufmerksamkeit", "visuell", "Typ"):
        assert verboten.lower() not in beschreibung.lower()
    assert "koennte" in beschreibung or "könnte" in beschreibung
    conn.rollback()


def test_ein_einzelner_fehler_erzeugt_keine_hypothese(conn, cfg, clock):
    """§29: ein Fehler ist keine Diagnose. §30: erst die Replikation."""
    session = Session(conn, "HY-3", clock, cfg=cfg)
    turn = session.submit(Submission(task_id="ZO06-D3-S-A", answer=58))
    assert turn.error_codes == ["ERR_ZERO_PLACEHOLDER"]
    assert hypotheses.open_hypotheses(conn, "HY-3") == []
    conn.rollback()


def test_hypothese_ohne_widerlegendes_item_wird_nicht_eroeffnet(conn, cfg, clock):
    """§115 Grundsatz der Widerlegbarkeit, technisch erzwungen."""
    action = hypotheses._open_or_update(
        conn, "HY-4", "REPRESENTATION_HYPOTHESIS", "TEST:ohne:Item", None,
        ["a1"], [], 50, cfg, clock, "§115")
    assert action.action == "BLOCKED_NOT_FALSIFIABLE"
    conn.rollback()


# ------------------------------------------------- Sprint 9: Parken


def test_parken_verlangt_zwei_verschiedene_items(conn, cfg, clock):
    """D-05 zu §38: zwei richtige Versuche an DERSELBEN Aufgabe sind keine
    ausreichend konsistente Evidenz (§19, §26 ITEM_SPECIFIC_SUCCESS)."""
    session = Session(conn, "PA-1", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D1-I-A", answer=47))
    session.submit(Submission(task_id="ZO06-D1-I-A", answer=47))
    row = conn.execute(
        "SELECT status, profile_markers FROM student_competency_state"
        " WHERE student_id = 'PA-1' AND competency_id = 'ZO06_PLACE_VALUE'").fetchone()
    assert row["status"] != "PARKED"
    conn.rollback()


def test_parken_und_reaktivieren(conn, cfg, clock):
    """§38 und §39. Der Reaktivierungsgrund wird protokolliert."""
    session = Session(conn, "PA-2", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D1-I-A", answer=47))
    session.submit(Submission(task_id="ZO06-D1-I-B", answer=63))
    row = conn.execute(
        "SELECT status FROM student_competency_state WHERE student_id = 'PA-2'"
        " AND competency_id = 'ZO06_PLACE_VALUE'").fetchone()
    assert row["status"] == "PARKED"

    clock.advance(days=cfg.require("park.evidence_too_old_days") + 1)
    transition = parking.check_reactivation(conn, "PA-2", "ZO06_PLACE_VALUE", cfg, clock)
    assert transition is not None
    assert transition.reason == "EVIDENCE_TOO_OLD"
    conn.rollback()


def test_lehrkraft_kann_sperren(conn, cfg, clock):
    """§3: die Lehrkraft kann Systementscheidungen uebersteuern."""
    session = Session(conn, "PA-3", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D1-I-A", answer=47))
    parking.set_blocked(conn, "PA-3", "ZO06_PLACE_VALUE", clock)
    result = state.recompute(conn, "PA-3", "ZO06_PLACE_VALUE", cfg, clock)
    assert result.status == "BLOCKED"
    nodes = routing.active_nodes(conn, "PA-3", cfg)
    assert "ZO06_PLACE_VALUE" not in nodes
    conn.rollback()


# ------------------------------------------------- Sprint 7: Routing


def test_routing_protokolliert_jede_entscheidung(conn, cfg, clock):
    """§89 Explainability Logging."""
    session = Session(conn, "RO-1", clock, cfg=cfg)
    decision = session.next_task()
    row = conn.execute(
        "SELECT * FROM routing_decisions WHERE decision_id = ?",
        (decision.decision_id,)).fetchone()
    assert row is not None
    assert row["selected_task"] == decision.selected_task
    assert json.loads(row["alternatives_considered"])
    assert json.loads(row["score_breakdown"])
    assert row["confidence"] in ("LOW", "MEDIUM", "HIGH")
    conn.rollback()


def test_startstufe_ist_nicht_die_leichteste(conn, cfg, clock):
    """§96: nicht automatisch bei der leichtesten Aufgabe beginnen."""
    session = Session(conn, "RO-2", clock, cfg=cfg, focus={"ZO09_MULTIPLICATION"})
    decision = session.next_task()
    item = task(conn, decision.selected_task)
    assert item["internal_difficulty"] != "D1"
    conn.rollback()


def test_route_aus_paragraph_83_greift(conn, cfg, clock):
    """§83 definiert R001 woertlich: ZO09-REL-D3-S-A falsch -> ZO09-REL-D3-S-B."""
    session = Session(conn, "RO-3", clock, cfg=cfg, focus={"ZO09_MULTIPLICATION"})
    turn = session.submit(Submission(task_id="ZO09-REL-D3-S-A", answer=47))
    assert turn.next_decision.selected_task == "ZO09-REL-D3-S-B"
    assert turn.next_decision.rule_triggered == "R001"
    conn.rollback()


def test_geparkte_kompetenz_verlaesst_den_pool(conn, cfg, clock):
    """§38: aus dem normalen aktiven Aufgabenpool entfernt."""
    session = Session(conn, "RO-4", clock, cfg=cfg, focus={"ZO06_PLACE_VALUE"})
    session.submit(Submission(task_id="ZO06-D1-I-A", answer=47))
    session.submit(Submission(task_id="ZO06-D1-I-B", answer=63))
    nodes = routing.active_nodes(conn, "RO-4", cfg)
    assert "ZO06_PLACE_VALUE" not in nodes
    conn.rollback()


def test_nicht_uebertesten(conn, cfg, clock):
    """§73: das System entscheidet auch, NICHT weiterzutesten."""
    session = Session(conn, "RO-5", clock, cfg=cfg, focus={"ZO13_ARITHMETIC_LAWS"})
    for _ in range(8):
        decision = session.next_task()
        if decision.selected_task is None:
            assert decision.stop_reason is not None
            assert "§73" in decision.explanation or "73" in decision.explanation
            conn.rollback()
            return
        session.submit(Submission(task_id=decision.selected_task,
                                  answer=json.loads(
                                      task(conn, decision.selected_task)["correct_answer"]
                                  ).get("selection")))
    pytest.fail("Das System hat nicht aufgehoert zu testen")


def test_skip_level_folgt_der_konfiguration(conn, cfg, clock):
    """§34/§35: die Spruenge stehen in system_config, nicht im Code."""
    skip_map = cfg.require("routing.skip_level_map")
    assert skip_map["D3"]["success"] == "D5"
    assert skip_map["D3"]["failure"] == "D1"
    assert skip_map["D5"]["failure"] == "D4"


def test_keine_aufgaben_id_im_routing_code():
    """§84: 'Nicht: if(task === "ZO09...")'."""
    import re
    from pathlib import Path
    source = Path(routing.__file__).read_text(encoding="utf-8")
    for number, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"'):
            continue
        assert not re.search(r"['\"](ZO|ZP)\d", line), f"routing.py:{number}"


# ------------------------------------------------- Lehrkraftansicht


def test_lehrkraftansicht_zeigt_keinen_prozentwert(conn, cfg, clock):
    """§117: 'Kompetenz nicht aus Prozentwert bilden'."""
    from mathkomp import teacher
    session = Session(conn, "TE-1", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=6))
    session.submit(Submission(task_id="ZO06-D2-I-A", answer=60))
    text = teacher.render(teacher.report(conn, "TE-1", cfg, clock))
    assert "%" not in text
    assert "Konsistenz" in text
    conn.rollback()


def test_lehrkraftansicht_enthaelt_die_pflichtfelder(conn, cfg, clock):
    """§106: Kompetenz, Status, Evidenz, letzte Aufgaben, offene Hypothesen,
    aktueller Foerderbereich, naechster geplanter Schritt."""
    from mathkomp import teacher
    session = Session(conn, "TE-2", clock, cfg=cfg, focus={"ZO06_PLACE_VALUE"})
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=6))
    session.submit(Submission(task_id="ZO06-D2-S-B", answer=7))
    session.next_task()
    text = teacher.render(teacher.report(conn, "TE-2", cfg, clock))
    for feld in ("Status", "Evidenz", "Letzte Aufgaben", "NAECHSTER SCHRITT",
                 "Konfidenz", "Regel"):
        assert feld in text, feld
    conn.rollback()


def test_zeit_wird_gespeichert_aber_nicht_interpretiert(conn, cfg, clock):
    """§62: 'langsam = schwache Kompetenz ist nicht zulaessig'."""
    session = Session(conn, "TE-3", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=60, time_seconds=900.0))
    row = conn.execute(
        "SELECT time_seconds FROM task_attempts WHERE student_id = 'TE-3'").fetchone()
    assert row["time_seconds"] == 900.0
    assert cfg.require("evidence.time_seconds_used_for_inference") is False
    result = state.recompute(conn, "TE-3", "ZO06_PLACE_VALUE", cfg, clock)
    assert result.status in ("ACTIVE", "SECURE")
    conn.rollback()


def test_parallelitem_folgt_auf_jeden_fehler(conn):
    """§30: "A falsch -> B Parallelitem". §67 nennt "replicate error" als erste
    Prioritaet, §31 das Parallelitem als Rang 2 von 12.

    tasks.parallel_item_id trug diese Beziehung lange nur als Datenfeld: das
    Routing las es nirgends. Fuenf Items hatten eine ausdrueckliche
    REPLICATE_ERROR-Route, die uebrigen dreizehn trafen ihr Parallelitem nur
    dann, wenn der ergebnisblinde Familienbonus zufaellig reichte - bei drei
    Items reichte er nicht. Dieser Test haelt die Regel fest, nicht den Zufall.
    """
    from mathkomp.attempts import Submission
    from mathkomp.session import Session

    paare = [(r["task_id"], r["parallel_item_id"]) for r in conn.execute(
        "SELECT task_id, parallel_item_id FROM tasks"
        " WHERE parallel_item_id IS NOT NULL ORDER BY task_id")]
    assert paare, "keine Parallelitems im Content"

    verfehlt = []
    for i, (task_id, parallel) in enumerate(paare):
        student = f"REPL-{i:03d}"
        session = Session(conn, student, FixedClock(), Config(conn), grade_reference=3)
        turn = session.submit(Submission(
            task_id=task_id, answer="___absichtlich_falsch___",
            events=[{"event_type": "SUBMIT"}]))
        assert not turn.is_correct, f"{task_id}: Testantwort war unerwartet richtig"
        gewaehlt = turn.next_decision.selected_task
        if gewaehlt != parallel:
            verfehlt.append(f"{task_id}: erwartet {parallel}, gewaehlt {gewaehlt}")

    assert not verfehlt, ("§30 verlangt nach einem Fehler das Parallelitem:\n  "
                          + "\n  ".join(verfehlt))


def test_repliziert_wird_nur_bis_das_muster_feststeht(conn):
    """§30 verlangt die Wiederholung, §73 verbietet das Uebertesten.

    Ist der Fehler repliziert, ist die Replikation erledigt und §31 geht zu
    Rang 3 weiter. Ohne diese Schranke repliziert das System auf jeder Stufe
    erneut - Testfall B lief dadurch von vier auf sieben Aufgaben, ohne eine
    einzige zusaetzliche Beobachtung.
    """
    from mathkomp import routing

    from mathkomp.attempts import Submission
    from mathkomp.session import Session

    cfg = Config(conn)
    noetig = int(cfg.require("mastery.failure_replication_required"))
    student = "REPL-GATE"
    session = Session(conn, student, FixedClock(), Config(conn), grade_reference=3)

    gesehen = []
    for durchgang in range(noetig):
        turn = session.submit(Submission(task_id="ZO06-D2-S-A", answer="___falsch___",
                                         events=[{"event_type": "SUBMIT"}]))
        assert not turn.is_correct
        gesehen = turn.error_codes
        last = {"task_id": "ZO06-D2-S-A", "competency_id": "ZO06_PLACE_VALUE",
                "difficulty": "D2", "representation": "MATHEMATICAL_SYMBOL",
                "is_correct": False, "error_codes": gesehen, "repeated": False}
        offen = routing._replication_pending(conn, student, last, cfg)
        if durchgang < noetig - 1:
            assert offen, f"nach {durchgang + 1} Fehlversuch steht die Replikation noch aus"

    assert not routing._replication_pending(conn, student, last, cfg), \
        "§73: nach erreichter Replikation darf nicht weiter repliziert werden"


def test_replikation_ignoriert_den_selbstkorrektur_code(conn):
    """ERR_SELF_CORRECTED beschreibt den Bearbeitungsverlauf, nicht das
    Fehlermuster. Zaehlte er mit, waeren beliebige Fehler 'aehnlich' und §30
    waere ausgehebelt - die Replikation gaelte dann als erledigt, ohne dass
    zweimal dasselbe beobachtet wurde."""
    from mathkomp import routing

    last = {"task_id": "ZO06-D2-S-A", "competency_id": "ZO06_PLACE_VALUE",
            "difficulty": "D2", "representation": "MATHEMATICAL_SYMBOL",
            "is_correct": False, "error_codes": ["ERR_SELF_CORRECTED"], "repeated": False}
    assert not routing._replication_pending(conn, "REPL-SELF", last, Config(conn)), \
        "ohne benennbares Fehlermuster gibt es nichts zu replizieren"
