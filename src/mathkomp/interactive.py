"""Interaktiver Durchlauf: die Schueler:innenansicht aus §105 auf der Konsole.

§105 nennt vier Schritte - Aufgabe, Interaktion, Antwort, Feedback / naechste
Aufgabe. Genau diese Schleife steht hier, mehr nicht ("keine komplexen
Dashboards notwendig").

Alles Diagnostische - Fehlercodes, Statuswechsel, Hypothesen - gehoert nach
§106 in die Lehrkraftansicht und liegt deshalb hinter --diagnose. §32 verbietet
ausdruecklich, einer Schueler:in eine Eigenschaft zuzuschreiben; eine waehrend
der Bearbeitung eingeblendete Hypothese waere genau das.

Zwei Eigenheiten dieser Oberflaeche sind nicht Bequemlichkeit, sondern
Vorschrift:

* §42 verlangt fuer Zaehlitems ausdruecklich, Klickreihenfolge, ausgelassene
  Objekte und doppelte Klicks zu speichern. Wer nur die Endzahl abfragt, kann
  ERR_OMISSION und ERR_DOUBLE_COUNT nie beobachten - die Fehlercodes existierten
  dann nur in der Simulation. Deshalb wird die Klickfolge eigens erfragt.
* §62 sagt zweierlei: "Zeit speichern" - und "langsam = schwache Kompetenz ist
  nicht zulaessig". Die Zeit wird deshalb gemessen und nach §60 als Rohdatum
  abgelegt, aber von nichts ausgewertet. Der Sperrschluessel
  evidence.time_seconds_used_for_inference steht auf false, eine Pruefregel
  haelt ihn dort. Nur speichern waere zu wenig, nur messen zu viel.

Und eine ist §3: das System trifft keine endgueltige Entscheidung. Der Befehl
:weiter uebergeht den Vorschlag und nimmt die naechstbeste Alternative aus dem
Entscheidungsprotokoll - die Lehrkraft darf die Auswahl uebersteuern.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Callable

from . import attempts, renderer, teacher
from .attempts import Submission
from .clock import Clock
from .config import Config
from .session import Session

#: Befehle statt einer Antwort. Fuehrender Doppelpunkt, damit sie nie mit einer
#: Antwort verwechselt werden koennen - "nein" ist bei ZP05-D1-A eine Antwort.
HELP = """  Befehle
    :hilfe     diese Uebersicht
    :warum     warum das System gerade diese Aufgabe vorschlaegt (§89)
    :stand     Lehrkraftansicht zum aktuellen Stand (§106)
    :stuetze   die naechste Antwort als 'mit Unterstuetzung geloest' erfassen (§33)
    :weiter    diesen Vorschlag uebergehen, naechstbeste Aufgabe nehmen (§3)
    :ende      Sitzung beenden

  Antwortformen
    Zahl              12
    Zahlenfolge       12 13 14        (Leerzeichen oder Komma)
    Auswahl           die Nummer der Option, oder ihren Text
    Klickfolge        1 2 3 ...       (leer = alle der Reihe nach)
"""


class _Command(Exception):
    """Statt einer Antwort wurde ein Befehl eingegeben."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


class _Abort(Exception):
    """Eingabe abgebrochen (Ctrl-C, Ctrl-D)."""


# ------------------------------------------------------------------ Eingabe


def _read(read: Callable[[str], str], prompt: str, allow_commands: bool = True) -> str:
    try:
        line = read(prompt)
    except (EOFError, KeyboardInterrupt):
        raise _Abort from None
    line = line.strip()
    if allow_commands and line.startswith(":"):
        raise _Command(line.lower())
    return line


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[,;\s]+", text.strip()) if t]


def _num(token: str) -> Any:
    """Zahl aus einer Eingabe. Nicht-Zahlen bleiben Text - eine unsinnige
    Antwort ist eine Antwort und muss erfassbar bleiben, nicht abgewiesen."""
    try:
        value = float(token.replace(",", "."))
    except ValueError:
        return token
    return int(value) if value.is_integer() else value


def _option(spec: dict, token: str) -> Any:
    """Optionsnummer oder Optionstext auf den Optionswert abbilden."""
    options = spec["interaction"].get("options") or []
    if token.isdigit() and 1 <= int(token) <= len(options):
        return options[int(token) - 1]
    for option in options:
        if str(option).strip().lower() == token.lower():
            return option
    return token  # unbekannte Eingabe: als falsche Antwort erfassen (§59)


# ------------------------------------------------------------- Antwortform


def _hint(task: dict, spec: dict, correct_keys: list[str]) -> str:
    """Welche Form die Antwort haben muss. Die Form, nicht die Antwort -
    render_text nennt bei ENTER aus demselben Grund schon 'NUMBER x1'."""
    rule, mode = task["scoring_rule"], task["interaction_mode"]
    if mode == "SELECT":
        n = len(spec["interaction"].get("options") or [])
        if rule == "SELECT_MULTIPLE":
            return f"mehrere Nummern aus 1-{n}"
        return f"Nummer 1-{n}"
    if rule in ("SEQUENCE_EXACT", "SET_EXACT"):
        return "Zahlenfolge"
    if rule == "GROUP_PARTITION":
        return " und ".join(correct_keys)
    if rule == "PLACED_OBJECT_COUNT":
        return "Anzahl gelegter Objekte"
    if rule == "INTERACTION_COUNT":
        return "Anzahl der Klicks"
    if rule == "EXPRESSION_EQUIVALENT":
        return "Rechnung, z.B. 50+35"
    if rule == "ANY_OF_ACCEPTED":
        return "Zerlegung, z.B. 30+7"
    return "Zahl"


def collect(task: dict, spec: dict, read: Callable[[str], str]) -> tuple[Any, list[dict]]:
    """Antwort und Interaktionsereignisse einsammeln (§60/§61).

    Gibt (answer, events) in genau der Form zurueck, die scoring.score und
    scoring.classify erwarten - die Oberflaeche baut die Abgabe, die Engine
    bewertet sie. Wirft _Command, wenn ein Befehl eingegeben wurde.
    """
    payload = json.loads(task["task_payload"]) if isinstance(task["task_payload"], str) \
        else (task["task_payload"] or {})
    correct = json.loads(task["correct_answer"]) if isinstance(task["correct_answer"], str) \
        else task["correct_answer"]
    rule, mode = task["scoring_rule"], task["interaction_mode"]
    keys = [k for k, v in correct.items() if isinstance(v, (int, float))]
    events: list[dict] = []

    # §42: bei Zaehlitems zuerst die Klickfolge, dann die genannte Zahl.
    if mode == "CLICK_SEQUENCE" and payload.get("objects"):
        total = payload["objects"]
        line = _read(read, f"  Klickfolge (1-{total}, leer = alle der Reihe nach): ")
        order = _tokens(line) or [str(i + 1) for i in range(total)]
        events = [{"event_type": "CLICK", "object_id": f"obj{t}"} for t in order]
        answer = _num(_read(read, "  Genannte Gesamtzahl: ", allow_commands=False))
        events.append({"event_type": "SUBMIT"})
        return answer, events

    line = _read(read, f"  Antwort ({_hint(task, spec, keys)}): ")
    tokens = _tokens(line)

    if rule == "SELECT_MULTIPLE":
        answer: Any = [_option(spec, t) for t in tokens]
    elif rule in ("SELECT_ONE", "BOOLEAN"):
        answer = _option(spec, line)
    elif rule in ("SEQUENCE_EXACT", "SET_EXACT"):
        answer = [_num(t) for t in tokens]
    elif rule in ("ANY_OF_ACCEPTED", "EXPRESSION_EQUIVALENT"):
        answer = line
    elif rule == "INTERACTION_COUNT":
        count = _num(line)
        answer = {"interactions": count}
        if isinstance(count, int):
            events = [{"event_type": "CLICK", "object_id": f"obj{i + 1}"} for i in range(count)]
    elif rule == "PLACED_OBJECT_COUNT":
        answer = {"placed": _num(line)}
        events = [{"event_type": "DRAG", "object_id": "obj1"},
                  {"event_type": "DROP", "object_id": "obj1"}]
    elif rule == "GROUP_PARTITION":
        answer = {k: _num(t) for k, t in zip(keys, tokens)}
    else:
        answer = _num(line)

    if mode == "SELECT":
        events.append({"event_type": "SELECT", "object_id": "option"})
    events.append({"event_type": "SUBMIT"})
    return answer, events


# --------------------------------------------------------------- Rueckmeldung


def _feedback(turn, task: dict, show_solution: bool, diagnose: bool) -> list[str]:
    """§105 'Feedback'. Ohne --loesung nur richtig / nicht richtig.

    Ob eine Schueler:in die richtige Loesung sofort sehen soll, ist eine
    fachdidaktische Entscheidung; §1 verbietet, sie hier eigenmaechtig zu
    treffen. Voreinstellung ist deshalb die zurueckhaltende.
    """
    out = ["  " + ("-> richtig" if turn.is_correct else "-> nicht richtig")]
    if show_solution and not turn.is_correct:
        correct = json.loads(task["correct_answer"]) if isinstance(task["correct_answer"], str) \
            else task["correct_answer"]
        out.append(f"     richtig waere: {_render_solution(correct)}")

    if not diagnose:
        return out

    if turn.error_codes:
        out.append(f"     [§59] Beobachtung   {', '.join(turn.error_codes)}")
    for competency, before, after in turn.state_changes:
        out.append(f"     [§63] Status        {competency}: {before or '-'} -> {after}")
    for action in turn.hypothesis_actions:
        out.append(f"     [§64] Hypothese     {action.action} {action.hypothesis_type}"
                   f" ({action.target_construct})")
    for transition in turn.transitions:
        out.append(f"     [§38] Uebergang     {transition.competency_id}:"
                   f" {transition.to_status} ({transition.reason})")
    return out


def _render_solution(correct: dict) -> str:
    for key in ("value", "selection", "sequence", "expression"):
        if key in correct:
            value = correct[key]
            return ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
    if "accepted" in correct:
        return " oder ".join(str(v) for v in correct["accepted"])
    return ", ".join(f"{k}={v}" for k, v in correct.items())


# ------------------------------------------------------------------- Ablauf


def _override(conn: sqlite3.Connection, decision, alternative: dict) -> None:
    """§3 Uebersteuerung, protokolliert nach §89.

    next_task() hat die Zeile in routing_decisions bereits geschrieben, bevor
    die Lehrkraft den Vorschlag uebergehen kann. Wuerde hier nur das Objekt im
    Speicher geaendert, naehme das Protokoll eine Aufgabe auf, die nie gestellt
    wurde - und §88 fragt ausdruecklich: "Warum hat das System diesen Pfad
    gewaehlt?" Eine Antwort, die die tatsaechlich gestellte Aufgabe verschweigt,
    ist keine. Deshalb wird die bestehende Zeile korrigiert, statt eine zweite
    zu schreiben: es war eine Entscheidung, nur nicht die des Systems.
    """
    decision.selected_task = alternative["task_id"]
    decision.reason = alternative["reason"]
    decision.rule_triggered = "TEACHER_OVERRIDE"
    decision.confidence = "LOW"  # §3: die Begruendung stammt nicht mehr vom Score.
    decision.explanation = (
        f"Vorschlag uebergangen (§3). Stattdessen {alternative['task_id']},"
        f" Begruendung {alternative['reason']}, Score {alternative['score']}."
        " Die Auswahl stammt von der Lehrkraft, nicht vom System.")
    conn.execute(
        "UPDATE routing_decisions SET selected_task = ?, rule_triggered = ?, confidence = ?"
        " WHERE decision_id = ?",
        (decision.selected_task, "TEACHER_OVERRIDE", decision.confidence,
         decision.decision_id))


def run(conn: sqlite3.Connection, student_id: str, *, grade: int | None = None,
        focus: set[str] | None = None, diagnose: bool = False,
        show_solution: bool = False, max_tasks: int | None = None,
        read: Callable[[str], str] = input,
        write: Callable[[str], None] = print) -> int:
    """Die Schleife aus §105, angetrieben von §119/§120 in session.Session."""
    cfg, clock = Config(conn), Clock()
    session = Session(conn, student_id, clock, cfg, grade_reference=grade, focus=focus)

    done = conn.execute("SELECT COUNT(*) n FROM task_attempts WHERE student_id = ?",
                        (student_id,)).fetchone()["n"]
    write(f"Schueler:in {student_id}"
          + (f" - {done} frueherer Versuch{'e' if done != 1 else ''}" if done else " - neu")
          + (f", Fokus {', '.join(sorted(focus))}" if focus else ""))
    write(":hilfe zeigt die Befehle, :ende beendet.\n")

    skipped: set[str] = set()
    support_next = False
    answered = 0
    #: Die von submit() bereits getroffene Auswahl (§120 Schritt 7). Ohne sie
    #: wuerde die Schleife next_task() ein zweites Mal aufrufen und damit eine
    #: identische zweite Zeile nach §89 schreiben - ein Protokoll, das zwei
    #: Entscheidungen behauptet, wo eine getroffen wurde. Entscheidung D-35.
    vorgemerkt = None

    while max_tasks is None or answered < max_tasks:
        if vorgemerkt is None:
            decision, spec = session.render_next()
        else:
            decision, vorgemerkt = vorgemerkt, None
            spec = (renderer.render(attempts.load_task(conn, decision.selected_task))
                    if decision.selected_task else None)

        # §3: uebergangene Vorschlaege durch die naechstbeste Alternative ersetzen.
        while spec is not None and decision.selected_task in skipped:
            nxt = next((a for a in decision.alternatives if a["task_id"] not in skipped), None)
            if nxt is None:
                write("  Keine weitere Alternative im Protokoll. Uebergehen aufgehoben.")
                skipped.clear()
                break
            _override(conn, decision, nxt)
            spec = renderer.render(attempts.load_task(conn, decision.selected_task))

        if spec is None:
            write(f"\nEnde: {decision.stop_reason}")
            write(f"  {decision.explanation}")
            break

        write("")
        write(renderer.render_text(spec))
        if diagnose:
            write(f"  [§89] {decision.reason} / {decision.rule_triggered}"
                  f" / Konfidenz {decision.confidence}")

        try:
            task = attempts.load_task(conn, decision.selected_task)
            if support_next:
                write("  (wird als 'mit Unterstuetzung' erfasst - §33)")
            begonnen = clock.now()
            answer, events = collect(task, spec, read)
            dauer = (clock.now() - begonnen).total_seconds()
        except _Abort:
            write("\nAbgebrochen.")
            break
        except _Command as cmd:
            action = _handle(cmd.text, conn, student_id, cfg, clock, decision, write)
            if action == "quit":
                break
            if action == "skip":
                # Uebergehen verlangt eine neue Auswahl - also auch eine neue
                # Zeile im Protokoll. Alle uebrigen Befehle aendern nichts an
                # der Entscheidung; sie wird weiterverwendet statt neu gefaellt.
                skipped.add(decision.selected_task)
            else:
                if action == "support":
                    support_next = not support_next
                vorgemerkt = decision
            continue

        turn = session.submit(Submission(
            task_id=decision.selected_task, answer=answer, events=events,
            # §62 sagt zweierlei, und beides gilt: "Zeit speichern." - und
            # "langsam = schwache Kompetenz ist nicht zulaessig". §60 fuehrt
            # time_seconds unter den zu speichernden Rohdaten. Gespeichert wird
            # also, ausgewertet nicht: der Sperrschluessel
            # evidence.time_seconds_used_for_inference steht auf false und wird
            # von einer Pruefregel gehalten.
            time_seconds=round(dauer, 1),
            support_used=support_next,
            selected_by_reason=decision.reason, selected_by_rule=decision.rule_triggered))
        support_next = False
        answered += 1
        vorgemerkt = turn.next_decision
        conn.commit()

        for line in _feedback(turn, task, show_solution, diagnose):
            write(line)

    conn.commit()
    if answered:
        write(f"\n{answered} Aufgabe{'n' if answered != 1 else ''} bearbeitet."
              f" Auswertung:  python -m mathkomp student {student_id}")
    return 0


def _handle(text: str, conn: sqlite3.Connection, student_id: str, cfg: Config,
            clock: Clock, decision, write: Callable[[str], None]) -> str | None:
    if text in (":ende", ":quit", ":q"):
        return "quit"
    if text in (":weiter", ":skip"):
        return "skip"
    if text in (":stuetze", ":hilfe-genutzt"):
        return "support"
    if text in (":hilfe", ":h", ":help", ":?"):
        write(HELP)
    elif text in (":warum", ":why"):
        write(f"  {decision.explanation}")
        for alt in decision.alternatives[1:]:
            write(f"    Alternative  {alt['task_id']:<24} {alt['score']:>6.2f}  {alt['reason']}")
    elif text in (":stand", ":status"):
        write(teacher.render(teacher.report(conn, student_id, cfg, clock)))
    else:
        write(f"  Unbekannter Befehl {text}. :hilfe zeigt die Befehle.")
    return None
