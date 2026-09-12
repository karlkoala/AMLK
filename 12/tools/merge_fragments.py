"""Fuehrt die autorisierten Inhaltsfragmente in content/*.json zusammen.

Einmalig ausfuehrbares Werkzeug, kein Teil der Laufzeit. Es dokumentiert, welche
Entscheidung welche Datei geaendert hat - die Fragmente unter
content/_fragments/ bleiben als Nachweis liegen.

Angewandte Entscheidungen (siehe ENTSCHEIDUNGEN.md):
  D-01  ID-Kollision ZO07-D3-S-A aufgeloest, §24-Item wird ZO07-D3-S-E
  D-02  48+37 wird ZO07-D3-S-F
  D-03  doppelt gefuehrte Items zusammengelegt
  D-09  Distraktoren fuer 11 Auswahlaufgaben
  D-10  akzeptierte Antworten fuer ZO05-D4-S-A
  D-11  13 neue Items, 2 neue Familien, 4 reparierte Familien, 16 Routen
  D-12  77 Relationskanten
  D-13  46 Kompetenzbeschreibungen
  D-15  language_demand fuer alle Items
  D-19  Prozesskompetenzen
  D-21  Klassenstufenreferenzen
  D-19f Merkmalsergaenzungen inklusive NEAR_ROUND_NUMBER nach Regel
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
FRAGMENTS = CONTENT / "_fragments"

RENAMES = {"ZO07-CONTRAST-01-A": "ZO07-D3-S-E", "ZO07-CONTRAST-01-B": "ZO07-D3-S-F"}

#: D-03: inhaltlich identische Items werden zusammengelegt. Der Wert nennt das
#: bleibende Item und die Kompetenz, die dort als Sekundaerkompetenz eintritt.
MERGES = {
    "ZO07-D3-S-B": ("ZO12-D2-S-A", "ZO07_ADDITION"),
    "ZO09-D4-S-A": ("ZO13-D3-S-A", "ZO09_MULTIPLICATION"),
}

FEATURE_FIELDS = ("numeric_features", "structural_features", "surface_features",
                  "strategy_affordances", "additional_demands")


def load(name: str, base: Path = CONTENT) -> dict:
    return json.loads((base / name).read_text(encoding="utf-8"))


def save(name: str, data: dict, base: Path = CONTENT) -> None:
    (base / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


def log(message: str) -> None:
    print(f"  {message}")


# ----------------------------------------------------------------- Vokabulare


def merge_vocabularies() -> None:
    data = load("vocabularies.json")
    by_name = {v["vocabulary"]: v for v in data["vocabularies"]}
    added = 0

    new_terms = [
        ("NUMERIC_FEATURE", "CROSSES_THOUSAND", "überschreitet einen Tausender",
         "§20 kennt nur CROSSES_TEN und CROSSES_HUNDRED. ZO04-D3-S-A (Vorgänger von 1000)"
         " überschreitet einen Tausender; ohne diesen Term wäre das Merkmal nicht"
         " darstellbar. Entscheidung D-19."),
        ("STRUCTURAL_FEATURE", "EVENT_COUNTING",
         "Zählen von Ereignissen oder eigenen Handlungen",
         "§45 verlangt für ZP04 das Zählen flüchtiger Signale und eigener Tipp-Handlungen."
         " §21 kennt nur Strukturen an Objektmengen. Entscheidung D-19."),
        ("TASK_SOURCE_TYPE", "IMPLEMENTER_AUTHORED",
         "vom Implementierer ergänzt, fachliche Freigabe offen",
         "Items, die nicht aus §42-57 stammen, sondern zur Schließung von F-21 und F-22"
         " ergänzt wurden. Der eigene Wert macht sie in jeder Abfrage von den"
         " Seed-Items unterscheidbar. Entscheidung D-11."),
    ]
    for vocabulary, term, label, note in new_terms:
        target = by_name[vocabulary]
        if any(t["term"] == term for t in target["terms"]):
            continue
        target["terms"].append({"term": term, "label_de": label, "notes": note})
        added += 1
        log(f"{vocabulary}.{term}")

    if "OPTIONS_STATUS" not in by_name:
        data["vocabularies"].append({
            "vocabulary": "OPTIONS_STATUS",
            "vocabulary_kind": "STATUS",
            "spec_section": "§113",
            "description": "Herkunft der Auswahloptionen eines Items. Dokumentiert, ob die"
                           " Distraktoren aus der Spezifikation stammen oder vom"
                           " Implementierer autorisiert wurden. Steht in"
                           " task_payload.options_status und ist damit nicht per"
                           " Fremdschlüssel erzwungen; der Validator prüft es.",
            "terms": [
                {"term": "UNDEFINED", "label_de": "nicht festgelegt",
                 "notes": "Item ist nach §113 nicht auslieferbar."},
                {"term": "SPEC_GIVEN", "label_de": "wörtlich aus der Spezifikation",
                 "notes": "Nur ZO02-D3-MIXED-A, ZP05-D2-B sowie die Zweiwahl-Items in §48."},
                {"term": "IMPLEMENTER_AUTHORED", "label_de": "vom Implementierer autorisiert",
                 "notes": "Distraktoren nach Entscheidung D-09, fachliche Freigabe offen."},
            ],
        })
        added += 3
        log("OPTIONS_STATUS (neues Vokabular, 3 Terme)")
    save("vocabularies.json", data)
    print(f"vocabularies.json: {added} Terme")


# --------------------------------------------------------------- Kompetenzen


def merge_competencies() -> None:
    data = load("competencies.json")
    fragment = load("beschreibungen.json", FRAGMENTS)
    grades = {c["competency_id"]: c for c in load("merkmale.json", FRAGMENTS)["competencies"]}
    described = {c["competency_id"]: c for c in fragment["competencies"]}

    n_desc = n_grade = 0
    for entry in data["competencies"]:
        cid = entry["competency_id"]
        source = described.get(cid)
        if source and not entry.get("description"):
            parts = [source["description"].strip()]
            if source.get("abgrenzung"):
                parts.append(f"Abgrenzung: {source['abgrenzung'].strip()}")
            if source.get("beobachtbar_an"):
                parts.append(f"Beobachtbar an: {source['beobachtbar_an'].strip()}")
            entry["description"] = " ".join(parts)
            n_desc += 1
        grade = grades.get(cid)
        if grade:
            entry["grade_reference_min"] = grade.get("grade_reference_min")
            entry["grade_reference_max"] = grade.get("grade_reference_max")
            if grade.get("grade_reference_min") is not None:
                n_grade += 1

    data["_comment"] = [
        "Kompetenzknoten. Struktur und Bezeichnungen wörtlich aus §7, §9 und §10.",
        "",
        "parent_id modelliert ausschließlich die strukturelle Zugehörigkeit aus §10",
        "(Gliederung des Dokuments). Es ist KEINE Voraussetzungsbeziehung.",
        "Voraussetzungen liegen ausschließlich in relations.json (§11, §12).",
        "",
        "description ist unter Entscheidung D-13 ergänzt: §10 listet die Knoten nur",
        "als Stichworte. Jede Beschreibung nennt, was die Kompetenz ist, wie sie sich",
        "von ihren Geschwistern abgrenzt und woran sie beobachtbar ist.",
        "",
        "grade_reference_min/max ist unter Entscheidung D-21 belegt, abgeleitet aus",
        "Zahlenraum und Operation der zugeordneten Items. §94 ist bindend: die",
        "Klassenstufe ist eine Referenz, keine Schranke - das Routing darf darüber",
        "hinausgehen (routing.allow_above_grade).",
        "",
        "L2 bis L5 existieren als Wurzelknoten ohne Inhalt, damit §7 erfüllt ist:",
        "'Die übrigen Bereiche müssen aber bereits als Querverbindungen",
        "referenzierbar sein.'",
    ]
    save("competencies.json", data)
    print(f"competencies.json: {n_desc} Beschreibungen, {n_grade} Klassenstufenreferenzen")
    for problem in fragment.get("nicht_trennscharf", []):
        log(f"NICHT TRENNSCHARF {', '.join(problem['knoten'])}: {problem['problem'][:100]}")


# ----------------------------------------------------------------- Relationen


def merge_relations() -> None:
    data = load("relations.json")
    fragment = load("relationen.json", FRAGMENTS)
    existing = {r["relation_id"] for r in data["relations"]}
    pairs = {(r["source_competency"], r["target_competency"], r["relation_type"])
             for r in data["relations"]}

    added = skipped = 0
    for relation in fragment["relations"]:
        key = (relation["source_competency"], relation["target_competency"],
               relation["relation_type"])
        if relation["relation_id"] in existing or key in pairs:
            skipped += 1
            continue
        data["relations"].append({k: v for k, v in relation.items() if k != "begruendung"})
        existing.add(relation["relation_id"])
        pairs.add(key)
        added += 1

    data["_comment"] = [
        "Relationen im Kompetenzgraphen (§12, §13, §80).",
        "",
        "§10 listet die Kompetenzknoten, gibt aber KEINE Kantenliste an. §11 stellt",
        "ausdrücklich fest, dass der Graph kein linearer Baum ist, die Kanten also",
        "nicht aus der Reihenfolge in §10 folgen. Version 1.0 dieses Repos enthielt",
        "deshalb nur die 12 Kanten, die der Text selbst behauptet (REL_001 bis",
        "REL_012). Die übrigen sind unter Entscheidung D-12 autorisiert.",
        "",
        "evidence_status nach §13 und §114:",
        "  C = fachdidaktisch gut gestützt, aber ohne empirische Fundstelle",
        "  D = Systemhypothese, schwächer begründet",
        "A und B werden NICHT vergeben: für keine dieser Kanten liegt eine empirische",
        "Fundstelle vor. §13 erlaubt einer C- oder D-Beziehung, eine Kontrollaufgabe",
        "auszulösen, verbietet ihr aber, eine Aussage über die Schüler:in zu erzeugen.",
        "Die Evidence Engine hält sich daran: eine Voraussetzungskante erzeugt nur",
        "INDIRECT_POSITIVE bei richtiger Antwort und nie indirekt negative Evidenz",
        "(§29, §121).",
        "",
        "strength ist durchgängig null = UNDEFINED. §80 führt das Feld, definiert aber",
        "keine Skala.",
        "",
        "Jede Kante nennt in spec_section ihre Fundstelle oder ihre Herleitung und in",
        "notes die fachdidaktische Begründung.",
    ]
    save("relations.json", data)
    print(f"relations.json: {added} Kanten ergänzt, {skipped} übersprungen"
          f" (gesamt {len(data['relations'])})")
    for rejected in fragment.get("abgelehnte_kanten", [])[:6]:
        log(f"ABGELEHNT {rejected['von']} -> {rejected['nach']}: {rejected['grund'][:90]}")


# ------------------------------------------------------------------- Aufgaben


def merge_tasks() -> None:
    data = load("tasks.json")
    new_items = load("neue_items.json", FRAGMENTS)
    features = {t["task_id"]: t for t in load("merkmale.json", FRAGMENTS)["tasks"]}
    distractors = load("distraktoren.json", FRAGMENTS)
    by_id = {t["task_id"]: t for t in data["tasks"]}

    # 1. D-03: zusammenlegen. Das bleibende Item erhält die Kompetenz des
    #    entfallenden als Sekundärkompetenz (§14: ein Item kann mehrere
    #    Kompetenzen berühren).
    removed = []
    for gone, (kept, secondary) in MERGES.items():
        if gone not in by_id:
            continue
        target = by_id[kept]
        secondaries = target.setdefault("secondary_competencies", [])
        if secondary not in secondaries:
            secondaries.append(secondary)
        target["note"] = (target.get("note") or "") + (
            f" Entscheidung D-03: das inhaltlich identische Item {gone} ist entfallen;"
            f" {secondary} ist als Sekundärkompetenz eingetreten, damit die Evidenz"
            " weiterhin dort ankommt (INDIRECT_*, §28).")
        data["tasks"] = [t for t in data["tasks"] if t["task_id"] != gone]
        removed.append(gone)
    by_id = {t["task_id"]: t for t in data["tasks"]}
    log(f"D-03 zusammengelegt, entfallen: {', '.join(removed)}")

    # 2. D-01/D-02: Umbenennung, damit die IDs dem Schema aus §42-57 folgen.
    for task in data["tasks"]:
        if task["task_id"] in RENAMES:
            new_id = RENAMES[task["task_id"]]
            task["note"] = (task.get("note") or "") + (
                f" Entscheidung D-01/D-02: ID von {task['task_id']} auf {new_id}"
                " geändert, damit sie dem Muster {Kompetenz}-{Stufe}-{Darstellung}-"
                "{Variante} aus §42-57 folgt. Die Familie behält den Namen"
                " ZO07-CONTRAST-01 aus §52.")
            task["task_id"] = new_id
        if task.get("parallel_item_id") in RENAMES:
            task["parallel_item_id"] = RENAMES[task["parallel_item_id"]]
    log(f"D-01/D-02 umbenannt: {', '.join(f'{k} -> {v}' for k, v in RENAMES.items())}")
    by_id = {t["task_id"]: t for t in data["tasks"]}

    # 3. Merkmale, Sprachanforderung, Klassenstufe, Prozesskompetenzen (D-15/19/21).
    n_features = 0
    for task in data["tasks"]:
        source = features.get(task["task_id"])
        if source is None:
            continue
        task["language_demand"] = source["language_demand"]
        task["grade_reference_min"] = source.get("grade_reference_min")
        task["grade_reference_max"] = source.get("grade_reference_max")
        if source.get("process_competencies"):
            task["process_competencies"] = source["process_competencies"]
        for field in FEATURE_FIELDS:
            current = list(task.get(field, []))
            for value in source.get(f"add_{field}", []):
                if value not in current:
                    current.append(value)
                    n_features += 1
            for value in source.get(f"remove_{field}", []):
                if value in current:
                    current.remove(value)
                    n_features += 1
            if current:
                task[field] = sorted(current)
            else:
                task.pop(field, None)
    log(f"D-15/19/21 angewandt, {n_features} Merkmalsänderungen")

    # 4. D-09: Distraktoren.
    n_options = 0
    for item in distractors["items"]:
        task = by_id.get(item["task_id"])
        if task is None:
            continue
        payload = task.setdefault("task_payload", {})
        payload["options"] = item["options"]
        payload["options_status"] = item.get("options_status", "IMPLEMENTER_AUTHORED")
        payload.pop("expected_pair", None)
        rationale = "; ".join(
            f"{d['option']} = {d['fehlvorstellung']} ({d['error_code']})"
            for d in item["distraktoren"])
        task["note"] = (task.get("note") or "") + (
            f" Entscheidung D-09: Distraktoren autorisiert. {rationale}.")
        n_options += 1
    log(f"D-09 angewandt: {n_options} Auswahlaufgaben mit Distraktoren")

    # 5. D-10: akzeptierte Antworten für ZO05-D4-S-A.
    accepted = distractors["any_of_accepted"]
    task = by_id.get(accepted["task_id"])
    if task is not None:
        task["correct_answer"] = {"accepted": accepted["accepted"],
                                  "normalisierung": accepted["normalisierung"]}
        task["note"] = (task.get("note") or "") + (
            f" Entscheidung D-10: akzeptierte Antworten autorisiert."
            f" {accepted['begruendung']}")
        log(f"D-10 angewandt: {accepted['task_id']} akzeptiert"
            f" {len(accepted['accepted'])} Antworten")

    # 6. D-11: neue Items.
    for item in new_items["tasks"]:
        entry = {k: v for k, v in item.items() if k != "begruendung"}
        entry["note"] = (entry.get("note") or "") + f" {item.get('begruendung', '')}"
        entry["source_type"] = "IMPLEMENTER_AUTHORED"
        data["tasks"].append(entry)
    log(f"D-11 angewandt: {len(new_items['tasks'])} neue Items")
    by_id = {t["task_id"]: t for t in data["tasks"]}

    # 7. D-11: Folgeänderungen aus den reparierten Familien.
    repairs = [
        ("ZO09-D2-S-A", "parallel_item_id", "ZO09-D2-S-B"),
        ("ZO09-REL-D3-I-A", "task_family_id", None),
        ("ZO07-D2-S-A", "parallel_item_id", "ZO07-D2-S-C"),
        ("ZO07-D2-S-B", "parallel_item_id", "ZO07-D2-S-D"),
        ("ZO07-D2-S-B", "task_purpose", "CONTRAST"),
    ]
    for task_id, field, value in repairs:
        if task_id in by_id:
            by_id[task_id][field] = value
    log(f"D-11 Folgeänderungen an {len({r[0] for r in repairs})} bestehenden Items")

    data["_comment"] = [
        "Aufgabenbank. Alle Items aus §42 bis §57, dazu die unter Entscheidung D-11",
        "ergänzten Items zur Schließung von F-21 und F-22.",
        "",
        "HERKUNFT: source_type SPEC_SEED_MVP bezeichnet Items aus §42-57,",
        "IMPLEMENTER_AUTHORED die ergänzten. Alle tragen calibration_status",
        "UNCALIBRATED_MVP_ITEM (§6) - keines ist ein validiertes Testitem.",
        "",
        "primary_competency folgt der Kapitelüberschrift des jeweiligen Abschnitts",
        "(z.B. '50. Stellenwert - ZO06'), also der Gruppenebene. Eine feinere",
        "Zuordnung zu Unterknoten wäre eine fachliche Entscheidung und bleibt offen",
        "(F-16); die Facettenaufschlüsselung nach §117 leistet dasselbe ohne sie.",
        "",
        "representation_mode folgt dem Darstellungskürzel der Item-ID: I = IMAGE,",
        "S = MATHEMATICAL_SYMBOL, L = NATURAL_LANGUAGE, ACTION = ACTION,",
        "MIXED = MIXED. Die ZP05-Items in §46 tragen kein Kürzel (F-15, D-16).",
        "",
        "task_payload.options_status hält fest, woher die Distraktoren kommen:",
        "SPEC_GIVEN aus §42-57, IMPLEMENTER_AUTHORED nach Entscheidung D-09.",
        "Ein Item mit UNDEFINED darf der Renderer nicht ausliefern (§113).",
        "",
        "Das Feld note ist Dokumentation und wird nicht in die Datenbank importiert;",
        "§81 führt für tasks kein notes-Feld. Die Fundstelle steht in spec_section",
        "und wird als source_reference übernommen.",
    ]
    save("tasks.json", data)
    print(f"tasks.json: {len(data['tasks'])} Items")


# ------------------------------------------------------------------ Familien


def merge_families() -> None:
    data = load("task_families.json")
    new_items = load("neue_items.json", FRAGMENTS)
    existing = {f["task_family_id"] for f in data["task_families"]}
    by_id = {f["task_family_id"]: f for f in data["task_families"]}

    added = 0
    for family in new_items["task_families"]:
        if family["task_family_id"] in existing:
            continue
        data["task_families"].append(
            {k: v for k, v in family.items() if k != "begruendung"})
        added += 1

    # Reparaturen aus dem Fragment, als strukturierte Änderungen.
    if "FAM_ZO09_6X8_REPRESENTATION" in by_id:
        family = by_id["FAM_ZO09_6X8_REPRESENTATION"]
        family["notes"] = (
            "6*8 und 7*6, jeweils symbolisch und ikonisch. Die vier Items bilden eine"
            " 2x2-Anordnung aus Darstellung und Zahlenpaar. Schwierigkeit (D2),"
            " Bedienform (ENTER) und Antwortformat (EXACT_NUMERIC) sind in der ganzen"
            " Familie konstant; jeder diagnostisch genutzte Einzelvergleich verändert"
            " genau eine Variable - S-A gegen I-A nur die Darstellung, S-A gegen S-B"
            " nur das Zahlenpaar. §116 erfüllt. Entscheidung D-11 schließt damit F-21:"
            " vorher lagen die verglichenen Items auf verschiedenen Stufen und mit"
            " verschiedenen Antwortformaten. ZO09-REL-D3-I-A ist aus der Familie"
            " ausgetreten und bleibt Schritt 2 der Förderroute aus §93.")
    if "FAM_ZO07_D2_TWO_DIGIT" in by_id:
        family = by_id["FAM_ZO07_D2_TWO_DIGIT"]
        family["name"] = "ZO07 D2 Contrast Family zweistellige Addition"
        family["family_type"] = "CONTRAST_ITEM"
        family["diagnostic_purpose"] = (
            "Prüfen, ob der Erfolg bei zweistelliger Addition am Merkmal"
            " NEAR_ROUND_NUMBER hängt - derselbe Kontrast wie ZO07-CONTRAST-01, aber"
            " auf D2. §52 ausdrücklich: nicht automatisch 'Addition sicher/unsicher'.")
        family["notes"] = (
            "38+27 und 39+24 mit NEAR_ROUND_NUMBER, 46+38 und 47+35 ohne. Kompetenz,"
            " Schwierigkeit (D2), Darstellung und Bedienform sind konstant; zwischen"
            " den Hälften variiert nur das Merkmal NEAR_ROUND_NUMBER, innerhalb einer"
            " Hälfte nur die Ziffern. §116 erfüllt. Der Wechsel von PARALLEL_ITEM auf"
            " CONTRAST_ITEM folgt aus Entscheidung D-19: nach der operationalen Regel"
            " für NEAR_ROUND_NUMBER trägt 38+27 das Merkmal und 46+38 nicht, womit die"
            " beiden kein Parallelpaar mehr sind.")
    if "FAM_ZO06_D1_ICONIC" in by_id:
        family = by_id["FAM_ZO06_D1_ICONIC"]
        family["diagnostic_purpose"] = (
            "Fehler beim Ablesen einer ikonischen Zehner-Einer-Darstellung replizieren."
            " Die Rolle der ikonischen Gegenprobe nach §69 ist an FAM_ZO06_D2_ICONIC"
            " übergegangen, weil diese auf derselben Stufe wie die symbolischen Items"
            " liegt (§116). Diese Familie trägt jetzt die Schwierigkeitsabsenkung"
            " nach §34.")
        family["notes"] = ("4Z+7E / 6Z+3E. Struktur und Darstellung konstant."
                           " §116 erfüllt.")
    if "FAM_ZO06_D2_SYMBOLIC" in by_id:
        family = by_id["FAM_ZO06_D2_SYMBOLIC"]
        family["notes"] = (
            "'Wert der Ziffer 6 in 364' / 'Wert der Ziffer 7 in 572'. §116 erfüllt."
            " Die ikonische Gegenprobe auf derselben Stufe liegt in FAM_ZO06_D2_ICONIC"
            " (3H+6Z+4E / 5H+7Z+2E, gleiche Frageform, gleiches Antwortformat). Der"
            " Darstellungsvergleich läuft über R003 und hält Schwierigkeit und"
            " Antwortformat konstant (§116, Entscheidung D-11).")

    save("task_families.json", data)
    print(f"task_families.json: {added} neu, 4 repariert (gesamt {len(data['task_families'])})")


# -------------------------------------------------------------------- Routen


def merge_routes() -> None:
    data = load("task_routes.json")
    new_items = load("neue_items.json", FRAGMENTS)
    by_id = {r["route_id"]: r for r in data["task_routes"]}

    replaced = added = 0
    for route in new_items["task_routes"]:
        entry = {k: v for k, v in route.items() if k != "begruendung"}
        entry.setdefault("requires_status", None)
        entry.setdefault("requires_hypothesis", None)
        if route.get("reason") == "SUPPORT_ROUTE":
            entry["requires_status"] = "SUPPORT_FOCUS"
        for old, new in RENAMES.items():
            if entry.get("source_task") == old:
                entry["source_task"] = new
            if entry.get("target_task") == old:
                entry["target_task"] = new
        if route["route_id"] in by_id:
            by_id[route["route_id"]].update(entry)
            replaced += 1
        else:
            data["task_routes"].append(entry)
            added += 1

    for route in data["task_routes"]:
        for old, new in RENAMES.items():
            if route.get("source_task") == old:
                route["source_task"] = new
            if route.get("target_task") == old:
                route["target_task"] = new

    data["task_routes"].sort(key=lambda r: r["route_id"])
    save("task_routes.json", data)
    print(f"task_routes.json: {added} neu, {replaced} ersetzt"
          f" (gesamt {len(data['task_routes'])})")


def main() -> int:
    if not FRAGMENTS.exists():
        print(f"Fragmentverzeichnis fehlt: {FRAGMENTS}", file=sys.stderr)
        return 1
    print("VOKABULARE")
    merge_vocabularies()
    print("\nKOMPETENZEN")
    merge_competencies()
    print("\nRELATIONEN")
    merge_relations()
    print("\nAUFGABEN")
    merge_tasks()
    print("\nFAMILIEN")
    merge_families()
    print("\nROUTEN")
    merge_routes()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
