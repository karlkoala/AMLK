"""Fuehrt das Feld question_form ein (Kritikbefund 6, §116).

Der Befund: der Darstellungsvergleich aus §69 hielt nach der ersten Reparatur
Schwierigkeit und Antwortformat konstant, aber nicht die FRAGEFORM. Symbolisch
wird eine ZIFFER genannt und ihre Stelle muss lokalisiert werden ("Welchen Wert
hat die Ziffer 6 in 364?"), ikonisch wird die STELLE genannt ("Welchen Wert
haben die Zehnerstangen zusammen?"). Damit variierten weiterhin zwei Dinge, und
§32 verbietet, den Unterschied dann der Darstellung zuzuschreiben.

Ohne ein Feld dafuer bleibt das eine Dokumentationsnotiz. Mit dem Feld wird es
zur Bedingung: der Vergleichsschluessel fuer Abhaengigkeitshypothesen umfasst
Stufe, Antwortformat UND Frageform. Ein konfundierter Vergleich eroeffnet dann
keine Hypothese mehr, sondern bleibt sichtbar offen.

Zusaetzlich werden zwei symbolische Items mit der Frageform des ikonischen
Partners ergaenzt, damit ein sauberer Vergleich ueberhaupt existiert.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

TERMS = [
    ("COUNT_OBJECTS", "Anzahl einer gezeigten Menge nennen"),
    ("STATE_TOTAL_AFTER_COUNTING", "nach dem Zählen die Gesamtanzahl nennen"),
    ("PLACE_EXACT_COUNT", "genau n Objekte legen"),
    ("PRODUCE_ACTION_COUNT", "genau n Handlungen ausführen"),
    ("PARTITION_OBJECTS", "Objekte verteilen, aufteilen oder bündeln"),
    ("JUDGE_INVARIANCE", "beurteilen, ob eine Anzahl gleich bleibt"),
    ("CONTINUE_SEQUENCE", "eine Zahlenfolge fortsetzen"),
    ("NAME_NEIGHBOUR", "Vorgänger, Nachfolger oder Zwischenzahl nennen"),
    ("COMPARE_NUMBERS", "zwei Zahlen vergleichen"),
    ("COMPARE_TO_REFERENCE", "Nähe zu einem genannten Bezugswert beurteilen"),
    ("MEASURE_DISTANCE", "Abstand zweier markierter Zahlen bestimmen"),
    ("COMPUTE_RESULT", "das Ergebnis einer gegebenen Rechnung angeben"),
    ("COMPLETE_EQUATION", "eine Lücke in einer Gleichung füllen"),
    ("COMPLEMENT_TO_TARGET", "auf einen genannten Zielwert ergänzen"),
    ("DERIVE_FROM_KNOWN_FACT", "aus einer gegebenen Aufgabe eine andere ableiten"),
    ("READ_NUMBER_FROM_MATERIAL", "eine Zahl aus Stellenwertmaterial ablesen"),
    ("COMPOSE_FROM_PLACES", "eine Zahl aus genannten Stellenwerten bilden"),
    ("VALUE_OF_NAMED_DIGIT", "Wert einer genannten Ziffer bestimmen"),
    ("VALUE_OF_NAMED_PLACE", "Wert einer genannten Stelle bestimmen"),
    ("DIGIT_AT_NAMED_PLACE", "Ziffer an einer genannten Stelle nennen"),
    ("WORD_TO_NUMERAL", "ein Zahlwort als Zahlzeichen schreiben"),
    ("SELECT_MATCHING_EXPRESSION", "die zur Situation passende Rechnung auswählen"),
    ("SELECT_EQUIVALENT_EXPRESSION", "eine wertgleiche, günstigere Rechnung auswählen"),
    ("SELECT_DECOMPOSITION", "die passende Zerlegung auswählen"),
    ("SELECT_STRATEGY", "die günstige Strategie auswählen"),
    ("MATCH_INVERSE", "die zugehörige Umkehraufgabe zuordnen"),
    ("NAME_DECOMPOSITION", "eine hilfreiche Zerlegung selbst angeben"),
]

#: Ausnahmen, bei denen keine Regel greift oder die Regel das Falsche liefert.
OVERRIDES = {
    "ZO02-D2-S-A": "NAME_NEIGHBOUR",       # Zahl direkt nach 99
    "ZO04-D2-S-C": "NAME_NEIGHBOUR",       # Zahl zwischen 48 und 50
    "ZO04-D3-S-A": "NAME_NEIGHBOUR",       # Vorgaenger von 1000
    "ZO04-D3-I-A": "MEASURE_DISTANCE",     # Zahlenstrahl
    "ZO04-D4-S-A": "COMPARE_TO_REFERENCE",
    "ZO05-D4-S-A": "NAME_DECOMPOSITION",   # freie Angabe, ANY_OF_ACCEPTED
    "ZO08-D4-STRATEGY-A": "SELECT_STRATEGY",
    "ZO06-SUP-D3-L-A": "WORD_TO_NUMERAL",
    # Die beiden Foerderitems aus §92 zeigen eine Stellenwerttafel, einmal mit
    # Material, einmal mit Ziffern in den Spalten. Beide verlangen, die Zahl
    # daraus zu bilden - dieselbe Frageform wie COMPOSE_FROM_PLACES bei
    # ZO06-D3-S-A, nur mit Darstellungsstuetze (§92 ACCESSIBLE ENTRY).
    "ZO06-SUP-D1-I-A": "READ_NUMBER_FROM_MATERIAL",
    "ZO06-SUP-D2-MIXED-A": "COMPOSE_FROM_PLACES",
    "ZO12-D3-S-A": "COMPUTE_RESULT",       # 99+47, gescored wird das Ergebnis
    "ZP04-D2-I-A": "COUNT_OBJECTS",        # Signale zaehlen
    "ZP03-D2-I-A": "COUNT_OBJECTS",        # eines hinzugefuegt
}


def derive(task: dict) -> str:
    """Frageform aus Antwortformat und Aufgabenpayload ableiten."""
    if task["task_id"] in OVERRIDES:
        return OVERRIDES[task["task_id"]]

    payload = task.get("task_payload") or {}
    rule = task["scoring_rule"]
    prompt = task["task_prompt"].lower()

    if payload.get("ask_total_after_counting"):
        return "STATE_TOTAL_AFTER_COUNTING"
    if rule == "INTERACTION_COUNT":
        return "PRODUCE_ACTION_COUNT"
    if rule == "PLACED_OBJECT_COUNT":
        return "PLACE_EXACT_COUNT"
    if rule == "GROUP_PARTITION":
        return "PARTITION_OBJECTS"
    if rule == "BOOLEAN" or "gleich viele" in prompt:
        return "JUDGE_INVARIANCE"
    if rule in ("SEQUENCE_EXACT", "SET_EXACT"):
        return "CONTINUE_SEQUENCE"
    if payload.get("expected_pair") or rule == "SELECT_MULTIPLE":
        return "MATCH_INVERSE"
    if "digit" in payload:
        return "VALUE_OF_NAMED_DIGIT"
    if payload.get("asked_unit") == "TENS_TOTAL":
        return "VALUE_OF_NAMED_PLACE"
    if payload.get("asked_unit") == "TENS_DIGIT":
        return "DIGIT_AT_NAMED_PLACE"
    if payload.get("asked_unit") == "TENS_VALUE":
        return "VALUE_OF_NAMED_PLACE"
    if "hundreds" in payload:
        return "COMPOSE_FROM_PLACES"
    if "tens" in payload and "ones" in payload:
        return "READ_NUMBER_FROM_MATERIAL"
    if "given_fact" in payload:
        if payload.get("options") is not None:
            return "MATCH_INVERSE"
        if "blank_position" in payload:
            return "COMPLETE_EQUATION"
        return "DERIVE_FROM_KNOWN_FACT"
    if "blank_position" in payload:
        return "COMPLETE_EQUATION"
    if "whole" in payload and "known_part" in payload:
        return "COMPLETE_EQUATION"
    if "start" in payload and "target" in payload:
        return "COMPLEMENT_TO_TARGET"
    if payload.get("options") is not None:
        if "strategie" in prompt:
            return "SELECT_STRATEGY"
        if "zerlegung" in prompt or "shown_structure" in payload or "array" in payload:
            return "SELECT_DECOMPOSITION"
        if "denselben wert" in prompt or "entspricht" in prompt or "günstig" in prompt:
            return "SELECT_EQUIVALENT_EXPRESSION"
        if any(k in payload for k in ("objects_first", "objects_removed", "groups",
                                      "per_group", "recipients")):
            return "SELECT_MATCHING_EXPRESSION"
        if "größer" in prompt or "groesser" in prompt:
            return "COMPARE_NUMBERS"
        return "SELECT_MATCHING_EXPRESSION"
    if "operands" in payload or payload.get("operation"):
        return "COMPUTE_RESULT"
    if any(k in payload for k in ("objects", "array", "signal_count")):
        return "COUNT_OBJECTS"
    raise ValueError(f"Keine Frageform ableitbar: {task['task_id']}")


def main() -> int:
    # 1. Vokabular
    vocab = json.loads((CONTENT / "vocabularies.json").read_text(encoding="utf-8"))
    if not any(v["vocabulary"] == "QUESTION_FORM" for v in vocab["vocabularies"]):
        vocab["vocabularies"].append({
            "vocabulary": "QUESTION_FORM",
            "vocabulary_kind": "CLASSIFICATION",
            "spec_section": "§116",
            "description":
                "Was die Aufgabe verlangt, unabhängig von Darstellung (§16) und"
                " Bedienform (§17). Dritte Variable, die ein Vergleich konstant"
                " halten muss: 'Welchen Wert hat die Ziffer 6 in 364?' und 'Welchen"
                " Wert haben die Zehnerstangen zusammen?' fragen Verschiedenes, auch"
                " wenn Stufe und Antwortformat übereinstimmen. §116 verlangt, dass"
                " nur eine relevante Variable variiert; ohne dieses Feld wäre die"
                " Frageform eine unbeobachtete zweite. Entscheidung D-28.",
            "terms": [{"term": t, "label_de": label, "notes": "TECHNICAL"}
                      for t, label in TERMS],
        })
        (CONTENT / "vocabularies.json").write_text(
            json.dumps(vocab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"vocabularies.json: QUESTION_FORM mit {len(TERMS)} Termen")

    # 2. Zwei symbolische Items mit der Frageform des ikonischen Partners.
    tasks = json.loads((CONTENT / "tasks.json").read_text(encoding="utf-8"))
    by_id = {t["task_id"]: t for t in tasks["tasks"]}
    neu = [
        ("ZO06-D2-S-C", "Welchen Wert haben die Zehner in 364 zusammen?", 364, 60,
         "ZO06-D2-S-D"),
        ("ZO06-D2-S-D", "Welchen Wert haben die Zehner in 572 zusammen?", 572, 70, None),
    ]
    for task_id, prompt, number, value, parallel in neu:
        if task_id in by_id:
            continue
        tasks["tasks"].append({
            "task_id": task_id,
            "task_family_id": "FAM_ZO06_D2_SAME_QUESTION",
            "title": f"Wert der Zehner in {number}",
            "primary_competency": "ZO06_PLACE_VALUE",
            "internal_difficulty": "D2",
            "representation_mode": "MATHEMATICAL_SYMBOL",
            "interaction_mode": "ENTER",
            "language_demand": "LOW",
            "task_prompt": prompt,
            "task_payload": {"number": number, "asked_unit": "TENS_VALUE"},
            "correct_answer": {"value": value},
            "scoring_rule": "EXACT_NUMERIC",
            "task_purpose": "CONTRAST",
            "source_type": "IMPLEMENTER_AUTHORED",
            "parallel_item_id": parallel,
            "grade_reference_min": 3, "grade_reference_max": 4,
            "structural_features": ["PLACE_VALUE_DECOMPOSITION"],
            "surface_features": ["SYMBOLIC_ONLY", "FREE_ENTRY", "NO_CONTEXT"],
            "strategy_affordances": ["PLACE_VALUE_STRATEGY"],
            "spec_section": "§69, §116",
            "note":
                "Ergaenzt nach Kritikbefund 6. Die Seed-Items ZO06-D2-S-A/-S-B fragen"
                " nach dem Wert einer genannten ZIFFER, das ikonische Gegenstueck"
                " ZO06-D2-I-A nach dem Wert einer genannten STELLE. Der"
                " Darstellungsvergleich aus §69 variierte damit weiterhin zwei Dinge."
                " Dieses Item traegt dieselbe Frageform wie das ikonische und macht"
                " den Vergleich nach §116 sauber. Die Seed-Items bleiben unberuehrt"
                " (§1).",
        })
    by_id = {t["task_id"]: t for t in tasks["tasks"]}

    # 3. Frageform fuer alle Items
    fehlend = []
    verteilung: dict[str, int] = {}
    for task in tasks["tasks"]:
        try:
            form = derive(task)
        except ValueError as exc:
            fehlend.append(str(exc))
            continue
        task["question_form"] = form
        verteilung[form] = verteilung.get(form, 0) + 1
    if fehlend:
        for line in fehlend:
            print(f"  FEHLER: {line}")
        return 1

    tasks["_comment"] = tasks["_comment"] + [
        "",
        "question_form (§116, Entscheidung D-28) hält fest, WAS die Aufgabe verlangt -",
        "unabhängig von Darstellung und Bedienform. Der Vergleichsschlüssel für",
        "Abhängigkeitshypothesen umfasst Stufe, Antwortformat und Frageform; ein",
        "Vergleich, der zwei davon ändert, eröffnet keine Hypothese mehr.",
    ]
    (CONTENT / "tasks.json").write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"tasks.json: {len(tasks['tasks'])} Items mit question_form")
    for form, n in sorted(verteilung.items(), key=lambda kv: -kv[1]):
        print(f"    {form:<32} {n}")

    # 4. Neue Familie
    families = json.loads((CONTENT / "task_families.json").read_text(encoding="utf-8"))
    if not any(f["task_family_id"] == "FAM_ZO06_D2_SAME_QUESTION"
               for f in families["task_families"]):
        families["task_families"].append({
            "task_family_id": "FAM_ZO06_D2_SAME_QUESTION",
            "name": "ZO06 D2 Wert der Zehner, symbolisch",
            "family_type": "PARALLEL_ITEM",
            "primary_competency": "ZO06_PLACE_VALUE",
            "diagnostic_purpose":
                "Symbolische Seite des Darstellungsvergleichs aus §69 mit derselben"
                " Frageform wie FAM_ZO06_D2_ICONIC. Erst mit diesem Paar hält der"
                " Vergleich Stufe, Antwortformat UND Frageform konstant (§116).",
            "spec_section": "§69, §116",
            "notes":
                "Ergaenzt nach Kritikbefund 6. Die Seed-Items ZO06-D2-S-A/-S-B fragen"
                " nach dem Wert einer Ziffer und verlangen zusätzlich, deren Stelle zu"
                " lokalisieren - eine Anforderung, die das ikonische Gegenstück nicht"
                " hat. Sie bleiben als eigene Familie erhalten (§1).",
        })
        (CONTENT / "task_families.json").write_text(
            json.dumps(families, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("task_families.json: FAM_ZO06_D2_SAME_QUESTION ergaenzt")

    # 5. Route auf das gleichfoermige Paar
    routes = json.loads((CONTENT / "task_routes.json").read_text(encoding="utf-8"))
    ids = {r["route_id"] for r in routes["task_routes"]}
    if "R032" not in ids:
        routes["task_routes"].append({
            "route_id": "R032",
            "source_task": "ZO06-D2-S-D",
            "condition": "WRONG_REPLICATED",
            "target_task": "ZO06-D2-I-A",
            "target_competency": None,
            "reason": "CHANGE_REPRESENTATION",
            "priority": 90,
            "enabled": 1,
            "requires_status": None,
            "requires_hypothesis": None,
            "spec_section": "§69, §116",
            "notes":
                "Darstellungswechsel mit konstanter Frageform. R003 leistet dasselbe"
                " von den Seed-Items aus, dort variiert aber zusätzlich die Frageform"
                " (Kritikbefund 6); diese Route ist der saubere Vergleich.",
        })
        routes["task_routes"].sort(key=lambda r: r["route_id"])
        (CONTENT / "task_routes.json").write_text(
            json.dumps(routes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("task_routes.json: R032 ergaenzt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
