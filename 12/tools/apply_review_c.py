"""Zieht die Testerwartungen an die getrennte §69-Kette nach (Kritikbefund 6)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATCHES = [
    (ROOT / "tests/test_content.py",
     '''    assert rows["IMPLEMENTER_AUTHORED"] == 14, \\
        "13 nach Entscheidung D-11, plus ZO06-D3-S-C nach Kritikbefund 10"
    assert sum(rows.values()) == 95''',
     '''    assert rows["IMPLEMENTER_AUTHORED"] == 16, \\
        "13 nach D-11, ZO06-D3-S-C nach Kritikbefund 10, ZO06-D2-S-C/-S-D nach" \\
        " Kritikbefund 6"
    assert sum(rows.values()) == 97'''),

    (ROOT / "tests/test_content.py",
     '''    assert kette[("ZO06-D2-S-A", "WRONG")] == ("ZO06-D2-S-B", "REPLICATE_ERROR")
    assert kette[("ZO06-D2-S-B", "WRONG_REPLICATED")] == ("ZO06-D2-I-A", "CHANGE_REPRESENTATION")
    assert kette[("ZO06-D2-I-A", "CORRECT")][1] == "DISCRIMINATE_HYPOTHESIS"''',
     '''    # §30: erst replizieren.
    assert kette[("ZO06-D2-S-A", "WRONG")] == ("ZO06-D2-S-B", "REPLICATE_ERROR")
    # §31 Schritt 7 "Aufgabentyp": die Seed-Items fragen nach dem Wert einer
    # ZIFFER, das ikonische Gegenstueck nach dem Wert einer STELLE. Zuerst wird
    # nur die Frageform gewechselt, symbolisch (Kritikbefund 6, §116).
    assert kette[("ZO06-D2-S-B", "WRONG_REPLICATED")] == ("ZO06-D2-S-C", "CHECK_TASK_TYPE")
    # §31 Schritt 8 "Darstellung": jetzt wechselt nur noch die Darstellung.
    assert kette[("ZO06-D2-S-D", "WRONG_REPLICATED")] == ("ZO06-D2-I-A",
                                                          "CHANGE_REPRESENTATION")
    assert kette[("ZO06-D2-I-A", "CORRECT")][1] == "DISCRIMINATE_HYPOTHESIS"'''),

    (ROOT / "tests/test_engine.py",
     '''def test_hypothese_entsteht_bei_gleicher_stufe(conn, cfg, clock):
    """§88 und §100: zwei symbolische Fehler und zwei ikonische Erfolge auf
    derselben Stufe eroeffnen die Darstellungshypothese."""
    session = Session(conn, "HY-2", clock, cfg=cfg)
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=6))
    session.submit(Submission(task_id="ZO06-D2-S-B", answer=7))
    session.submit(Submission(task_id="ZO06-D2-I-A", answer=60))
    session.submit(Submission(task_id="ZO06-D2-I-B", answer=70))''',
     '''def test_hypothese_entsteht_bei_gleicher_stufe(conn, cfg, clock):
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
    session.submit(Submission(task_id="ZO06-D2-I-B", answer=70))'''),

    (ROOT / "tests/test_engine.py",
     '''def test_hypothese_braucht_gleiche_stufe_und_gleiches_antwortformat(conn, cfg, clock):
    """§116 und §32: ein Darstellungsvergleich ueber verschiedene Stufen hinweg
    laesst den Unterschied nicht der Darstellung zuordnen (D-24)."""
    session = Session(conn, "HY-1", clock, cfg=cfg)
    # Symbolisch falsch auf D2, ikonisch richtig auf D1 - verschiedene Stufen.
    session.submit(Submission(task_id="ZO06-D2-S-A", answer=6))
    session.submit(Submission(task_id="ZO06-D2-S-B", answer=7))
    session.submit(Submission(task_id="ZO06-D1-I-A", answer=47))
    session.submit(Submission(task_id="ZO06-D1-I-B", answer=63))
    offen = [h for h in hypotheses.open_hypotheses(conn, "HY-1")
             if h["hypothesis_type"] == "REPRESENTATION_HYPOTHESIS"]
    assert offen == []
    conn.rollback()''',
     '''def test_hypothese_braucht_gleiche_bedingungen(conn, cfg, clock):
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
    conn.rollback()'''),

    (ROOT / "tests/test_testfaelle.py",
     '''def test_c_repraesentation(alle, conn):
    """§100: D SYMBOL falsch -> Parallel SYMBOL falsch -> D IMAGE richtig ->
    Parallel IMAGE richtig -> REPRESENTATION_HYPOTHESIS."""
    trace = alle["C"]
    reihenfolge = [(s.representation, s.is_correct) for s in trace.steps[:4]]
    assert reihenfolge[0] == ("MATHEMATICAL_SYMBOL", False)
    assert reihenfolge[1] == ("MATHEMATICAL_SYMBOL", False)
    assert reihenfolge[2] == ("IMAGE", True)
    assert reihenfolge[3] == ("IMAGE", True)
    assert "REPRESENTATION_HYPOTHESIS" in trace.hypothesis_types()''',
     '''def test_c_repraesentation(alle, conn):
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
    assert "REPRESENTATION_HYPOTHESIS" in trace.hypothesis_types()'''),
]


def main():
    for path, old, new in PATCHES:
        text = path.read_text(encoding="utf-8")
        if old not in text:
            print(f"  NICHT GEFUNDEN in {path.name}: {old.splitlines()[0][:70]}")
            continue
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        print(f"  {path.name}: {old.splitlines()[0][:64]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
