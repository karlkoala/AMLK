"""Einmaliges Werkzeug: passt die Sprint-1-3-Tests an den Content nach dem
Merge der autorisierten Fragmente an (IDs, Routen, Itemzahl).

Wird nach dem Lauf nicht mehr benoetigt und dient nur der Nachvollziehbarkeit,
welche Testerwartung sich durch welche Entscheidung geaendert hat.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

Q = chr(39) * 3  # dreifaches einfaches Anfuehrungszeichen

CONTENT_PATCHES = [
    # Itemzahl und Herkunft (D-03, D-11)
    ('''def test_anzahl_seed_items(conn):
    """§42-57 plus die zwei ID-losen Items der Contrast Family aus §52."""
    n = conn.execute("SELECT COUNT(*) n FROM tasks").fetchone()["n"]
    assert n == 83''',
     '''def test_itemzahl_und_herkunft(conn):
    """§42-57 liefern die Seed-Items; Entscheidung D-11 ergaenzt 13 weitere zur
    Schliessung von F-21 und F-22. Die Herkunft muss unterscheidbar bleiben."""
    rows = {r["source_type"]: r["n"] for r in conn.execute(
        "SELECT source_type, COUNT(*) n FROM tasks GROUP BY source_type")}
    assert rows["SPEC_SEED_MVP"] == 81, "§42-57 plus §52, minus 2 zusammengelegte (D-03)"
    assert rows["IMPLEMENTER_AUTHORED"] == 13, "Entscheidung D-11"
    assert sum(rows.values()) == 94'''),

    # Umbenennung nach D-01/D-02
    ("""        "SELECT * FROM tasks WHERE task_id = 'ZO07-CONTRAST-01-A'\"""",
     """        "SELECT * FROM tasks WHERE task_id = 'ZO07-D3-S-E'\""""),
    ('''    assert [r["task_id"] for r in rows] == [
        "ZO07-CONTRAST-01-A", "ZO07-CONTRAST-01-B", "ZO07-D3-S-C", "ZO07-D3-S-D"]''',
     '''    assert [r["task_id"] for r in rows] == [
        "ZO07-D3-S-C", "ZO07-D3-S-D", "ZO07-D3-S-E", "ZO07-D3-S-F"]'''),
    ('''    assert mit == {"ZO07-CONTRAST-01-A", "ZO07-CONTRAST-01-B"}''',
     '''    assert mit == {"ZO07-D3-S-E", "ZO07-D3-S-F"}'''),
    ('''    assert merkmale("ZO07-CONTRAST-01-A") != merkmale("ZO07-D3-S-C")''',
     '''    assert merkmale("ZO07-D3-S-E") != merkmale("ZO07-D3-S-C")'''),
]

STELLENWERT_ALT = '''    assert kette[("ZO06-D2-S-A", "WRONG")] == ("ZO06-D2-S-B", "REPLICATE_ERROR")
    assert kette[("ZO06-D2-S-B", "WRONG_REPLICATED")] == ("ZO06-D1-I-A", "CHANGE_REPRESENTATION")
    assert kette[("ZO06-D1-I-A", "WRONG")] == ("ZO06_1_BUNDLING", "CHECK_PREREQUISITE")
    assert kette[("ZO06-D1-I-A", "CORRECT")][1] == "DISCRIMINATE_HYPOTHESIS"'''

STELLENWERT_NEU = '''    assert kette[("ZO06-D2-S-A", "WRONG")] == ("ZO06-D2-S-B", "REPLICATE_ERROR")
    assert kette[("ZO06-D2-S-B", "WRONG_REPLICATED")] == ("ZO06-D2-I-A", "CHANGE_REPRESENTATION")
    assert kette[("ZO06-D2-I-A", "CORRECT")][1] == "DISCRIMINATE_HYPOTHESIS"
    # §31 Schritt 3 und §99: Rueckwaertsnavigation auf die Voraussetzung. Das
    # Buendelungsitem existiert erst durch Entscheidung D-11 (vorher F-22).
    prerequisite_routes = {
        (r["source_task"], r["target_task"]) for r in conn.execute(
            "SELECT source_task, target_task FROM task_routes"
            " WHERE reason = %sCHECK_PREREQUISITE%s")
    }
    assert ("ZO06-D2-I-A", "ZO06-1-D1-ACTION-A") in prerequisite_routes


def test_darstellungswechsel_haelt_stufe_und_format_konstant(conn):
    """§116 Grundsatz der minimalen Veraenderung, angewandt auf Routen.

    Eine Route mit reason CHANGE_REPRESENTATION darf nur die Darstellung
    wechseln. Wechselt sie zugleich Stufe oder Antwortformat, ist ein
    Unterschied nicht mehr der Darstellung zuzuordnen (§32) - genau das war der
    Befund F-21.
    """
    for row in conn.execute(
        "SELECT r.route_id, a.internal_difficulty AS ad, b.internal_difficulty AS bd,"
        " a.scoring_rule AS ars, b.scoring_rule AS brs"
        " FROM task_routes r JOIN tasks a ON a.task_id = r.source_task"
        " JOIN tasks b ON b.task_id = r.target_task"
        " WHERE r.reason = %sCHANGE_REPRESENTATION%s"
    ):
        assert row["ad"] == row["bd"], f"{row['route_id']} wechselt die Stufe"
        assert row["ars"] == row["brs"], f"{row['route_id']} wechselt das Antwortformat"''' % (
    "'", "'", "'", "'")

MULTIPLIKATION_ALT = '''    assert kette[("ZO09-D2-S-A", "WRONG_REPLICATED")][1] == "CHANGE_REPRESENTATION"
    assert kette[("ZO09-REL-D3-I-A", "WRONG")] == ("ZO09-GV-D1-I-A", "CHECK_PREREQUISITE")'''

MULTIPLIKATION_NEU = '''    assert kette[("ZO09-D2-S-A", "WRONG")] == ("ZO09-D2-S-B", "REPLICATE_ERROR")
    assert kette[("ZO09-D2-S-B", "WRONG_REPLICATED")] == ("ZO09-D2-I-A", "CHANGE_REPRESENTATION")
    assert kette[("ZO09-D2-I-A", "WRONG")] == ("ZO09-GV-D1-I-A", "CHECK_PREREQUISITE")'''

HINWEISE_ALT = '''def test_hinweise_werden_gemeldet(conn):
    """Die fachlichen Luecken muessen sichtbar sein, nicht stillschweigend
    ueberdeckt (§1: Rueckfrage stellen)."""
    findings = validate.run_all(conn)
    notices = [f for f in findings if f.severity == validate.NOTICE]
    regeln = {f.rule for f in notices}
    assert "options_undefined" in regeln
    assert "config_undefined" in regeln
    assert "representation_route_confound" in regeln'''

HINWEISE_NEU = '''def test_keine_unauslieferbaren_items_mehr(conn):
    """F-17 und F-18 sind mit den Entscheidungen D-09 und D-10 geschlossen:
    kein Item traegt mehr UNDEFINED in options oder correct_answer."""
    regeln = {f.rule for f in validate.run_all(conn)}
    assert "options_undefined" not in regeln
    assert "answer_undefined" not in regeln


def test_keine_undefinierten_konfigurationswerte_mehr(conn):
    """Alle Schluessel sind unter D-05 bis D-07 belegt; require() bricht nicht
    mehr ab. §1 bleibt gewahrt: jede Festlegung ist als CONFIGURABLE markiert
    und in ENTSCHEIDUNGEN.md begruendet."""
    from mathkomp.config import Config
    assert Config(conn).undefined_keys() == []


def test_verbleibende_hinweise_sind_dokumentiert(conn):
    """§1: eine fachliche Luecke wird gemeldet, nicht ueberdeckt. Was noch offen
    ist, muss als NOTICE erscheinen - und was erledigt ist, nicht mehr."""
    regeln = {f.rule for f in validate.run_all(conn) if f.severity == validate.NOTICE}
    # F-16 bleibt offen: die Items sind nach §42-57 der Gruppenebene zugeordnet,
    # nicht den Unterknoten aus §10.
    assert "competency_without_items" in regeln
    for erledigt in ("options_undefined", "answer_undefined", "config_undefined",
                     "competency_description", "successor_missing"):
        assert erledigt not in regeln, erledigt'''


def patch(path: Path, pairs) -> int:
    text = path.read_text(encoding="utf-8")
    applied = 0
    for old, new in pairs:
        if old not in text:
            print(f"  NICHT GEFUNDEN in {path.name}: {old.splitlines()[0][:70]}")
            continue
        text = text.replace(old, new, 1)
        applied += 1
    path.write_text(text, encoding="utf-8")
    return applied


def main() -> int:
    content = ROOT / "tests" / "test_content.py"
    pairs = list(CONTENT_PATCHES)
    pairs.append((STELLENWERT_ALT, STELLENWERT_NEU))
    pairs.append((MULTIPLIKATION_ALT, MULTIPLIKATION_NEU))
    pairs.append((HINWEISE_ALT, HINWEISE_NEU))
    pairs.append(('WHERE spec_section = \'§70\'', 'WHERE spec_section LIKE \'%70%\''))
    print(f"tests/test_content.py: {patch(content, pairs)} Stellen angepasst")

    schema = ROOT / "tests" / "test_schema.py"
    print(f"tests/test_schema.py: {patch(schema, [(chr(39) + 'ZO07-CONTRAST-01-A' + chr(39), chr(39) + 'ZO07-D3-S-E' + chr(39))])} Stellen angepasst")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
