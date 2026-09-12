"""Baut die §69-Kette so um, dass jeder Schritt genau eine Variable aendert.

Die Pruefregel auf question_form hat drei konfundierte Routen gefunden, darunter
die gerade selbst ergaenzte R032. Der Befund ist richtig:

  ZO06-D2-S-A/-S-B  fragen nach dem Wert einer genannten ZIFFER
                    (VALUE_OF_NAMED_DIGIT) - die Stelle muss lokalisiert werden
  ZO06-D2-I-A/-I-B  fragen nach dem Wert einer genannten STELLE
                    (VALUE_OF_NAMED_PLACE) - die Lokalisierung entfaellt

Ein direkter Sprung von der einen auf die andere Seite aendert Darstellung UND
Frageform. §31 nennt beide als getrennte Pruefebenen und gibt sogar die
Reihenfolge vor:

    7  Aufgabentyp
    8  Darstellung

Genau so wird die Kette gebaut: erst die Frageform wechseln und symbolisch
bleiben, dann die Darstellung wechseln und die Frageform konstant halten.
Damit ist jeder Einzelschritt nach §116 interpretierbar.

Bei der Multiplikation ist die Frageform NICHT trennbar: eine Multiplikation
ikonisch zu stellen heisst notwendig, die Faktoren als Struktur zu zeigen. Die
Frageform beider Seiten ist deshalb COMPUTE_RESULT - verlangt wird das Produkt,
nur die Darbietung der Faktoren unterscheidet sich. Das ist die
Darstellungsdifferenz selbst und keine zweite Variable.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

#: Frageformen, die die Ableitungsregel nicht richtig treffen kann, weil sie
#: den Aufgabentext braucht und nicht nur den Payload.
CORRECTIONS = {
    # Payload enthaelt hundreds/tens/ones, gefragt ist aber nur der Wert EINER
    # Stelle - dieselbe Frage wie bei ZO06-D2-S-C/-S-D.
    "ZO06-D2-I-A": "VALUE_OF_NAMED_PLACE",
    "ZO06-D2-I-B": "VALUE_OF_NAMED_PLACE",
    # Malwinkel mit verdecktem Inneren: verlangt ist das Produkt, nicht das
    # Abzaehlen einer Menge. Dieselbe Frage wie bei 6*8 symbolisch.
    "ZO09-D2-I-A": "COMPUTE_RESULT",
    "ZO09-D2-I-B": "COMPUTE_RESULT",
}


def main() -> int:
    # 1. Frageformen korrigieren
    tasks = json.loads((CONTENT / "tasks.json").read_text(encoding="utf-8"))
    for task in tasks["tasks"]:
        form = CORRECTIONS.get(task["task_id"])
        if form:
            task["question_form"] = form
            task["note"] = (task.get("note") or "").rstrip() + (
                f" question_form auf {form} korrigiert: die Ableitungsregel liest den"
                " Payload, nicht den Aufgabentext, und traf hier das Falsche.")
    (CONTENT / "tasks.json").write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"tasks.json: {len(CORRECTIONS)} Frageformen korrigiert")

    # 2. Neuer ROUTE_REASON fuer §31 Schritt 7
    vocab = json.loads((CONTENT / "vocabularies.json").read_text(encoding="utf-8"))
    reasons = next(v for v in vocab["vocabularies"] if v["vocabulary"] == "ROUTE_REASON")
    if not any(t["term"] == "CHECK_TASK_TYPE" for t in reasons["terms"]):
        index = next(i for i, t in enumerate(reasons["terms"])
                     if t["term"] == "CHANGE_REPRESENTATION")
        reasons["terms"].insert(index, {
            "term": "CHECK_TASK_TYPE",
            "label_de": "Aufgabentyp prüfen",
            "notes": "SPEC §31 Schritt 7. §31 führt Aufgabentyp (7) und Darstellung (8)"
                     " als getrennte Prüfebenen; ohne diesen Grund ließe sich ein"
                     " Wechsel der Frageform nicht von einem Darstellungswechsel"
                     " unterscheiden (§116).",
        })
        (CONTENT / "vocabularies.json").write_text(
            json.dumps(vocab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("vocabularies.json: ROUTE_REASON.CHECK_TASK_TYPE")

    # 3. Die §69-Kette in zwei Schritte trennen
    routes = json.loads((CONTENT / "task_routes.json").read_text(encoding="utf-8"))
    by_id = {r["route_id"]: r for r in routes["task_routes"]}

    by_id["R003"].update({
        "target_task": "ZO06-D2-S-C",
        "reason": "CHECK_TASK_TYPE",
        "spec_section": "§69, §31, §116",
        "notes":
            "Erster Schritt des Darstellungsvergleichs aus §69, aber noch ohne"
            " Darstellungswechsel. Die Seed-Items ZO06-D2-S-A/-S-B fragen nach dem"
            " Wert einer genannten ZIFFER und verlangen zusätzlich, deren Stelle zu"
            " lokalisieren; das ikonische Gegenstück nennt die Stelle. Ein direkter"
            " Sprung würde Darstellung und Frageform zugleich wechseln (§116). Diese"
            " Route wechselt nur die Frageform und bleibt symbolisch - §31 Schritt 7"
            " 'Aufgabentyp' geht Schritt 8 'Darstellung' voraus.",
    })
    if "R033" not in by_id:
        routes["task_routes"].append({
            "route_id": "R033",
            "source_task": "ZO06-D2-S-C",
            "condition": "WRONG",
            "target_task": "ZO06-D2-S-D",
            "target_competency": None,
            "reason": "REPLICATE_ERROR",
            "priority": 100,
            "enabled": 1,
            "requires_status": None,
            "requires_hypothesis": None,
            "spec_section": "§30, §69",
            "notes": "Parallelitem zu ZO06-D2-S-C. §30: erst die Replikation macht aus"
                     " dem Fehler ein Muster.",
        })
    by_id_new = {r["route_id"]: r for r in routes["task_routes"]}
    by_id_new["R032"].update({
        "source_task": "ZO06-D2-S-D",
        "condition": "WRONG_REPLICATED",
        "target_task": "ZO06-D2-I-A",
        "reason": "CHANGE_REPRESENTATION",
        "priority": 90,
        "spec_section": "§69, §31, §116",
        "notes":
            "Zweiter Schritt: jetzt wechselt die Darstellung, und nur sie."
            " ZO06-D2-S-C/-S-D und ZO06-D2-I-A/-I-B tragen dieselbe Stufe, dasselbe"
            " Antwortformat und dieselbe Frageform (VALUE_OF_NAMED_PLACE). Erst dieser"
            " Vergleich erlaubt nach §116 und §32 die Zuschreibung an die Darstellung."
            " §31 Schritt 8.",
    })
    routes["task_routes"].sort(key=lambda r: r["route_id"])
    (CONTENT / "task_routes.json").write_text(
        json.dumps(routes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("task_routes.json: §69-Kette in Frageform- und Darstellungsschritt getrennt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
