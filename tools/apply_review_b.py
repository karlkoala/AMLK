"""Korrekturen aus der Kritik, Teil B: Politik und Testerwartungen.

Die operandensymmetrische NEAR_ROUND_NUMBER-Regel (Kritikbefund 3) verschiebt
das Kontrastmerkmal auf COMPENSATION. §71 nennt fuer die erfolgreiche Seite
ausdruecklich beides - "NEAR_ROUND_NUMBER, COMPENSATION_AVAILABLE" - aber nur
COMPENSATION trennt die vier Items so, wie §71 sie gruppiert. Die Politik von
Testfall D und die davon abhaengigen Erwartungen folgen dem.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATCHES = [
    # --- simulation.py: Politik von Testfall D folgt COMPENSATION
    (ROOT / "src/mathkomp/simulation.py",
     '''def policy_number_dependency(task: dict, features: dict) -> bool:
    """§101 Testfall D. Erfolg haengt am Merkmal NEAR_ROUND_NUMBER.

    §71 beschreibt genau dieses Muster: 49+36 und 48+37 gelingen, 37+28 und
    46+27 nicht. Erwartung: das System stuft Addition NICHT pauschal herab,
    sondern vergleicht Merkmale und waehlt ein Contrast Item.
    """
    if "TWO_DIGIT_ADDITION" not in features.get("STRUCTURAL_FEATURE", ()):
        return True
    return "NEAR_ROUND_NUMBER" in features.get("NUMERIC_FEATURE", ())''',
     '''def policy_number_dependency(task: dict, features: dict) -> bool:
    """§101 Testfall D. Der Erfolg haengt daran, ob der Ausgleich in der
    natuerlichen Richtung moeglich ist.

    §71 beschreibt das Muster: 49+36 und 48+37 gelingen, 37+28 und 46+27 nicht.
    Als Merkmal nennt §71 fuer die erfolgreiche Seite "NEAR_ROUND_NUMBER,
    COMPENSATION_AVAILABLE". Getrennt werden die vier Items nur durch das
    zweite: nach der operandensymmetrischen Regel traegt auch 37+28 einen
    runden Anker (28 ist 2 von 30), aber der Ausgleich muesste dort den
    Ausgangswert nach unten anpassen (37+28 = 35+30) statt nach oben
    (49+36 = 50+35). Siehe ENTSCHEIDUNGEN.md D-19 und F-25.

    Erwartung: das System stuft Addition NICHT pauschal herab, sondern
    vergleicht Merkmale und waehlt ein Contrast Item.
    """
    if "TWO_DIGIT_ADDITION" not in features.get("STRUCTURAL_FEATURE", ()):
        return True
    return "COMPENSATION" in features.get("STRATEGY_AFFORDANCE", ())'''),

    # --- test_content.py: Itemzahl
    (ROOT / "tests/test_content.py",
     '''    assert rows["IMPLEMENTER_AUTHORED"] == 13, "Entscheidung D-11"
    assert sum(rows.values()) == 94''',
     '''    assert rows["IMPLEMENTER_AUTHORED"] == 14, \\
        "13 nach Entscheidung D-11, plus ZO06-D3-S-C nach Kritikbefund 10"
    assert sum(rows.values()) == 95'''),

    # --- test_content.py: Kontrastmerkmal
    (ROOT / "tests/test_content.py",
     '''def test_contrast_family_trennt_nach_near_round_number(conn):
    """§71: die erfolgreichen Items tragen NEAR_ROUND_NUMBER, die anderen
    nicht. Genau darin liegt der diagnostische Kontrast."""
    mit = set()
    for r in conn.execute(
        "SELECT t.task_id FROM tasks t JOIN task_features f ON f.task_id = t.task_id"
        " WHERE t.task_family_id = 'ZO07-CONTRAST-01'"
        " AND f.feature_value = 'NEAR_ROUND_NUMBER'"
    ):
        mit.add(r["task_id"])
    assert mit == {"ZO07-D3-S-E", "ZO07-D3-S-F"}''',
     '''def test_contrast_family_trennt_nach_compensation(conn):
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
    assert mit("NEAR_ROUND_NUMBER") != {"ZO07-D3-S-E", "ZO07-D3-S-F"}'''),

    # --- test_schema.py: FREE_ENTRY ergaenzt (Kritikbefund 12)
    (ROOT / "tests/test_schema.py",
     '''    assert sorted(json.loads(row["surface_features"])) == ["NO_CONTEXT", "SYMBOLIC_ONLY"]''',
     '''    # FREE_ENTRY kam nach Kritikbefund 12 hinzu; §24 nennt es nicht, es folgt
    # aber aus interaction_mode ENTER und gilt fuer alle Familienpartner.
    assert set(json.loads(row["surface_features"])) >= {"NO_CONTEXT", "SYMBOLIC_ONLY"}'''),

    # --- test_testfaelle.py: Hypothese auf COMPENSATION
    (ROOT / "tests/test_testfaelle.py",
     '''    assert any("NEAR_ROUND_NUMBER" in h["target_construct"] for h in offen), \\
        "§71 nennt genau dieses Merkmal"''',
     '''    assert any("COMPENSATION" in h["target_construct"] for h in offen), \\
        "§71 nennt COMPENSATION_AVAILABLE fuer die erfolgreiche Seite"'''),

    # --- test_testfaelle.py: Facette auf COMPENSATION
    (ROOT / "tests/test_testfaelle.py",
     '''def test_d_facetten_zeigen_das_muster(alle, conn):
    """§117: statt eines Prozentwerts eine Aufschlüsselung nach Bedingungen.
    Das Merkmal NEAR_ROUND_NUMBER muss sicher sein, seine Abwesenheit nicht."""
    facets = state.facets_of(conn, "SIM-D", "ZO07_ADDITION")
    numeric = facets.get("NUMERIC_FEATURE", {})
    assert numeric["NEAR_ROUND_NUMBER"]["negative_count"] == 0
    assert numeric["NEAR_ROUND_NUMBER"]["positive_count"] >= 2
    assert numeric["NEAR_ROUND_NUMBER"]["status"] == "SECURE"''',
     '''def test_d_facetten_zeigen_das_muster(alle, conn):
    """§117: statt eines Prozentwerts eine Aufschlüsselung nach Bedingungen.
    Unter COMPENSATION muss die Leistung sicher sein, ohne nicht."""
    facets = state.facets_of(conn, "SIM-D", "ZO07_ADDITION")
    strategie = facets.get("STRATEGY_AFFORDANCE", {})
    assert strategie["COMPENSATION"]["negative_count"] == 0
    assert strategie["COMPENSATION"]["positive_count"] >= 2
    assert strategie["COMPENSATION"]["status"] == "SECURE"'''),
]


def main():
    for path, old, new in PATCHES:
        text = path.read_text(encoding="utf-8")
        if old not in text:
            print(f"  NICHT GEFUNDEN in {path.name}: {old.splitlines()[0][:70]}")
            continue
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        print(f"  {path.name}: angepasst ({old.splitlines()[0][:60]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
