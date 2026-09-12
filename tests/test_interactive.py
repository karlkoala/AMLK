"""Die interaktive Oberflaeche (§105).

Der wichtigste Test ist der Rundlauf: fuer JEDE Aufgabe der Bank wird die
richtige Antwort so eingetippt, wie eine Schueler:in sie eintippen wuerde, durch
interactive.collect() geschickt und von scoring.score() bewertet. Wenn dabei
irgendwo "falsch" herauskommt, misst die Oberflaeche etwas anderes als die
Engine - und die gesamte Diagnostik haengt an einer Eingabemaske, nicht an der
Kompetenz. Das waere der schwerste denkbare Fehler in diesem System.

Der zweite Test betrifft §42: Klickreihenfolge, ausgelassene Objekte und doppelte
Klicks sind ausdruecklich zu speichern. In der Simulation entstehen ERR_OMISSION
und ERR_DOUBLE_COUNT; hier wird geprueft, dass sie auch ueber die Tastatur
erreichbar sind - sonst gaebe es die beiden Fehlercodes im Echtbetrieb nie.
"""

from __future__ import annotations

import json

import pytest

from mathkomp import attempts, interactive, renderer, scoring


def _reader(*lines: str):
    """Ein input()-Ersatz, der die vorgegebenen Zeilen der Reihe nach liefert."""
    it = iter(lines)

    def read(_prompt: str) -> str:
        return next(it)

    return read


def _typed_answer(task: dict, spec: dict) -> list[str]:
    """Die richtige Antwort in der Form, in der sie jemand eintippen wuerde."""
    correct = json.loads(task["correct_answer"])
    payload = json.loads(task["task_payload"] or "{}")
    rule, mode = task["scoring_rule"], task["interaction_mode"]

    if mode == "CLICK_SEQUENCE" and payload.get("objects"):
        # Erste Zeile leer = alle Objekte der Reihe nach, zweite die Gesamtzahl.
        return ["", str(correct["value"])]
    if rule in ("SELECT_ONE", "BOOLEAN"):
        options = spec["interaction"]["options"]
        return [str(options.index(correct["selection"]) + 1)]
    if rule == "SELECT_MULTIPLE":
        options = spec["interaction"]["options"]
        return [" ".join(str(options.index(s) + 1) for s in correct["selection"])]
    if rule in ("SEQUENCE_EXACT", "SET_EXACT"):
        return [" ".join(str(v) for v in correct["sequence"])]
    if rule == "ANY_OF_ACCEPTED":
        return [str(correct["accepted"][0])]
    if rule == "EXPRESSION_EQUIVALENT":
        return [str(correct.get("expression", correct.get("value")))]
    if rule == "INTERACTION_COUNT":
        return [str(correct["interactions"])]
    if rule == "PLACED_OBJECT_COUNT":
        return [str(correct["placed"])]
    if rule == "GROUP_PARTITION":
        return [" ".join(str(v) for v in correct.values() if isinstance(v, (int, float)))]
    return [str(correct["value"])]


def _all_tasks(conn):
    return [attempts.load_task(conn, r["task_id"])
            for r in conn.execute("SELECT task_id FROM tasks ORDER BY task_id")]


def test_eingetippte_richtige_antwort_wird_als_richtig_gewertet(conn):
    """Rundlauf ueber die gesamte Aufgabenbank.

    §105 beschreibt die Oberflaeche als duenne Schicht: Aufgabe, Interaktion,
    Antwort, Feedback. Duenn heisst, dass sie die Antwort nicht veraendert.
    """
    fehler = []
    for task in _all_tasks(conn):
        spec = renderer.render(task)
        answer, _events = interactive.collect(task, spec, _reader(*_typed_answer(task, spec)))
        result = scoring.score(task, answer)
        if not result.is_correct:
            fehler.append(f"{task['task_id']} ({task['scoring_rule']}): "
                          f"eingegeben {answer!r}, erwartet {task['correct_answer']}")
    assert not fehler, "Richtige Antwort wurde als falsch gewertet:\n  " + "\n  ".join(fehler)


def test_jede_scoring_rule_ist_abgedeckt(conn):
    """Der Rundlauf ist nur so viel wert wie seine Abdeckung."""
    regeln = {r["scoring_rule"] for r in conn.execute("SELECT DISTINCT scoring_rule FROM tasks")}
    modi = {r["interaction_mode"] for r in conn.execute(
        "SELECT DISTINCT interaction_mode FROM tasks")}
    assert len(regeln) >= 10, f"nur {len(regeln)} Scoring-Regeln in der Bank"
    assert len(modi) >= 4, f"nur {len(modi)} Interaktionsformen in der Bank"


def test_option_kann_als_text_statt_als_nummer_eingegeben_werden(conn):
    task = attempts.load_task(conn, "ZP05-D1-A")  # BOOLEAN, Optionen JA / NEIN
    spec = renderer.render(task)
    answer, _ = interactive.collect(task, spec, _reader("ja"))
    assert scoring.score(task, answer).is_correct


def test_unsinnige_eingabe_wird_als_falsche_antwort_erfasst_nicht_abgewiesen(conn):
    """§59: eine unsinnige Antwort ist eine Beobachtung. Die Oberflaeche darf
    sie nicht verschlucken, sonst fehlt der Versuch in den Rohdaten (§60)."""
    task = attempts.load_task(conn, "ZO06-D3-S-A")
    spec = renderer.render(task)
    answer, _ = interactive.collect(task, spec, _reader("weiss nicht"))
    assert answer == "weiss nicht"
    assert not scoring.score(task, answer).is_correct


@pytest.mark.parametrize("klickfolge, erwartet", [
    ("1 2 3 4 5", "ERR_OMISSION"),       # ein Objekt ausgelassen
    ("1 2 3 4 5 5 6", "ERR_DOUBLE_COUNT"),  # eines doppelt geklickt
])
def test_klickfolge_erzeugt_die_fehlercodes_aus_paragraph_42(conn, klickfolge, erwartet):
    """§42 verlangt ausdruecklich ausgelassene Objekte und doppelte Klicks.

    Ohne eigene Abfrage der Klickfolge waeren ERR_OMISSION und ERR_DOUBLE_COUNT
    im Echtbetrieb unerreichbar - sie entstuenden nur in der Simulation.
    """
    task = attempts.load_task(conn, "ZP01-D1-I-A")  # 6 Objekte
    spec = renderer.render(task)
    answer, events = interactive.collect(task, spec, _reader(klickfolge, "6"))
    result = scoring.score(task, answer)
    codes = scoring.classify(task, answer, result,
                             scoring.ClassificationContext(events=events))
    assert erwartet in codes, f"erwartet {erwartet}, beobachtet {codes}"


def test_leere_klickfolge_bedeutet_alle_objekte_der_reihe_nach(conn):
    task = attempts.load_task(conn, "ZP01-D1-I-A")
    spec = renderer.render(task)
    answer, events = interactive.collect(task, spec, _reader("", "6"))
    clicks = [e for e in events if e["event_type"] == "CLICK"]
    assert len(clicks) == 6
    result = scoring.score(task, answer)
    codes = scoring.classify(task, answer, result,
                             scoring.ClassificationContext(events=events))
    assert "ERR_OMISSION" not in codes and "ERR_DOUBLE_COUNT" not in codes


def test_befehl_statt_antwort_wird_nicht_als_antwort_gewertet(conn):
    """Befehle tragen einen Doppelpunkt, weil 'nein' bei ZP05-D1-A eine Antwort
    ist. Ohne das Praefix waere jede Oberflaechenbedienung eine Beobachtung."""
    task = attempts.load_task(conn, "ZO06-D3-S-A")
    spec = renderer.render(task)
    with pytest.raises(interactive._Command) as exc:
        interactive.collect(task, spec, _reader(":warum"))
    assert exc.value.text == ":warum"


def test_abbruch_wird_nicht_zu_einer_leeren_antwort(conn):
    """Ctrl-D darf keinen Versuch mit leerer Antwort in die Rohdaten schreiben."""
    def read(_prompt):
        raise EOFError

    task = attempts.load_task(conn, "ZO06-D3-S-A")
    spec = renderer.render(task)
    with pytest.raises(interactive._Abort):
        interactive.collect(task, spec, read)


def test_durchlauf_schreibt_versuche_und_nur_pseudonyme_daten(conn):
    """§86: nur die pseudonyme ID. §60/§62: Zeit wird gespeichert."""
    antworten = _reader("12", "12", "12", "12", "12", "12")
    interactive.run(conn, "TEST-INT-01", grade=3, max_tasks=2,
                    read=antworten, write=lambda _s: None)

    row = conn.execute("SELECT * FROM students WHERE student_id = 'TEST-INT-01'").fetchone()
    assert set(dict(row)) <= {"student_id", "created_at", "grade_reference"}

    versuche = list(conn.execute(
        "SELECT time_seconds FROM task_attempts WHERE student_id = 'TEST-INT-01'"))
    assert len(versuche) == 2
    assert all(v["time_seconds"] is not None for v in versuche), \
        "§62 'Zeit speichern' und §60: time_seconds gehoert zu den Rohdaten"


def test_zeit_wird_gespeichert_aber_nicht_ausgewertet(conn):
    """§62 laesst sich nur als Paar erfuellen: speichern, nicht auswerten.

    Die zweite Haelfte haengt am Sperrschluessel, nicht an der Oberflaeche -
    deshalb wird hier geprueft, dass er steht. Faellt er, ist das Speichern der
    Zeit von einer Rohdatenpflicht zu einem Risiko geworden.
    """
    row = conn.execute(
        "SELECT value FROM system_config"
        " WHERE config_key = 'evidence.time_seconds_used_for_inference'").fetchone()
    assert row is not None, "§62 braucht einen ausdruecklichen Sperrschluessel"
    assert row["value"].lower() == "false", \
        "§62: 'langsam = schwache Kompetenz' ist nicht zulaessig"


def test_uebersteuern_wird_protokolliert(conn):
    """§89: das Protokoll muss die tatsaechlich gestellte Aufgabe nennen.

    next_task() schreibt seine Zeile, bevor die Lehrkraft uebersteuern kann.
    Ohne Korrektur nennt das Protokoll eine Aufgabe, die nie gestellt wurde -
    und §88 fragt ausdruecklich, warum das System diesen Pfad gewaehlt hat.
    """
    interactive.run(conn, "TEST-INT-OV", grade=3, max_tasks=1,
                    read=_reader(":weiter", "12", "12"), write=lambda _s: None)

    gestellt = {r["task_id"] for r in conn.execute(
        "SELECT task_id FROM task_attempts WHERE student_id = 'TEST-INT-OV'")}
    assert len(gestellt) == 1

    protokoll = list(conn.execute(
        "SELECT selected_task, rule_triggered FROM routing_decisions"
        " WHERE student_id = 'TEST-INT-OV' ORDER BY decision_id"))
    uebersteuert = [r for r in protokoll if r["rule_triggered"] == "TEACHER_OVERRIDE"]
    assert uebersteuert, "Uebersteuerung fehlt im Entscheidungsprotokoll (§89)"
    assert uebersteuert[0]["selected_task"] in gestellt, \
        "Das Protokoll nennt eine Aufgabe, die nie gestellt wurde"
