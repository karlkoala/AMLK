"""Schema-Tests: Sprint 1.

Prueft, dass das Schema die Vorgaben der Spezifikation strukturell
erzwingt - nicht nur, dass der Import durchlaeuft.
"""

import sqlite3

import pytest

from mathkomp import db


def test_alle_in_paragraph_78_verlangten_tabellen_existieren(conn):
    """§78 nennt 13 Tabellen als Minimum."""
    vorhanden = db.table_names(conn)
    fehlend = set(db.REQUIRED_TABLES_SPEC_78) - vorhanden
    assert not fehlend, f"§78 verlangt zusaetzlich: {sorted(fehlend)}"


def test_beobachtung_evidenz_hypothese_sind_getrennte_tabellen(conn):
    """§66: Diese Ebenen duerfen technisch nicht vermischt werden."""
    vorhanden = db.table_names(conn)
    assert "attempt_error_codes" in vorhanden, "Ebene Beobachtung"
    assert "evidence_events" in vorhanden, "Ebene Evidenz"
    assert "student_hypotheses" in vorhanden, "Ebene Hypothese"

    # Keine der drei Tabellen darf Spalten der anderen Ebene fuehren.
    def spalten(table):
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}

    assert "hypothesis_type" not in spalten("evidence_events")
    assert "error_code" not in spalten("evidence_events")
    assert "error_code" not in spalten("student_hypotheses")


def test_keine_hardcodierten_wertelisten_im_schema():
    """§108: Vokabulare muessen datengetrieben sein. Das Schema darf keine
    CHECK (spalte IN ('A','B',...))-Listen mit fachlichen Werten enthalten."""
    import re
    # Kommentarzeilen entfernen - dort steht die Begruendung, warum es keine
    # solchen Listen gibt, und die soll den Test nicht ausloesen.
    sql = "\n".join(
        zeile for zeile in db.SCHEMA_PATH.read_text(encoding="utf-8").splitlines()
        if not zeile.lstrip().startswith("--")
    )
    # Zulaessig sind nur die technischen Booleans 0/1.
    treffer = re.findall(r"CHECK\s*\([^)]*\bIN\s*\(([^)]*)\)", sql)
    for inhalt in treffer:
        werte = {w.strip() for w in inhalt.split(",")}
        assert werte <= {"0", "1"}, f"Hardcodierte Werteliste im Schema: {werte}"


def test_student_tabelle_enthaelt_keine_personenbezogenen_spalten(conn):
    """§86: nur pseudonyme UUID, keine unnoetigen personenbezogenen Daten.
    §87: keine medizinischen Diagnosen."""
    spalten = {r["name"] for r in conn.execute("PRAGMA table_info(students)")}
    verboten = {"name", "vorname", "nachname", "birthdate", "geburtsdatum",
                "email", "school", "schule", "diagnosis", "diagnose", "adhd", "adhs"}
    assert not (spalten & verboten), f"Verbotene Spalten: {spalten & verboten}"


def test_kein_adhs_bezug_im_gesamten_schema():
    """§87: ADHS-Erkennung ist ausdruecklich nicht Bestandteil des MVP."""
    sql = db.SCHEMA_PATH.read_text(encoding="utf-8").lower()
    for begriff in ("adhd", "adhs", "diagnosis", "diagnose"):
        # 'keine medizinischen Diagnosen speichern' darf als Kommentar stehen,
        # aber kein Bezeichner darf so heissen.
        for zeile in sql.splitlines():
            if begriff in zeile and not zeile.strip().startswith("--"):
                pytest.fail(f"'{begriff}' ausserhalb eines Kommentars: {zeile.strip()}")


def test_fehlercode_kann_nicht_zur_diagnose_werden(conn):
    """§59: Fehlercodes beschreiben Beobachtungen. Das CHECK verhindert,
    dass ein Code nachtraeglich umgewidmet wird."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO error_codes (error_code, label_de, is_observation_only)"
            " VALUES ('ERR_TEST_DIAG', 'Test', 0)"
        )
    conn.rollback()


def test_relation_ohne_evidenzstatus_wird_abgelehnt(empty_conn):
    """§114: Keine Relation ohne relation_type und evidence_status."""
    empty_conn.execute(
        "INSERT INTO sources (source_id, author_or_org, title, source_type)"
        " VALUES ('S1', 'X', 'Y', 'THEORETICAL')"
    )
    for cid in ("C1", "C2"):
        empty_conn.execute(
            "INSERT INTO competencies (competency_id, name, domain, leitidee, evidence_status)"
            " VALUES (?, ?, 'MATHEMATICS', 'NUMBER_OPERATION', 'C')", (cid, cid)
        )
    with pytest.raises(sqlite3.IntegrityError):
        empty_conn.execute(
            "INSERT INTO relations (relation_id, source_competency, target_competency,"
            " relation_type, evidence_status) VALUES ('R', 'C1', 'C2', 'SUCCESSOR', NULL)"
        )


def test_unbekannter_vokabularwert_wird_abgelehnt(empty_conn):
    """§108: Werte muessen in vocabulary_terms stehen. Ein Tippfehler oder
    ein neuer Wert ohne Vokabulareintrag darf nicht durchgehen."""
    with pytest.raises(sqlite3.IntegrityError):
        empty_conn.execute(
            "INSERT INTO competencies (competency_id, name, domain, leitidee, evidence_status)"
            " VALUES ('C9', 'X', 'MATHEMATICS', 'NUMBER_OPERATION', 'Z')"
        )


def test_relation_auf_sich_selbst_wird_abgelehnt(empty_conn):
    for cid in ("C1", "C2"):
        empty_conn.execute(
            "INSERT INTO competencies (competency_id, name, domain, leitidee, evidence_status)"
            " VALUES (?, ?, 'MATHEMATICS', 'NUMBER_OPERATION', 'C')", (cid, cid)
        )
    with pytest.raises(sqlite3.IntegrityError):
        empty_conn.execute(
            "INSERT INTO relations (relation_id, source_competency, target_competency,"
            " relation_type, evidence_status) VALUES ('R', 'C1', 'C1', 'SUCCESSOR', 'C')"
        )


def test_route_ohne_ziel_wird_abgelehnt(conn):
    """§83: eine Route braucht ein Ziel - Aufgabe oder Kompetenzknoten."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO task_routes (route_id, source_task, condition, reason, priority)"
            " VALUES ('RX', 'ZO07-D2-S-A', 'WRONG', 'REPLICATE_ERROR', 10)"
        )
    conn.rollback()


def test_keine_fremdschluesselverletzungen(conn):
    assert db.check_foreign_keys(conn) == []


def test_merkmalsarray_view_rekonstruiert_paragraph_82(conn):
    """§82 beschreibt vier Arrays; das Schema speichert normalisiert.
    Die View muss die Arrays wieder liefern."""
    import json
    row = conn.execute(
        "SELECT * FROM v_task_features_arrays WHERE task_id = 'ZO07-D3-S-E'"
    ).fetchone()
    assert sorted(json.loads(row["numeric_features"])) == ["CROSSES_TEN", "NEAR_ROUND_NUMBER"]
    assert json.loads(row["structural_features"]) == ["TWO_DIGIT_ADDITION"]
    assert sorted(json.loads(row["strategy_affordances"])) == ["COMPENSATION", "DECOMPOSITION"]
    # FREE_ENTRY kam nach Kritikbefund 12 hinzu; §24 nennt es nicht, es folgt
    # aber aus interaction_mode ENTER und gilt fuer alle Familienpartner.
    assert set(json.loads(row["surface_features"])) >= {"NO_CONTEXT", "SYMBOLIC_ONLY"}
