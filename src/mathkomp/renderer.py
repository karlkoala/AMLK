"""Task Renderer (Sprint 4).

Erzeugt aus einer Aufgabe eine Darstellungsvorschrift. Bewusst kopflos: die
Funktion liefert ein Dictionary, das eine Web-, Tablet- oder Textoberflaeche
umsetzen kann. Damit sind Sprint 5 bis 12 ohne UI testbar.

§17 ist bindend: "Darstellung und Bedienform sind zwei unterschiedliche
Variablen." Die Vorschrift fuehrt beide getrennt - representation beschreibt,
was zu sehen ist, interaction beschreibt, wie geantwortet wird. Eine
Oberflaeche darf die beiden nicht zusammenziehen, sonst ist ein Unterschied
spaeter nicht mehr zuzuordnen (§32).

§113 ist bindend: ein Item ohne vollstaendige Angaben wird nicht ausgeliefert.
Der Renderer raet keine Distraktoren und keine Antwortmenge, er verweigert.
"""

from __future__ import annotations

import json
from typing import Any

from .scoring import UndeliverableTask

#: Welche Interaktionsereignisse (§61) die Oberflaeche je Bedienform senden muss.
#: §42 verlangt fuer Zaehlitems ausdruecklich Klickreihenfolge, ausgelassene
#: Objekte und doppelte Klicks - das ist nur aus einer CLICK-Folge mit
#: object_id rekonstruierbar.
REQUIRED_EVENTS = {
    "SELECT": ("SELECT", "DESELECT", "ANSWER_CHANGE", "SUBMIT"),
    "ENTER": ("ANSWER_CHANGE", "SUBMIT"),
    "DRAG": ("DRAG", "DROP", "ANSWER_CHANGE", "SUBMIT"),
    "SORT": ("DRAG", "DROP", "ANSWER_CHANGE", "SUBMIT"),
    "CLICK_SEQUENCE": ("CLICK", "SUBMIT"),
    "MANIPULATE": ("CLICK", "DRAG", "DROP", "SUBMIT"),
    "CONSTRUCT": ("CLICK", "DRAG", "DROP", "ANSWER_CHANGE", "SUBMIT"),
}

#: Bedienformen, fuer die die Seed-Aufgabenbank Items enthaelt. SORT und
#: CONSTRUCT stehen in §17, kommen aber in §42-57 nicht vor.
IMPLEMENTED_MODES = ("SELECT", "ENTER", "DRAG", "MANIPULATE", "CLICK_SEQUENCE")


def render(task: dict) -> dict:
    """Darstellungsvorschrift fuer ein Item.

    Raises:
        UndeliverableTask: wenn fachliche Angaben fehlen (§1, §113).
    """
    payload = json.loads(task["task_payload"]) if isinstance(task["task_payload"], str) \
        else dict(task["task_payload"])
    correct = json.loads(task["correct_answer"]) if isinstance(task["correct_answer"], str) \
        else task["correct_answer"]

    if payload.get("options_status") == "UNDEFINED":
        raise UndeliverableTask(
            f"{task['task_id']}: Auswahloptionen sind UNDEFINED. §113 verlangt eine"
            " vollstaendige Aufgabe; Distraktoren werden nicht geraten (F-17).")
    if isinstance(correct, dict) and correct.get("status") == "UNDEFINED":
        raise UndeliverableTask(
            f"{task['task_id']}: akzeptierte Antworten sind UNDEFINED. §49 verlangt"
            " mehrere zulaessige Antworten, §1 verbietet sie zu erfinden (F-18).")

    mode = task["interaction_mode"]
    builder = _BUILDERS.get(mode)
    if builder is None:
        raise UndeliverableTask(
            f"{task['task_id']}: Bedienform {mode} ist im MVP nicht implementiert"
            f" (implementiert: {', '.join(IMPLEMENTED_MODES)})")

    return {
        "task_id": task["task_id"],
        "prompt": task["task_prompt"],
        # §16 getrennt von §17.
        "representation": {
            "mode": task["representation_mode"],
            "stimulus": _stimulus(task, payload),
        },
        "interaction": {"mode": mode, **builder(task, payload, correct)},
        "required_events": list(REQUIRED_EVENTS[mode]),
        "support_available": bool(payload.get("support")),
        "meta": {
            "difficulty": task["internal_difficulty"],
            "purpose": task["task_purpose"],
            "calibration": task["calibration_status"],
        },
    }


def _stimulus(task: dict, payload: dict) -> dict:
    """Was die Oberflaeche zeigen muss, unabhaengig von der Bedienform.

    §9 verlangt, die Anordnung der Objekte als Aufgabenmerkmal zu fuehren:
    dieselbe Anzahl kann in einer Reihe gelingen und ungeordnet nicht. Die
    Anordnung wird deshalb an die Oberflaeche durchgereicht und nicht ihr
    ueberlassen.

    Zwei Formen sind zulaessig. Die Items aus §42-57 fuehren ihre Darstellung
    in flachen Schluesseln (objects, tens, array); das Zusatzpaket Klasse 5-10
    fuehrt sie in einem Objekt unter "figure". Der Renderer uebersetzt die
    eine nicht in die andere: eine Uebersetzung waere eine fachliche Deutung,
    und §17 verbietet ihm ohnehin, aus der Darstellung auf die Bedienform zu
    schliessen. Was er nicht kennt, reicht er unveraendert durch.
    """
    keys = ("figure",
            "objects", "arrangement", "structure", "heterogeneous", "movable",
            "signal_count", "presentation", "tens", "ones", "hundreds", "material",
            "field", "shown", "shown_structure", "array", "range", "marks",
            "given", "blanks", "direction", "start", "count", "number", "digit",
            # Ohne diese Schluessel ist das zugehoerige Bild nicht zeichenbar
            # und das Item damit nicht loesbar: "Welche Zahl zeigt die
            # Stellenwerttafel?" (ZO06-SUP-D1-I-A) braucht die Ziffern, nicht
            # nur die Materialangabe, und "Wie viele Punkte sind es
            # insgesamt?" (ZO09-D2-I-A) braucht die Information, dass das
            # Innere des Feldes verdeckt ist - genau darin besteht die
            # Aufgabe. In der Textausgabe fiel das nicht auf, weil dort
            # ohnehin niemand ein Bild sieht.
            "place_value_chart", "column_labels", "empty_tens_column", "asked_place",
            "interior_covered", "visible", "shown_decomposition", "notation",
            "loose_ones", "bundle_size", "decomposition_shown", "columns_hze",
            "operands", "operation", "given_fact", "target_calculation",
            "objects_available", "target_count", "objects_before", "objects_added",
            "objects_removed", "objects_first", "recipients", "per_group", "mode",
            "count_directions", "start_point_changed", "asked_unit", "whole",
            "known_part", "target", "decompose", "groups", "expected_pair",
            "intended_transformation", "signal", "columns", "word")
    return {k: payload[k] for k in keys if k in payload}


def _b_select(task: dict, payload: dict, correct: Any) -> dict:
    options = payload.get("options")
    if not options:
        raise UndeliverableTask(
            f"{task['task_id']}: Bedienform SELECT ohne Optionen (§113)")
    multiple = task["scoring_rule"] == "SELECT_MULTIPLE"
    return {"options": list(options), "multiple": multiple,
            "expected_selection_count": len(correct.get("selection", []))
            if multiple and isinstance(correct.get("selection"), list) else 1}


def _b_enter(task: dict, payload: dict, correct: Any) -> dict:
    if task["scoring_rule"] in ("SEQUENCE_EXACT", "SET_EXACT"):
        return {"input_type": "NUMBER_SEQUENCE",
                "fields": payload.get("blanks", len(correct.get("sequence", [])))}
    if task["scoring_rule"] == "EXPRESSION_EQUIVALENT":
        return {"input_type": "EXPRESSION", "fields": 1}
    if task["scoring_rule"] == "ANY_OF_ACCEPTED":
        # Zulaessig sind hier mehrere Schreibweisen, darunter Brueche wie 5/6.
        # Ein Zahlenfeld wuerde sie zurueckweisen und damit eine richtige
        # Antwort zu einer falschen machen - die Beobachtung waere dann ein
        # Artefakt der Oberflaeche und keine Beobachtung am Kind (§59).
        return {"input_type": "TEXT", "fields": 1}
    return {"input_type": "NUMBER", "fields": 1}


def _b_drag(task: dict, payload: dict, correct: Any) -> dict:
    if task["scoring_rule"] == "GROUP_PARTITION":
        return {"source_count": payload.get("objects"),
                "targets": payload.get("recipients") or "GROUPS_FREE",
                "target_group_size": payload.get("per_group"),
                "partition_mode": payload.get("mode")}
    figure = payload.get("figure") or {}
    if figure.get("type") == "NUMBER_LINE" and figure.get("place"):
        # Die Marke wird auf dem Zahlenstrahl abgelegt, nicht in einem Feld.
        # §16: die Skala gehoert zur Darstellung und steht in figure; hier
        # steht nur, worauf die Bedienung sie einrasten laesst.
        return {"input_type": "NUMBER_LINE_POSITION",
                "range": [figure.get("from"), figure.get("to")],
                "step": figure.get("step"), "targets": "NUMBER_LINE"}
    return {"source_count": payload.get("objects_available", payload.get("objects")),
            "targets": 1, "target_label": "Feld"}


def _b_manipulate(task: dict, payload: dict, correct: Any) -> dict:
    if task["scoring_rule"] == "GROUP_PARTITION":
        # Buendeln (§69, §92): loses Material wird zu Einheiten zusammengefasst.
        return {"objects": payload.get("loose_ones", payload.get("objects")),
                "bundle_size": payload.get("bundle_size"),
                "movable": True,
                "input_type": "PARTITION",
                "fields": sorted(k for k in correct if isinstance(correct[k], (int, float)))}
    return {"objects": payload.get("objects"),
            "movable": bool(payload.get("movable", True)),
            "input_type": "NUMBER"}


def _b_click_sequence(task: dict, payload: dict, correct: Any) -> dict:
    figure = payload.get("figure") or {}
    # Eine Figur mit anklickbaren Teilen (etwa ein Bruchstreifen) liefert die
    # Zahl der Ziele selbst. Sie wird nicht aus correct_answer abgeleitet -
    # dann waere die Loesung aus der Darstellungsvorschrift ablesbar.
    objects = payload.get("objects", payload.get("target_count"))
    if objects is None and figure.get("selectable"):
        objects = figure.get("parts")
    return {"objects": objects,
            "target_object": payload.get("target_object"),
            # §42: Klickreihenfolge, ausgelassene Objekte und doppelte Klicks.
            "record_object_ids": True,
            "input_type": "NUMBER" if payload.get("objects") else None}


_BUILDERS = {
    "SELECT": _b_select,
    "ENTER": _b_enter,
    "DRAG": _b_drag,
    "MANIPULATE": _b_manipulate,
    "CLICK_SEQUENCE": _b_click_sequence,
}


def render_text(spec: dict) -> str:
    """Textdarstellung fuer CLI und Simulation.

    §105: die Schueler:innenansicht ist im MVP bewusst einfach - Aufgabe,
    Interaktion, Antwort, Rueckmeldung.
    """
    lines = [f"[{spec['task_id']}]  {spec['meta']['difficulty']}"
             f" | {spec['representation']['mode']} | {spec['interaction']['mode']}",
             "", spec["prompt"]]
    stim = spec["representation"]["stimulus"]
    if stim:
        detail = ", ".join(f"{k}={v}" for k, v in stim.items())
        lines.append(f"  ({detail})")
    inter = spec["interaction"]
    if inter["mode"] == "SELECT":
        for i, option in enumerate(inter["options"], 1):
            lines.append(f"    {i}) {option}")
    elif inter["mode"] == "ENTER":
        lines.append(f"    Eingabe: {inter['input_type']} x{inter['fields']}")
    return "\n".join(lines)
