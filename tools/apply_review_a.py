"""Korrekturen aus der Kritik am autorisierten Content, Teil A.

Die beiden Kritiker-Agenten der Inhaltsautorierung haben 43 Befunde geliefert.
Dieses Werkzeug wendet die inhaltlichen Korrekturen an. Jede traegt die Nummer
des Befunds und die Fundstelle in der Spezifikation.

Nicht angewandte Befunde stehen als F-25 bis F-28 in OFFENE_FRAGEN.md.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"


def load(name):
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


def save(name, data):
    (CONTENT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")


def note(entry, text):
    entry["note"] = ((entry.get("note") or "").rstrip() + " " + text).strip()


# ---------------------------------------------------------------- Aufgaben


def fix_tasks():
    data = load("tasks.json")
    by_id = {t["task_id"]: t for t in data["tasks"]}
    log = []

    # ---- Befund 1 (BLOCKER): Das Buendelungsitem war durch Ziffernablesen
    # loesbar. "13 Einerwuerfel, buendle Zehner" -> 1 Zehner, 3 Einer: die
    # Antwort sind die beiden Ziffern von 13. Damit prueft das Item nicht
    # ZO06_1_BUNDLING, sondern das Ablesen - und die Rueckwaertsschritte aus
    # §69 haengen an einer Messung, die ihre Zielkompetenz nicht erreicht.
    # Korrektur: Fuenferbuendel. 13 zu Fuenfern -> 2 Buendel, 3 uebrig; die
    # Antwort steht nicht in den Ziffern. Das Zehneritem bleibt als
    # Kontrastpartner, damit genau eine Variable variiert (§116): die
    # Buendelungsgroesse.
    a = by_id["ZO06-1-D1-ACTION-A"]
    a["task_prompt"] = ("Hier liegen 13 Einerwürfel. Bündle so viele Fünfer, wie du"
                        " kannst. Wie viele Fünferbündel und wie viele einzelne"
                        " Würfel bleiben übrig?")
    a["task_payload"] = {"loose_ones": 13, "material": "UNIT_CUBES", "bundle_size": 5}
    a["correct_answer"] = {"bundles": 2, "remaining": 3}
    a["task_purpose"] = "SCREEN"
    note(a, "Korrektur nach Kritikbefund 1: die vorherige Fassung buendelte Zehner,"
            " wodurch die Antwort (1 Zehner, 3 Einer) genau die Ziffern der genannten"
            " Zahl 13 waren - das Item war ohne Buendelungshandlung loesbar und"
            " konnte ZO06_1_BUNDLING nicht messen. Mit Fuenferbuendeln steht die"
            " Antwort nicht in den Ziffern.")
    b = by_id["ZO06-1-D1-ACTION-B"]
    b["task_prompt"] = ("Hier liegen 13 Einerwürfel. Bündle so viele Zehner, wie du"
                        " kannst. Wie viele Zehnerbündel und wie viele einzelne"
                        " Würfel bleiben übrig?")
    b["task_payload"] = {"loose_ones": 13, "material": "UNIT_CUBES", "bundle_size": 10}
    b["correct_answer"] = {"bundles": 1, "remaining": 3}
    b["task_purpose"] = "CONTRAST"
    note(b, "Kontrastpartner zu ZO06-1-D1-ACTION-A: dieselbe Menge, nur die"
            " Buendelungsgroesse variiert (§116). Bei diesem Item stimmt die Antwort"
            " zufaellig mit den Ziffern von 13 ueberein - gelingt es und das"
            " Fuenferitem nicht, spricht das fuer Ziffernablesen statt Buendeln."
            " Genau dieser Vergleich ist der diagnostische Zweck.")
    log.append("Befund 1: Buendelungspaar auf Fuenfer/Zehner umgestellt")

    # ---- Befund 2 (BLOCKER): Das ikonische 6x8-Punktfeld war durch Abzaehlen
    # der 48 Punkte loesbar, der symbolische Partner nicht. Der Vergleich hielt
    # damit nicht die Darstellung als einzige Variable, sondern auch die Menge
    # der zulaessigen Loesungswege - und genau die trug den Befund.
    # Korrektur: Malwinkel. Zeilen- und Spaltenzahl bleiben sichtbar, das Feld
    # selbst ist verdeckt. §62 verbietet, das ueber eine Zeitgrenze zu loesen.
    for task_id, rows, cols in (("ZO09-D2-I-A", 6, 8), ("ZO09-D2-I-B", 6, 7)):
        t = by_id[task_id]
        t["task_payload"] = {"array": [rows, cols], "material": "ARRAY_WITH_COVER",
                             "interior_covered": True,
                             "visible": "ROW_AND_COLUMN_MARKERS",
                             "decomposition_shown": False}
        note(t, "Korrektur nach Kritikbefund 2: ein offenes Punktfeld waere durch"
                " Abzaehlen loesbar, der symbolische Partner nicht - der Vergleich"
                " haette neben der Darstellung auch die zulaessigen Loesungswege"
                " variiert. Als Malwinkel mit verdecktem Inneren bleiben Zeilen- und"
                " Spaltenzahl sichtbar, das Ergebnis muss multiplikativ bestimmt"
                " werden. §62 verbietet, Abzaehlen ueber eine Zeitgrenze"
                " auszuschliessen.")
    log.append("Befund 2: ikonische Multiplikationsitems auf Malwinkel umgestellt")

    # ---- Befund 3 (FEHLER): Das Parallelitem 7*6 aenderte gegenueber 6*8 beide
    # Faktoren UND ihre Rollen (6 Gruppen von 8 gegen 7 Gruppen von 6). §25
    # verlangt fuer ein Parallelitem, dass sich nur die Zahlen aendern.
    by_id["ZO09-D2-S-B"]["task_prompt"] = "6 * 7"
    by_id["ZO09-D2-S-B"]["task_payload"] = {"operands": [6, 7], "operation": "MULTIPLY"}
    by_id["ZO09-D2-S-B"]["correct_answer"] = {"value": 42}
    note(by_id["ZO09-D2-S-B"],
         "Korrektur nach Kritikbefund 3: vorher 7*6, was gegenueber 6*8 beide"
         " Faktoren und ihre Rollen aenderte. Mit 6*7 bleibt die Gruppenanzahl"
         " konstant und nur die Gruppengroesse variiert (§25, §116).")
    by_id["ZO09-D2-I-B"]["task_payload"]["array"] = [6, 7]
    note(by_id["ZO09-D2-I-B"], "Zeilenzahl 6 wie bei ZO09-D2-I-A, nur die"
                               " Zeilenlaenge variiert (§25).")
    log.append("Befund 3: Parallelitem 7*6 -> 6*7")

    # ---- Befund 7 (BLOCKER): Bei den drei GV-Items war eine Option der
    # Zahlenwert der richtigen Rechnung. Wer sie waehlt, hat die Situation
    # richtig modelliert UND ausgerechnet - also genau die Grundvorstellung
    # gezeigt, die das Item prueft - wurde aber als falsch gewertet und nach
    # §70 in die Foerderkette geleitet.
    # Befund 6 (FEHLER): '4*4' war aus zwei Gruenden waehlbar (Rollentausch oder
    # Verzaehlen) und damit nicht diskriminierend.
    # Korrektur: die Distraktoren pruefen nur noch die Operationsklasse. Genau
    # das ist die Frage der Grundvorstellung; eine Rollenverwechslung ist bei
    # kommutativen Operationen ohnehin nicht als falsch wertbar.
    gv = {
        "ZO07-GV-D1-I-A": ("6+3", ["6+3", "6-3", "6*3", "6:3"]),
        "ZO08-GV-D1-I-A": ("15-6", ["15-6", "15+6", "15*6", "15:6"]),
        "ZO09-GV-D1-I-A": ("4*3", ["4*3", "4+3", "4-3", "4:3"]),
    }
    for task_id, (correct, options) in gv.items():
        t = by_id[task_id]
        t["task_payload"]["options"] = options
        t["task_payload"]["options_status"] = "IMPLEMENTER_AUTHORED"
        t["correct_answer"] = {"selection": correct}
        note(t, "Korrektur nach Kritikbefunden 6 und 7: die vorherige Optionsliste"
                " enthielt den Zahlenwert der richtigen Rechnung. Wer ihn waehlt, hat"
                " die Situation richtig modelliert und ausgerechnet, waere aber als"
                " falsch gewertet und nach §70 in die Foerderkette 'Grundvorstellung"
                " pruefen' geleitet worden. Ausserdem war ein Distraktor aus zwei"
                " Gruenden waehlbar. Die drei Distraktoren pruefen jetzt genau eine"
                " Frage: welche Operationsklasse passt zur Situation. Rollentausch"
                " ist kein Distraktor, weil er bei kommutativen Operationen"
                " denselben Wert ergibt und vom Scoring als richtig gilt.")
    log.append("Befund 6/7: Distraktoren der drei GV-Items auf Operationsklasse reduziert")

    # ---- Befund 5 (FEHLER): drei der vier Distraktoren von ZO11-D3-S-A waren
    # fuer sich richtig gerechnet. Ein einziges Verhalten - alles anwaehlen, was
    # eine wahre Gleichung ist - erzeugte alle drei Wahlen, denen die Datei drei
    # verschiedene Fehlvorstellungen zuschrieb.
    t = by_id["ZO11-D3-S-A"]
    t["task_payload"]["options"] = ["6*7=42", "42:7=6", "42-7=35", "6+7=13"]
    note(t, "Korrektur nach Kritikbefund 5: von den fuer sich richtig gerechneten"
            " Distraktoren bleibt nur '42-7=35' (Verwechslung der Umkehroperation:"
            " Subtraktion statt Division). '24:6=4' ist entfallen, weil eine"
            " Ziffernumkehrung an einem Item ueber das Tripel (6, 7, 42) nicht"
            " interpretierbar ist.")
    log.append("Befund 5: ZO11-D3-S-A Distraktor '24:6=4' entfernt")

    # ---- Befund 13 (FEHLER): '40+36' bei ZO12-D2-S-A war aus zwei Gruenden
    # waehlbar - Ziffernabschneiden bei 49 (Stellenwert) oder Abrunden ohne
    # Ausgleich (Strategie). §31 Rang 3 verlangt, die Stellenwertlesart an einem
    # Stellenwertitem zu pruefen, nicht hier zu inferieren.
    t = by_id["ZO12-D2-S-A"]
    options = t["task_payload"].get("options") or []
    t["task_payload"]["options"] = ["50+35" if o == "50+35" else o
                                    for o in options if o != "40+36"]
    if "50+34" not in t["task_payload"]["options"]:
        t["task_payload"]["options"].append("50+34")
    note(t, "Korrektur nach Kritikbefund 13: '40+36' war aus zwei Gruenden waehlbar"
            " (Ziffernabschneiden oder Abrunden ohne Ausgleich) und damit nicht"
            " diskriminierend. Ersetzt durch '50+34': Ausgleich in der falschen"
            " Richtung, eindeutig ein Strategiefehler.")
    log.append("Befund 13: ZO12-D2-S-A Distraktor '40+36' -> '50+34'")

    # ---- Befund 10 (FEHLER): FAM_ZO06_D3_ZERO konnte den Nullstellenfehler
    # replizieren, aber nicht kontrastieren - beide Mitglieder tragen eine Null
    # an der Zehnerstelle. Ein nullfreies Kontrollitem auf derselben Stufe
    # trennt ZO06.5 (Stellenwertzerlegung) von ZO06.6 (Null als unbesetzte
    # Stelle).
    if "ZO06-D3-S-C" not in by_id:
        data["tasks"].append({
            "task_id": "ZO06-D3-S-C",
            "task_family_id": "FAM_ZO06_D3_ZERO",
            "title": "5 Hunderter, 3 Zehner, 8 Einer",
            "primary_competency": "ZO06_PLACE_VALUE",
            "internal_difficulty": "D3",
            "representation_mode": "MATHEMATICAL_SYMBOL",
            "interaction_mode": "ENTER",
            "language_demand": "LOW",
            "task_prompt": "5 Hunderter + 3 Zehner + 8 Einer.",
            "task_payload": {"hundreds": 5, "tens": 3, "ones": 8},
            "correct_answer": {"value": 538},
            "scoring_rule": "EXACT_NUMERIC",
            "task_purpose": "CONTRAST",
            "source_type": "IMPLEMENTER_AUTHORED",
            "grade_reference_min": 3, "grade_reference_max": 4,
            "structural_features": ["PLACE_VALUE_DECOMPOSITION"],
            "surface_features": ["SYMBOLIC_ONLY", "FREE_ENTRY", "NO_CONTEXT"],
            "strategy_affordances": ["PLACE_VALUE_STRATEGY"],
            "spec_section": "§50",
            "note": "Ergaenzt nach Kritikbefund 10. Beide bisherigen Mitglieder von"
                    " FAM_ZO06_D3_ZERO tragen eine Null an der Zehnerstelle; die"
                    " Familie konnte den Fehler ERR_ZERO_PLACEHOLDER replizieren, aber"
                    " nicht von einer allgemeinen Schwaeche der Stellenwertzerlegung"
                    " unterscheiden. Gegenueber ZO06-D3-S-A variiert genau eine"
                    " Variable: die Zehnerstelle ist besetzt (§116). Gelingt 538 und"
                    " misslingt 508, liegt der Fehler an der unbesetzten Stelle;"
                    " misslingen beide, an der Stellenwertzerlegung.",
        })
        log.append("Befund 10: nullfreies Kontrollitem ZO06-D3-S-C ergaenzt")

    # ---- Befund 14 (FEHLER): identische Zahlen muessen identische Zahlmerkmale
    # tragen. ZO08-D4-S-A und ZO08-D4-STRATEGY-A betreffen beide 403-198.
    t = by_id["ZO08-D4-STRATEGY-A"]
    t["numeric_features"] = sorted(set(t.get("numeric_features", []))
                                   | {"CROSSES_HUNDRED", "PLACE_VALUE_CHANGE"})
    note(t, "Korrektur nach Kritikbefund 14: dieselbe Rechnung wie ZO08-D4-S-A muss"
            " dieselben Zahlmerkmale tragen.")
    log.append("Befund 14: Zahlmerkmale von ZO08-D4-STRATEGY-A ergaenzt")

    # ---- Befund 12 (FEHLER): die Merkmalszuordnung lief ueber die alten IDs
    # ZO07-CONTRAST-01-A/B und griff nach der Umbenennung nicht mehr. Beide
    # Items trugen deshalb keine Sprachanforderung und keine Klassenstufe,
    # waehrend ihre Familienpartner sie tragen.
    for task_id in ("ZO07-D3-S-E", "ZO07-D3-S-F"):
        t = by_id[task_id]
        t["language_demand"] = "NONE"
        t["grade_reference_min"], t["grade_reference_max"] = 2, 3
        t["surface_features"] = sorted(set(t.get("surface_features", [])) | {"FREE_ENTRY"})
        note(t, "Korrektur nach Kritikbefund 12: die Merkmalszuordnung lief ueber die"
                " alte ID und griff nach der Umbenennung (D-01) nicht mehr.")
    log.append("Befund 12: Merkmale von ZO07-D3-S-E/-S-F nachgetragen")

    # ---- Befund 8 (FEHLER) und Hinweis SMALL/LARGE_FACTS: die Faktenmerkmale
    # gehoeren nur an einstellige Multiplikationen und Divisionen - "Fakt" im
    # Sinne von §20 ist ein abrufbares Einsmaleins-Ergebnis. Ausserdem muessen
    # die vier Mitglieder von FAM_ZO09_6X8_REPRESENTATION dasselbe Zahlprofil
    # tragen, weil sie dieselben Zahlenpaare verwenden.
    n_fact = 0
    for t in data["tasks"]:
        payload = t.get("task_payload") or {}
        operands = payload.get("operands") or []
        array = payload.get("array") or []
        numbers = operands or array
        multiplicative = payload.get("operation") in ("MULTIPLY", "DIVIDE") or bool(array)
        current = set(t.get("numeric_features", []))
        before = set(current)
        current -= {"SMALL_FACTS", "LARGE_FACTS"}
        if multiplicative and len(numbers) == 2 and all(
                isinstance(v, int) and v < 10 for v in numbers):
            product = numbers[0] * numbers[1]
            current.add("SMALL_FACTS" if product <= 25 else "LARGE_FACTS")
        if current != before:
            n_fact += 1
            if current:
                t["numeric_features"] = sorted(current)
            else:
                t.pop("numeric_features", None)
            note(t, "Faktenmerkmal nach Kritikhinweis neu bestimmt: SMALL_FACTS und"
                    " LARGE_FACTS gelten nur fuer einstellige Multiplikation und"
                    " Division, weil 'Fakt' im Sinne von §20 ein abrufbares"
                    " Einsmaleins-Ergebnis bezeichnet.")
    log.append(f"Befund 8/Hinweis: Faktenmerkmale bei {n_fact} Items neu bestimmt")

    # ---- Befund 3 (BLOCKER) NEAR_ROUND_NUMBER: die Regel war asymmetrisch -
    # zweistellig zaehlte nur der erste Operand, dreistellig genuegte einer.
    # Diese Asymmetrie hatte keinen fachlichen Grund, sie existierte allein,
    # damit die vier Kontrollfaelle aus §71 herauskommen.
    # Korrektur: operandensymmetrische Definition. Damit traegt 37+28 das
    # Merkmal (28 ist 2 von 30) - abweichend von §71, das das Item als
    # NO_NEAR_ROUND_ANCHOR fuehrt. Die Abweichung wird als F-25 gemeldet statt
    # durch Regeldesign beseitigt.
    # Der Kontrast der Contrast Families traegt jetzt COMPENSATION: §71 nennt
    # fuer die erfolgreiche Seite ausdruecklich COMPENSATION_AVAILABLE.
    def near_round(operands, operation):
        if operation not in ("ADD", "SUBTRACT") or len(operands) < 2:
            return None
        if not all(isinstance(v, int) and v >= 10 for v in operands):
            return False
        base = 100 if max(operands) >= 100 else 10
        return any(min(v % base, base - v % base) <= 2 for v in operands)

    def compensation(operands, operation):
        """Ausgleich in der natuerlichen Richtung: der ERSTE Operand liegt nahe
        an einer runden Zahl, wird aufgerundet und der zweite entsprechend
        verkleinert (49+36 = 50+35). Liegt nur der zweite Operand nahe, muss
        der Ausgangswert nach unten angepasst werden (37+28 = 35+30) - das ist
        die schwierigere Richtung, und §71 ordnet genau diese Items der
        erfolglosen Seite zu."""
        if operation not in ("ADD", "SUBTRACT") or len(operands) < 2:
            return None
        base = 100 if max(operands) >= 100 else 10
        if operation == "SUBTRACT":
            # Bei der Subtraktion traegt der Subtrahend den Anker (403-200+2).
            v = operands[1]
        else:
            v = operands[0]
        return isinstance(v, int) and v >= 10 and min(v % base, base - v % base) <= 2

    n_near = n_comp = 0
    for t in data["tasks"]:
        payload = t.get("task_payload") or {}
        operands = payload.get("operands") or []
        operation = payload.get("operation")
        verdict = near_round(operands, operation)
        if verdict is not None:
            current = set(t.get("numeric_features", []))
            before = set(current)
            current.discard("NEAR_ROUND_NUMBER")
            if verdict:
                current.add("NEAR_ROUND_NUMBER")
            if current != before:
                n_near += 1
                if current:
                    t["numeric_features"] = sorted(current)
                else:
                    t.pop("numeric_features", None)
        verdict = compensation(operands, operation)
        if verdict is not None:
            current = set(t.get("strategy_affordances", []))
            before = set(current)
            current.discard("COMPENSATION")
            if verdict:
                current.add("COMPENSATION")
            if current != before:
                n_comp += 1
                if current:
                    t["strategy_affordances"] = sorted(current)
                else:
                    t.pop("strategy_affordances", None)
    log.append(f"Befund 3: NEAR_ROUND_NUMBER symmetrisch ({n_near} Items),"
               f" COMPENSATION richtungsabhaengig ({n_comp} Items)")

    data["_comment"] = data["_comment"] + [
        "",
        "KORREKTUREN AUS DER KRITIK. Die Kritiker-Agenten der Inhaltsautorierung",
        "haben 43 Befunde geliefert; die inhaltlichen sind angewandt und in den",
        "note-Feldern der betroffenen Items einzeln begründet. Die wichtigsten:",
        "das Bündelungsitem war durch Ziffernablesen lösbar, das ikonische",
        "6·8-Punktfeld durch Abzählen, und drei GV-Items enthielten als Distraktor",
        "den Zahlenwert der richtigen Rechnung - wer ihn wählte, hatte die",
        "Grundvorstellung gezeigt und wurde trotzdem in die Förderkette geleitet.",
        "",
        "NEAR_ROUND_NUMBER ist jetzt operandensymmetrisch definiert. Damit trägt",
        "37+28 das Merkmal, abweichend von §71. Die Abweichung ist als F-25",
        "gemeldet, nicht durch Regeldesign beseitigt. Den Kontrast der",
        "Contrast Families trägt jetzt COMPENSATION - §71 nennt für die",
        "erfolgreiche Seite ausdrücklich COMPENSATION_AVAILABLE.",
    ]
    save("tasks.json", data)
    return log


# ---------------------------------------------------------------- Relationen


def fix_relations():
    data = load("relations.json")
    by_id = {r["relation_id"]: r for r in data["relations"]}
    log = []

    # ---- Befund 4 (BLOCKER): Kanten zwischen zwei Namen fuer denselben
    # Gegenstand. Die notes sagen es selbst; beschreibungen.json fuehrt die
    # Knotenpaare als nicht trennscharf. Eine Voraussetzungskante zwischen
    # Synonymen ist nach §115 nicht widerlegbar und erzeugt in der
    # Rueckwaertssuche nach §36 garantiert redundante Kontrollaufgaben - genau
    # das, was §73 verbietet.
    entfernt = []
    for relation_id in ("REL_019", "REL_021", "REL_038"):
        if relation_id in by_id:
            entfernt.append(f"{relation_id} ({by_id[relation_id]['source_competency']}"
                            f" -> {by_id[relation_id]['target_competency']})")
            data["relations"] = [r for r in data["relations"]
                                 if r["relation_id"] != relation_id]
    log.append(f"Befund 4: {len(entfernt)} Kanten zwischen synonymen Knoten entfernt"
               f" ({', '.join(entfernt)})")

    # ---- Befund 5 (BLOCKER): ZO06_4 wurde von zwei Lanes verschieden
    # definiert. Verbindlich ist die Definition aus den Kompetenzbeschreibungen
    # (Anzahl, die ein Zahlzeichen als Ganzes bezeichnet - 430 enthaelt 43
    # Zehner). Unter dieser Definition deckt REL_048 die Beziehung ab, die
    # REL_051 behauptet.
    if "REL_051" in by_id:
        data["relations"] = [r for r in data["relations"] if r["relation_id"] != "REL_051"]
        log.append("Befund 5: REL_051 entfernt (unter der verbindlichen Definition von"
                   " ZO06_4 von REL_048 abgedeckt)")

    # ---- Hinweis: vier Kanten sind Reihenfolgekanten im Sinne von §11. Ihre
    # Begruendung stuetzt sich darauf, dass Items der Aufgabenbank die andere
    # Operation als bekannt VORGEBEN - das ist eine Aufgabendesign-Entscheidung,
    # kein Entwicklungsvorrang. §13 erlaubt sie als Systemhypothese (D), die
    # eine Kontrollaufgabe ausloesen darf, aber keine Aussage erzeugt.
    herabgesetzt = []
    for relation_id in ("REL_062", "REL_064", "REL_072", "REL_081"):
        r = by_id.get(relation_id)
        if r and r["evidence_status"] == "C":
            r["evidence_status"] = "D"
            r["notes"] = (r["notes"].rstrip() + " Nach Kritikhinweis von C auf D"
                          " herabgesetzt: die Begruendung stuetzt sich darauf, dass"
                          " Items der Aufgabenbank die andere Operation als bekannt"
                          " vorgeben - das ist eine Aufgabendesign-Entscheidung, kein"
                          " Entwicklungsvorrang (§11). Als Systemhypothese darf die"
                          " Kante eine Kontrollaufgabe ausloesen, aber keine Aussage"
                          " ueber die Schueler:in erzeugen (§13).")
            herabgesetzt.append(relation_id)
    log.append(f"Hinweis: {len(herabgesetzt)} Reihenfolgekanten auf evidence_status D"
               f" herabgesetzt ({', '.join(herabgesetzt)})")

    # ---- Hinweis: die Definition von C im Kopfkommentar behauptete
    # "in der Fachliteratur einhellig beschrieben" - das ist die Stufe B, die
    # nach F-02 gerade nicht vergeben werden darf. §13 definiert C als
    # "theoretisch plausibel".
    data["_comment"] = [
        c.replace("fachdidaktisch gut gestützt, aber ohne empirische Fundstelle",
                  "theoretisch plausibel (§13), fachdidaktisch nachvollziehbar")
        for c in data["_comment"]
    ] + [
        "",
        "KORREKTUREN AUS DER KRITIK: drei Kanten zwischen Knoten, die dasselbe",
        "bezeichnen, sind entfernt (REL_019, REL_021, REL_038) - eine",
        "Voraussetzungskante zwischen Synonymen ist nach §115 nicht widerlegbar.",
        "Die betroffenen Knotenpaare stehen als F-24 zur Zusammenlegung.",
        "REL_051 ist entfallen, weil die Definition von ZO06_4 verbindlich aus den",
        "Kompetenzbeschreibungen kommt und REL_048 die Beziehung dort abdeckt.",
        "Vier Reihenfolgekanten sind auf evidence_status D herabgesetzt (§11, §13).",
        "",
        "Der Wortlaut zu C folgt jetzt §13 (theoretisch plausibel). Die vorherige",
        "Fassung sprach von einhelliger Beschreibung in der Fachliteratur - das ist",
        "Stufe B, die nach F-02 ohne Fundstelle nicht vergeben werden darf.",
    ]
    save("relations.json", data)
    return log


# -------------------------------------------------------------------- Routen


def fix_routes():
    data = load("task_routes.json")
    by_id = {r["route_id"]: r for r in data["task_routes"]}
    log = []

    # ---- Befund (Kritiker 2): R024 und R030 haben denselben Schluessel
    # (source_task, condition). Ohne Prioritaetsunterschied entscheidet die
    # Sortierung nach route_id, also der Zufall der Benennung.
    if "R030" in by_id and "R024" in by_id:
        by_id["R030"]["priority"] = 86
        by_id["R024"]["priority"] = 85
        by_id["R030"]["requires_status"] = "SUPPORT_FOCUS"
        by_id["R024"]["requires_status"] = None
        by_id["R030"]["notes"] = (by_id["R030"].get("notes") or "").rstrip() + (
            " Prioritaet 86 gegen 85 bei R024 nach Kritikbefund: beide Routen haben"
            " denselben Schluessel (ZO09-D2-I-A, CORRECT). R030 greift im"
            " Foerderkontext (requires_status SUPPORT_FOCUS), R024 sonst - ohne"
            " Prioritaetsunterschied entschiede die Sortierung nach route_id.")
        log.append("Befund: R024/R030 Prioritaeten getrennt (86 gegen 85)")

    # ---- Befund 4 (FEHLER): R031 fuehrte auf 46+38 als Kontrastseite. Unter
    # der operandensymmetrischen Regel traegt 46+38 NEAR_ROUND_NUMBER; der
    # Kontrast traegt jetzt COMPENSATION, und die saubere Kontrastseite ist
    # ZO07-D2-S-D (47+35).
    if "R031" in by_id:
        by_id["R031"]["target_task"] = "ZO07-D2-S-D"
        by_id["R031"]["notes"] = (by_id["R031"].get("notes") or "").rstrip() + (
            " Nach Kritikbefund 4 auf ZO07-D2-S-D umgelenkt: 46+38 traegt unter der"
            " operandensymmetrischen NEAR_ROUND_NUMBER-Regel selbst einen Anker (38"
            " ist 2 von 40) und ist damit keine saubere Kontrastseite. Der Kontrast"
            " laeuft jetzt ueber COMPENSATION - §71 nennt fuer die erfolgreiche Seite"
            " ausdruecklich COMPENSATION_AVAILABLE.")
        log.append("Befund 4: R031 auf ZO07-D2-S-D umgelenkt")

    # ---- Befund 1 (BLOCKER): die Rueckwaertsschritte nach §69 muessen auf das
    # Item zielen, das Buendelung tatsaechlich messen kann - also auf das
    # Fuenferitem, nicht auf das ziffernablesbare Zehneritem.
    for route_id in ("R005", "R022"):
        if route_id in by_id and by_id[route_id].get("target_task") in (
                "ZO06-1-D1-ACTION-A", "ZO06-1-D1-ACTION-B"):
            by_id[route_id]["target_task"] = "ZO06-1-D1-ACTION-A"
            by_id[route_id]["notes"] = (by_id[route_id].get("notes") or "").rstrip() + (
                " Ziel ist das Fuenferbuendelitem: das Zehneritem ist durch"
                " Ziffernablesen loesbar und kann die Voraussetzung nicht messen"
                " (Kritikbefund 1).")
    log.append("Befund 1: Voraussetzungsrouten auf das Fuenferbuendelitem gerichtet")

    data["_comment"] = data["_comment"] + [
        "",
        "KORREKTUREN AUS DER KRITIK: R024 und R030 hatten denselben Schlüssel aus",
        "source_task und condition; ohne Prioritätsunterschied hätte die Sortierung",
        "nach route_id entschieden. R031 zeigt jetzt auf die saubere Kontrastseite.",
        "Die Voraussetzungsrouten nach §69 zielen auf das Fünferbündelitem, weil das",
        "Zehnerbündelitem durch Ziffernablesen lösbar ist.",
    ]
    save("task_routes.json", data)
    return log


# ------------------------------------------------------------------ Familien


def fix_families():
    data = load("task_families.json")
    by_id = {f["task_family_id"]: f for f in data["task_families"]}
    log = []

    if "FAM_ZO06_1_D1_BUNDLING" in by_id:
        f = by_id["FAM_ZO06_1_D1_BUNDLING"]
        f["family_type"] = "CONTRAST_ITEM"
        f["name"] = "ZO06.1 D1 Bündeln: Fünfer gegen Zehner"
        f["diagnostic_purpose"] = (
            "Unterscheidet Bündeln von Ziffernablesen. Beide Items zeigen 13 Würfel;"
            " nur die Bündelungsgröße variiert (§116). Beim Zehneritem stimmt die"
            " Antwort zufällig mit den Ziffern von 13 überein, beim Fünferitem nicht."
            " Gelingt nur das Zehneritem, spricht das für Ablesen statt Bündeln.")
        f["notes"] = ("Korrektur nach Kritikbefund 1. Die vorherige Fassung führte zwei"
                      " Zehnerbündelitems (13 und 27), deren Antworten beide in den"
                      " Ziffern der genannten Zahl standen - die Familie konnte ihre"
                      " Zielkompetenz ZO06_1_BUNDLING nicht messen.")
        log.append("Befund 1: FAM_ZO06_1_D1_BUNDLING auf Fünfer/Zehner-Kontrast umgestellt")

    if "FAM_ZO07_D2_TWO_DIGIT" in by_id:
        f = by_id["FAM_ZO07_D2_TWO_DIGIT"]
        f["diagnostic_purpose"] = (
            "Prüfen, ob der Erfolg bei zweistelliger Addition davon abhängt, ob der"
            " Ausgleich in der natürlichen Richtung möglich ist (COMPENSATION), also"
            " ob der ERSTE Summand nahe an einer runden Zahl liegt. §52 ausdrücklich:"
            " nicht automatisch 'Addition sicher/unsicher'.")
        f["notes"] = (
            "38+27 und 39+24 mit COMPENSATION, 46+38 und 47+35 ohne. Kompetenz,"
            " Schwierigkeit (D2), Darstellung und Bedienform sind konstant."
            " Korrektur nach Kritikbefund 4: der Kontrast lief vorher über"
            " NEAR_ROUND_NUMBER, aber unter der operandensymmetrischen Regel trägt"
            " 46+38 selbst einen Anker (38 ist 2 von 40). §71 nennt für die"
            " erfolgreiche Seite ausdrücklich COMPENSATION_AVAILABLE - das ist das"
            " tragfähige Kontrastmerkmal.")
        log.append("Befund 4: FAM_ZO07_D2_TWO_DIGIT kontrastiert über COMPENSATION")

    if "ZO07-CONTRAST-01" in by_id:
        f = by_id["ZO07-CONTRAST-01"]
        f["notes"] = (f.get("notes") or "").rstrip() + (
            " Korrektur nach Kritikbefund 4: das Kontrastmerkmal ist COMPENSATION,"
            " nicht NEAR_ROUND_NUMBER. Unter der operandensymmetrischen Regel trägt"
            " auch 37+28 einen Anker (28 ist 2 von 30), obwohl §71 das Item der"
            " erfolglosen Seite zuordnet - diese Abweichung ist als F-25 gemeldet."
            " COMPENSATION trennt die vier Items so, wie §71 sie gruppiert.")

    if "FAM_ZO06_D3_ZERO" in by_id:
        f = by_id["FAM_ZO06_D3_ZERO"]
        f["family_type"] = "CONTRAST_ITEM"
        f["diagnostic_purpose"] = (
            "Trennt die unbesetzte Stelle (ZO06.6) von der Stellenwertzerlegung"
            " allgemein (ZO06.5). 508 und 704 tragen eine Null an der Zehnerstelle,"
            " 538 nicht. Gelingt 538 und misslingen 508 und 704, liegt der Fehler an"
            " der unbesetzten Stelle.")
        f["notes"] = ((f.get("notes") or "").rstrip() + " Korrektur nach Kritikbefund"
                      " 10: die Familie konnte den Fehler replizieren, aber nicht"
                      " kontrastieren, weil beide Mitglieder eine Null trugen."
                      " ZO06-D3-S-C (538) ist als nullfreies Kontrollitem auf"
                      " derselben Stufe ergänzt (§116).")
        log.append("Befund 10: FAM_ZO06_D3_ZERO als CONTRAST_ITEM mit nullfreiem Partner")

    save("task_families.json", data)
    return log


def main():
    print("AUFGABEN")
    for line in fix_tasks():
        print(f"  {line}")
    print("\nRELATIONEN")
    for line in fix_relations():
        print(f"  {line}")
    print("\nROUTEN")
    for line in fix_routes():
        print(f"  {line}")
    print("\nFAMILIEN")
    for line in fix_families():
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
