"""Content-Tests: Sprint 2 (Kompetenzen und Beziehungen) und Sprint 3 (Aufgabenbank).

Diese Tests pruefen, dass der importierte Content den Aussagen der
Spezifikation entspricht - insbesondere den Stellen, an denen die
Spezifikation ein konkretes Item oder eine konkrete Route benennt.
"""

import json

import pytest

from mathkomp import validate

#: Quelle des Zusatzpakets Klasse 5-10 (content/klassen5bis10/).
#:
#: Die Tests dieser Datei pruefen Aussagen der Spezifikation. §42-57 nennen
#: ausschliesslich Items des Primarbereichs; das Zusatzpaket beruft sich auf
#: keine Fundstelle und darf deshalb keine Aussage dieser Datei verletzen,
#: aber auch keine erfuellen. Wo eine Pruefung "jedes Item" oder "jede
#: Relation" meint, meint sie den MVP-Bestand - abgegrenzt ueber diese
#: Quelle. Dass das Zusatzpaket die Abgrenzung einhaelt, pruefen die Tests
#: im Abschnitt "Zusatzpaket" am Ende der Datei.
ZUSATZ_QUELLE = "SRC_CURRICULUM_SEK1_UNDEFINED"

#: Items des MVP-Bestands: alle, deren Kompetenzknoten nicht aus dem
#: Zusatzpaket stammt. Ein eigenes Kennzeichen an der Aufgabe waere
#: redundant - die Zugehoerigkeit steht bereits am Knoten.
MVP_ITEMS = (
    "SELECT t.* FROM tasks t JOIN competencies c"
    f" ON c.competency_id = t.primary_competency WHERE c.source_id IS NOT '{ZUSATZ_QUELLE}'"
)

ZUSATZ_ITEMS = (
    "SELECT t.* FROM tasks t JOIN competencies c"
    f" ON c.competency_id = t.primary_competency WHERE c.source_id = '{ZUSATZ_QUELLE}'"
)


# ------------------------------------------------- Sprint 2: Kompetenzgraph


def test_alle_fuenf_leitideen_referenzierbar(conn):
    """§7: Die uebrigen Bereiche muessen bereits als Querverbindungen
    referenzierbar sein."""
    rows = conn.execute("SELECT DISTINCT leitidee FROM competencies").fetchall()
    vorhanden = {r["leitidee"] for r in rows}
    assert vorhanden == {"NUMBER_OPERATION", "MEASUREMENT", "PATTERN_FUNCTION",
                         "SPACE_SHAPE", "DATA_CHANCE"}


def test_fuenf_zaehlprinzipien_vorhanden(conn):
    """§9: die fuenf klassischen Zaehlprinzipien nach Gelman/Gallistel."""
    rows = conn.execute(
        "SELECT competency_id, source_id FROM competencies"
        " WHERE competency_id LIKE 'ZP0%' AND competency_id <> 'ZP00_COUNTING_PRINCIPLES'"
    ).fetchall()
    assert len(rows) == 5
    assert all(r["source_id"] == "SRC_GELMAN_GALLISTEL" for r in rows)


def test_kompetenzgraph_ist_kein_linearer_baum(conn):
    """§11: Eine Kompetenz kann mehrere Voraussetzungen und mehrere
    Nachfolger haben. Das muss der Graph auch zeigen."""
    mehrere_eingaenge = conn.execute(
        "SELECT target_competency, COUNT(*) n FROM relations"
        " WHERE relation_type IN ('HARD_PREREQUISITE', 'STRONG_PREREQUISITE')"
        " GROUP BY target_competency HAVING n > 1"
    ).fetchall()
    assert mehrere_eingaenge, "Kein Knoten mit mehr als einer Voraussetzung"

    mehrere_ausgaenge = conn.execute(
        "SELECT source_competency, COUNT(*) n FROM relations"
        " GROUP BY source_competency HAVING n > 1"
    ).fetchall()
    assert mehrere_ausgaenge, "Kein Knoten mit mehr als einer ausgehenden Relation"


def test_zo11_hat_alle_vier_grundoperationen_als_voraussetzung(conn):
    """§56: die ZO11-Items geben jeweils eine Grundoperation als bekannt vor."""
    rows = conn.execute(
        "SELECT source_competency FROM relations"
        " WHERE target_competency = 'ZO11_INVERSE_OPERATIONS'"
        " AND relation_type = 'STRONG_PREREQUISITE'"
    ).fetchall()
    assert {r["source_competency"] for r in rows} == {
        "ZO07_ADDITION", "ZO08_SUBTRACTION", "ZO09_MULTIPLICATION", "ZO10_DIVISION"}


def test_zahlenstrahl_kreuzt_drei_leitideen(conn):
    """§14: eine Zahlenstrahlaufgabe beruehrt Raum und Form, Groessen und
    Muster - modelliert als CROSS_DOMAIN_RELATION."""
    rows = conn.execute(
        "SELECT target_competency FROM relations"
        " WHERE source_competency = 'ZO04_NUMBER_RELATIONS'"
        " AND relation_type = 'CROSS_DOMAIN_RELATION'"
    ).fetchall()
    assert {r["target_competency"] for r in rows} == {
        "L4_SPACE_SHAPE", "L2_MEASUREMENT", "L3_PATTERN_FUNCTION"}


def test_keine_relation_behauptet_unbelegte_evidenz(conn):
    """§114: ohne belastbare Quelle nur evidence_status C oder D."""
    rows = conn.execute(
        "SELECT relation_id, evidence_status FROM relations"
        " WHERE evidence_status IN ('A', 'B')"
    ).fetchall()
    assert rows == [], f"A/B ohne empirische Quelle: {[r['relation_id'] for r in rows]}"


def test_jede_relation_nennt_ihre_fundstelle(conn):
    rows = conn.execute(
        "SELECT relation_id FROM relations"
        " WHERE source_id IS NOT ? AND (spec_section IS NULL OR notes IS NULL)",
        (ZUSATZ_QUELLE,),
    ).fetchall()
    assert rows == [], f"Relation ohne Fundstelle oder Begruendung: {rows}"


# ---------------------------------------------------- Sprint 3: Aufgabenbank


def test_itemzahl_und_herkunft(conn):
    """§42-57 liefern die Seed-Items; Entscheidung D-11 ergaenzt 13 weitere zur
    Schliessung von F-21 und F-22. Die Herkunft muss unterscheidbar bleiben."""
    rows = {}
    for r in conn.execute(MVP_ITEMS):
        rows[r["source_type"]] = rows.get(r["source_type"], 0) + 1
    assert rows["SPEC_SEED_MVP"] == 81, "§42-57 plus §52, minus 2 zusammengelegte (D-03)"
    assert rows["IMPLEMENTER_AUTHORED"] == 16, \
        "13 nach D-11, ZO06-D3-S-C nach Kritikbefund 10, ZO06-D2-S-C/-S-D nach" \
        " Kritikbefund 6"
    assert sum(rows.values()) == 97


def test_alle_items_sind_unkalibriert(conn):
    """§6: die im MVP erstellten Aufgaben sind keine validierten Testitems."""
    n = conn.execute(
        "SELECT COUNT(*) n FROM tasks WHERE calibration_status <> 'UNCALIBRATED_MVP_ITEM'"
    ).fetchone()["n"]
    assert n == 0


def test_beispielitem_aus_paragraph_24_vollstaendig(conn):
    """§24 gibt fuer 49+36 alle Metadaten an. Sie muessen exakt so vorliegen."""
    t = conn.execute(
        "SELECT * FROM tasks WHERE task_id = 'ZO07-D3-S-E'"
    ).fetchone()
    assert t["primary_competency"] == "ZO07_ADDITION"
    assert t["internal_difficulty"] == "D3"
    assert t["calibration_status"] == "UNCALIBRATED_MVP_ITEM"
    assert t["representation_mode"] == "MATHEMATICAL_SYMBOL"
    assert t["interaction_mode"] == "ENTER"
    assert json.loads(t["correct_answer"])["value"] == 85

    features = {
        (r["feature_kind"], r["feature_value"])
        for r in conn.execute(
            "SELECT feature_kind, feature_value FROM task_features WHERE task_id = ?",
            (t["task_id"],))
    }
    assert ("NUMERIC_FEATURE", "NEAR_ROUND_NUMBER") in features
    assert ("NUMERIC_FEATURE", "CROSSES_TEN") in features
    assert ("STRUCTURAL_FEATURE", "TWO_DIGIT_ADDITION") in features
    assert ("STRATEGY_AFFORDANCE", "COMPENSATION") in features
    assert ("STRATEGY_AFFORDANCE", "DECOMPOSITION") in features
    assert ("SURFACE_FEATURE", "NO_CONTEXT") in features
    assert ("SURFACE_FEATURE", "SYMBOLIC_ONLY") in features


def test_contrast_family_paragraph_52_hat_vier_mitglieder(conn):
    """§52 nennt vier Items: 49+36, 48+37, 37+28, 46+27."""
    rows = conn.execute(
        "SELECT task_id FROM tasks WHERE task_family_id = 'ZO07-CONTRAST-01'"
        " ORDER BY task_id"
    ).fetchall()
    assert [r["task_id"] for r in rows] == [
        "ZO07-D3-S-C", "ZO07-D3-S-D", "ZO07-D3-S-E", "ZO07-D3-S-F"]


def test_contrast_family_trennt_nach_compensation(conn):
    """§71 nennt fuer die erfolgreiche Seite "NEAR_ROUND_NUMBER,
    COMPENSATION_AVAILABLE". Getrennt werden die vier Items der Contrast Family
    nur durch das zweite Merkmal.

    Nach der operandensymmetrischen Regel (Kritikbefund 3, D-19) traegt auch
    37+28 einen runden Anker - 28 ist 2 von 30 entfernt. §71 ordnet das Item
    trotzdem der erfolglosen Seite zu. Die Abweichung ist als F-25 gemeldet und
    nicht durch Regeldesign beseitigt; das tragfaehige Kontrastmerkmal ist
    COMPENSATION, weil der Ausgleich dort den Ausgangswert nach unten anpassen
    muesste.
    """
    def mit(feature):
        return {r["task_id"] for r in conn.execute(
            "SELECT t.task_id FROM tasks t JOIN task_features f ON f.task_id = t.task_id"
            " WHERE t.task_family_id = 'ZO07-CONTRAST-01' AND f.feature_value = ?",
            (feature,))}

    assert mit("COMPENSATION") == {"ZO07-D3-S-E", "ZO07-D3-S-F"}
    # F-25: NEAR_ROUND_NUMBER trennt die Familie NICHT mehr - das ist der
    # Befund, nicht ein Fehler.
    assert mit("NEAR_ROUND_NUMBER") != {"ZO07-D3-S-E", "ZO07-D3-S-F"}


def test_zahlenabhaengigkeit_paragraph_19(conn):
    """§19: 49+36 und 37+28 sind nicht austauschbar. Der Content muss den
    Unterschied auch abbilden - sonst waere die Aussage nicht pruefbar."""
    def merkmale(task_id):
        return {
            r["feature_value"] for r in conn.execute(
                "SELECT feature_value FROM task_features"
                " WHERE task_id = ? AND feature_kind IN"
                " ('NUMERIC_FEATURE', 'STRATEGY_AFFORDANCE')", (task_id,))
        }
    assert merkmale("ZO07-D3-S-E") != merkmale("ZO07-D3-S-C")


def test_darstellung_und_bedienform_sind_unabhaengig(conn):
    """§17: Darstellung und Bedienform sind zwei unterschiedliche Variablen.
    Im Content muss mindestens eine Darstellung mit mehreren Bedienformen
    und eine Bedienform mit mehreren Darstellungen vorkommen."""
    rows = conn.execute(
        "SELECT representation_mode r, COUNT(DISTINCT interaction_mode) n FROM tasks"
        " GROUP BY representation_mode HAVING n > 1"
    ).fetchall()
    assert rows, "Keine Darstellung mit mehreren Bedienformen"
    rows = conn.execute(
        "SELECT interaction_mode i, COUNT(DISTINCT representation_mode) n FROM tasks"
        " GROUP BY interaction_mode HAVING n > 1"
    ).fetchall()
    assert rows, "Keine Bedienform mit mehreren Darstellungen"


def test_ceiling_item_paragraph_54(conn):
    """§54: 'D5 dient hier nur zur Ceiling-Suche.'"""
    t = conn.execute(
        "SELECT internal_difficulty, task_purpose FROM tasks WHERE task_id = 'ZO09-D5-S-A'"
    ).fetchone()
    assert t["internal_difficulty"] == "D5"
    assert t["task_purpose"] == "CEILING"


def test_verteilen_und_aufteilen_sind_unterscheidbar(conn):
    """§55: 'Diese beiden Aufgaben unterscheiden: VERTEILEN und AUFTEILEN.'"""
    a = {r["feature_value"] for r in conn.execute(
        "SELECT feature_value FROM task_features"
        " WHERE task_id = 'ZO10-GV-D1-ACTION-A' AND feature_kind = 'STRUCTURAL_FEATURE'")}
    b = {r["feature_value"] for r in conn.execute(
        "SELECT feature_value FROM task_features"
        " WHERE task_id = 'ZO10-GV-D1-ACTION-B' AND feature_kind = 'STRUCTURAL_FEATURE'")}
    assert "PARTITIVE_DIVISION" in a and "QUOTATIVE_DIVISION" not in a
    assert "QUOTATIVE_DIVISION" in b and "PARTITIVE_DIVISION" not in b


def test_zahlenstrahlitem_traegt_die_angaben_aus_paragraph_14(conn):
    t = conn.execute(
        "SELECT primary_competency, process_competencies, secondary_leitideen"
        " FROM tasks WHERE task_id = 'ZO04-D3-I-A'"
    ).fetchone()
    assert t["primary_competency"] == "ZO04_NUMBER_RELATIONS"
    assert json.loads(t["process_competencies"]) == ["DARSTELLEN"]
    assert "SPACE_SHAPE" in json.loads(t["secondary_leitideen"])
    demands = {r["feature_value"] for r in conn.execute(
        "SELECT feature_value FROM task_features"
        " WHERE task_id = 'ZO04-D3-I-A' AND feature_kind = 'ADDITIONAL_DEMAND'")}
    assert demands == {"SPATIAL_PROCESSING"}


def test_jedes_item_nennt_seine_fundstelle(conn):
    rows = [r["task_id"] for r in conn.execute(MVP_ITEMS) if r["spec_section"] is None]
    assert rows == []


# ------------------------------------------------------------- Sprint 3: Routing


def test_route_r001_woertlich_aus_paragraph_83(conn):
    r = conn.execute("SELECT * FROM task_routes WHERE route_id = 'R001'").fetchone()
    assert r["source_task"] == "ZO09-REL-D3-S-A"
    assert r["condition"] == "WRONG"
    assert r["target_task"] == "ZO09-REL-D3-S-B"
    assert r["reason"] == "REPLICATE_ERROR"
    assert r["priority"] == 100
    assert r["enabled"] == 1


def test_stellenwert_routing_paragraph_69_vollstaendig(conn):
    """§69 beschreibt vier Uebergaenge: Parallelitem, Darstellungswechsel,
    Voraussetzungspruefung und zweites I/S-Paar."""
    kette = {
        (r["source_task"], r["condition"]): (r["target_task"] or r["target_competency"], r["reason"])
        for r in conn.execute("SELECT * FROM task_routes WHERE spec_section LIKE '%69%'")
    }
    # §30: erst replizieren.
    assert kette[("ZO06-D2-S-A", "WRONG")] == ("ZO06-D2-S-B", "REPLICATE_ERROR")
    # §31 Schritt 7 "Aufgabentyp": die Seed-Items fragen nach dem Wert einer
    # ZIFFER, das ikonische Gegenstueck nach dem Wert einer STELLE. Zuerst wird
    # nur die Frageform gewechselt, symbolisch (Kritikbefund 6, §116).
    assert kette[("ZO06-D2-S-B", "WRONG_REPLICATED")] == ("ZO06-D2-S-C", "CHECK_TASK_TYPE")
    # §31 Schritt 8 "Darstellung": jetzt wechselt nur noch die Darstellung.
    assert kette[("ZO06-D2-S-D", "WRONG_REPLICATED")] == ("ZO06-D2-I-A",
                                                          "CHANGE_REPRESENTATION")
    assert kette[("ZO06-D2-I-A", "CORRECT")][1] == "DISCRIMINATE_HYPOTHESIS"
    # §31 Schritt 3 und §99: Rueckwaertsnavigation auf die Voraussetzung. Das
    # Buendelungsitem existiert erst durch Entscheidung D-11 (vorher F-22).
    prerequisite_routes = {
        (r["source_task"], r["target_task"]) for r in conn.execute(
            "SELECT source_task, target_task FROM task_routes"
            " WHERE reason = 'CHECK_PREREQUISITE'")
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
        " WHERE r.reason = 'CHANGE_REPRESENTATION'"
    ):
        assert row["ad"] == row["bd"], f"{row['route_id']} wechselt die Stufe"
        assert row["ars"] == row["brs"], f"{row['route_id']} wechselt das Antwortformat"


def test_multiplikationsrouting_paragraph_70(conn):
    kette = {
        (r["source_task"], r["condition"]): (r["target_task"] or r["target_competency"], r["reason"])
        for r in conn.execute("SELECT * FROM task_routes WHERE spec_section LIKE '%70%'")
    }
    assert kette[("ZO09-D2-S-A", "WRONG")] == ("ZO09-D2-S-B", "REPLICATE_ERROR")
    assert kette[("ZO09-D2-S-B", "WRONG_REPLICATED")] == ("ZO09-D2-I-A", "CHANGE_REPRESENTATION")
    assert kette[("ZO09-D2-I-A", "WRONG")] == ("ZO09-GV-D1-I-A", "CHECK_PREREQUISITE")
    assert kette[("ZO09-GV-D1-I-A", "CORRECT")] == ("ZO12-D2-S-A", "CHECK_RELATED_COMPETENCY")
    assert kette[("ZO09-GV-D1-I-A", "WRONG")] == ("ZO09_MULTIPLICATION", "SUPPORT_ROUTE")


def test_routing_liegt_als_daten_vor_nicht_im_code():
    """§84: 'Nicht: if(task === "ZO09...") { nextTask = ... }'"""
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src" / "mathkomp"
    import re
    for pyfile in src.glob("*.py"):
        text = pyfile.read_text(encoding="utf-8")
        for zeile_nr, zeile in enumerate(text.splitlines(), 1):
            if zeile.strip().startswith("#") or zeile.strip().startswith('"'):
                continue
            # Eine Aufgaben-ID in einer Bedingung waere hardcodiertes Routing.
            if re.search(r"(if|elif|while).*['\"](ZO|ZP)\d", zeile):
                raise AssertionError(
                    f"§84 verletzt: hardcodierte Aufgaben-ID in {pyfile.name}:{zeile_nr}")


def test_config_enthaelt_keine_hardcodierten_schwellen():
    """§41: Mastery-Schwellen sind konfigurierbar, §39: Zeitgrenzen nicht
    hardcoden. Es darf keine Zahl aus §41 als Literal im Code stehen."""
    from pathlib import Path
    import re
    src = Path(__file__).resolve().parents[1] / "src" / "mathkomp"
    verdaechtig = re.compile(
        r"(success_confirmation_required|failure_replication_required"
        r"|max_same_level_items|start_difficulty)\s*=\s*[\d\"']")
    for pyfile in src.glob("*.py"):
        for zeile_nr, zeile in enumerate(pyfile.read_text(encoding="utf-8").splitlines(), 1):
            assert not verdaechtig.search(zeile), f"{pyfile.name}:{zeile_nr}: {zeile.strip()}"


# ----------------------------------------------------------- Pruefregeln


def test_keine_regelverstoesse(conn):
    findings = validate.run_all(conn)
    errs = validate.errors(findings)
    assert errs == [], "\n".join(str(f) for f in errs)


def test_keine_unauslieferbaren_items_mehr(conn):
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
        assert erledigt not in regeln, erledigt


# ---------------------------------------------------- Zusatzpaket Klasse 5-10


def test_zusatzpaket_beruft_sich_auf_keine_fundstelle(conn):
    """§1: eine Angabe, die nicht in der Spezifikation steht, darf sich nicht
    auf sie berufen. §42-57 nennen nur Items des Primarbereichs - jedes Item
    des Zusatzpakets muss spec_section NULL tragen und als vom Implementierer
    erstellt gekennzeichnet sein."""
    rows = conn.execute(ZUSATZ_ITEMS).fetchall()
    assert len(rows) == 138, "23 Knoten mit je sechs Items"
    falsch = [r["task_id"] for r in rows if r["spec_section"] is not None]
    assert falsch == [], f"Item des Zusatzpakets behauptet eine Fundstelle: {falsch}"
    falsch = [r["task_id"] for r in rows if r["source_type"] != "IMPLEMENTER_AUTHORED"]
    assert falsch == [], f"Item des Zusatzpakets ohne IMPLEMENTER_AUTHORED: {falsch}"
    falsch = [r["task_id"] for r in rows
              if r["calibration_status"] != "UNCALIBRATED_MVP_ITEM"]
    assert falsch == [], f"§6 verletzt - Item behauptet Kalibrierung: {falsch}"


def test_zusatzknoten_sind_nicht_als_mvp_markiert(conn):
    """§10 zaehlt die MVP-Knoten auf. Die Knoten der Klassen 5 bis 10 stehen
    dort nicht; is_mvp waere fuer sie eine falsche Behauptung (§1)."""
    rows = conn.execute(
        "SELECT competency_id, is_mvp, grade_reference_min, grade_reference_max,"
        " evidence_status FROM competencies WHERE source_id = ?", (ZUSATZ_QUELLE,)
    ).fetchall()
    assert len(rows) == 23
    assert all(r["is_mvp"] == 0 for r in rows)
    assert all(r["evidence_status"] == "D" for r in rows), \
        "§114: ohne ausgewerteten Bildungsplan hoechstens D"
    for r in rows:
        assert 5 <= r["grade_reference_min"] <= r["grade_reference_max"] <= 10, \
            r["competency_id"]


def test_zusatzpaket_parallelitems_sind_symmetrisch(conn):
    """§25: ein Parallelitem variiert nur die Zahlen. Stufe, Darstellung,
    Bedienform, Antwortformat und Frageform muessen gleich bleiben, sonst ist
    ein wiederholter Fehler nach §30 kein repliziertes Muster, sondern ein
    Fehler unter anderen Bedingungen."""
    paare = conn.execute(
        "SELECT a.task_id a_id, b.task_id b_id, a.internal_difficulty = b.internal_difficulty d,"
        " a.representation_mode = b.representation_mode r,"
        " a.interaction_mode = b.interaction_mode i,"
        " a.scoring_rule = b.scoring_rule s, a.question_form = b.question_form q"
        " FROM tasks a JOIN tasks b ON b.task_id = a.parallel_item_id"
        " JOIN competencies c ON c.competency_id = a.primary_competency"
        " WHERE c.source_id = ?", (ZUSATZ_QUELLE,)
    ).fetchall()
    assert len(paare) == 46, "23 Paare, beidseitig verknuepft"
    for p in paare:
        assert all((p["d"], p["r"], p["i"], p["s"], p["q"])), f"{p['a_id']} / {p['b_id']}"


def test_zusatzpaket_darstellungsfamilien_variieren_nur_die_darstellung(conn):
    """§116: ein diagnostischer Vergleich aendert genau eine Variable. In einer
    REPRESENTATION_VARIATION-Familie darf das nur die Darstellung sein - sonst
    ist ein Unterschied nach §32 nicht der Darstellung zuzuordnen."""
    familien = conn.execute(
        "SELECT f.task_family_id FROM task_families f"
        " JOIN competencies c ON c.competency_id = f.primary_competency"
        " WHERE c.source_id = ? AND f.family_type = 'REPRESENTATION_VARIATION'",
        (ZUSATZ_QUELLE,),
    ).fetchall()
    assert len(familien) == 23
    for f in familien:
        items = conn.execute(
            "SELECT * FROM tasks WHERE task_family_id = ?", (f["task_family_id"],)
        ).fetchall()
        assert len(items) == 2, f["task_family_id"]
        a, b = items
        for spalte in ("internal_difficulty", "interaction_mode", "scoring_rule",
                       "question_form", "correct_answer"):
            assert a[spalte] == b[spalte], f"{f['task_family_id']}: {spalte} variiert mit"
        assert a["representation_mode"] != b["representation_mode"], \
            f"{f['task_family_id']}: die Darstellung variiert gar nicht"


def test_zusatzpaket_routen_sind_abschaltbar_und_begruendet(conn):
    """§84: kein hardcodiertes Routing. §89: jede Entscheidung muss sich
    nachlesen lassen - eine Route ohne Begruendung waere nicht pruefbar."""
    rows = conn.execute(
        "SELECT r.route_id, r.notes, r.enabled FROM task_routes r"
        " JOIN tasks t ON t.task_id = r.source_task"
        " JOIN competencies c ON c.competency_id = t.primary_competency"
        " WHERE c.source_id = ?", (ZUSATZ_QUELLE,)
    ).fetchall()
    assert len(rows) == 92, "23 Knoten mit je vier Uebergaengen"
    assert all(r["notes"] for r in rows)
    assert all(r["enabled"] == 1 for r in rows)
