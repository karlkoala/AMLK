"""HTTP-Server fuer die Schueler:innenoberflaeche (``ui_schueler/``).

Die Analyseoberflaeche in ``server.py`` oeffnet die Datenbank ausdruecklich
schreibgeschuetzt: eine Betrachtung darf keine Diagnostik veraendern. Hier ist
es umgekehrt - dieser Server *fuehrt* die Sitzung, also schreibt er: Versuche,
Ereignisse, Evidenz, Zustaende, Hypothesen und nach §89 jede Routing-
Entscheidung. Beides in einem Prozess zu vereinen haette den Schreibschutz
dort aufgehoben; deshalb zwei Server, zwei Oberflaechen, zwei Verbindungen.

Was diese Oberflaeche zeigt und was nicht, steht nicht im Belieben des
Frontends:

* §105 nennt vier Schritte - Aufgabe, Interaktion, Antwort, Rueckmeldung.
  Mehr liefert ``/api/antwort`` nicht.
* §106 legt alles Diagnostische in die Lehrkraftansicht. Fehlercodes,
  Statuswechsel und Hypothesen verlassen diesen Server deshalb gar nicht
  erst - nicht versteckt im JSON, sondern ueberhaupt nicht. Wer sie sehen
  will, nimmt ``mathkomp student`` oder ``mathkomp ui``.
* §32 verbietet, einer Schueler:in eine Eigenschaft zuzuschreiben. Ein
  Fortschrittsbalken "Stellenwert: unsicher" waere genau das. Gezaehlt wird
  nur, was gearbeitet wurde.

Die Sitzung liegt im Serverprozess, nicht im Browser. Das ist kein
Bequemlichkeitsentscheid: ``Session.submit()`` liefert nach §120 Schritt 7 die
naechste Entscheidung bereits mit. Wuerde die Seite stattdessen nach jedem
Neuladen ``next_task()`` aufrufen, entstuenden zwei Zeilen in
``routing_decisions`` fuer eine gestellte Aufgabe - ein Protokoll, das eine
Entscheidung behauptet, die nie zu einer Aufgabe wurde (Entscheidung D-35).

Gebunden wird auf 127.0.0.1. Nur Standardbibliothek, wie das uebrige Projekt.
"""

from __future__ import annotations

import json
import mimetypes
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from . import attempts, renderer, routing, simulation
from .attempts import Submission
from .clock import Clock
from .config import Config
from .scoring import UndeliverableTask
from .server import ALLOWED_SUFFIXES
from .session import Session

UI_ROOT = Path(__file__).resolve().parents[2] / "ui_schueler"

#: §86: pseudonyme Kennung. Die Form wird erzwungen, damit niemand aus
#: Bequemlichkeit einen Klarnamen eintippt und das Feld ihn klaglos annimmt.
#: Ein Verbot, das nicht greift, ist keines.
STUDENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$")

#: Groesste zulaessige Anfrage. Eine Antwort ist eine Zahl, ein Wort oder eine
#: Klickfolge; alles darueber ist ein Fehler oder ein Angriff.
MAX_BODY = 64 * 1024


class Abgelehnt(Exception):
    """Fachlich oder formal unzulaessige Anfrage. Wird zu 400."""


@dataclass
class Lernsitzung:
    """Eine laufende Sitzung mit ihrer offenen Aufgabe."""
    session: Session
    #: Die bereits gefaellte, noch nicht gestellte Entscheidung (§120.7).
    offen: Any = None
    #: Beginn der Bearbeitung, fuer §60/§62 - gespeichert, nie ausgewertet.
    begonnen: Any = None
    #: §3: uebergangene Vorschlaege.
    uebergangen: set[str] = field(default_factory=set)
    #: §33: die naechste Antwort als "mit Unterstuetzung" erfassen.
    stuetze: bool = False


# ------------------------------------------------------------------- Endpunkte


class Lernlauf:
    """Die Sitzungen dieses Serverlaufs.

    Eine einzige Schreibverbindung, ein Schloss darum. SQLite erlaubt zwar
    mehrere Verbindungen, aber die Diagnostik ist zustandsbehaftet: zwei
    gleichzeitige Abgaben derselben Schueler:in wuerden Evidenz in einer
    Reihenfolge schreiben, die keine Sitzung je hatte.
    """

    def __init__(self, db_path: Path, zeige_loesung: bool = False) -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cfg = Config(self.conn)
        self.clock = Clock()
        self.zeige_loesung = zeige_loesung
        self.sitzungen: dict[str, Lernsitzung] = {}
        self.lock = threading.Lock()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    # ---------------------------------------------------------------- Katalog

    def katalog(self) -> dict:
        """Was die Oberflaeche beim Start braucht."""
        stufen = [
            dict(r) for r in self.conn.execute(
                "SELECT grade_reference_min AS stufe, COUNT(*) AS aufgaben FROM tasks"
                " WHERE grade_reference_min IS NOT NULL"
                " GROUP BY grade_reference_min ORDER BY grade_reference_min")
        ]
        bekannt = [
            dict(r) for r in self.conn.execute(
                "SELECT s.student_id, s.grade_reference,"
                " (SELECT COUNT(*) FROM task_attempts a WHERE a.student_id = s.student_id)"
                " AS bearbeitet FROM students s ORDER BY s.student_id")
        ]
        return {
            "klassenstufen": list(range(1, 11)),
            "aufgaben_je_stufe": stufen,
            "schueler": bekannt,
            "loesung_sichtbar": self.zeige_loesung,
            # §105: die Oberflaeche sagt selbst, was sie nicht zeigt.
            "hinweis": "Fehlercodes, Kompetenzstände und Hypothesen gehören nach"
                       " §106 in die Lehrkraftansicht und werden hier nicht"
                       " übertragen.",
        }

    # ---------------------------------------------------------------- Sitzung

    def sitzung_starten(self, body: dict) -> dict:
        student_id = str(body.get("student_id", "")).strip()
        if not STUDENT_ID.match(student_id):
            raise Abgelehnt(
                "Kennung muss 2 bis 32 Zeichen aus Buchstaben, Ziffern, '-' und '_'"
                " haben. §86: pseudonym, kein Klarname.")
        stufe = body.get("klassenstufe")
        if stufe is not None:
            if not isinstance(stufe, int) or not 1 <= stufe <= 10:
                raise Abgelehnt("Klassenstufe muss zwischen 1 und 10 liegen.")

        vorhanden = self.conn.execute(
            "SELECT grade_reference FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
        session = Session(self.conn, student_id, self.clock, self.cfg,
                          grade_reference=stufe)
        # §94 fuehrt die Klassenstufe als Referenz. Sie darf sich aendern -
        # aber nur, wenn jemand sie ausdruecklich angibt. Eine schon erfasste
        # Stufe wird nicht stillschweigend ueberschrieben.
        if vorhanden is not None and stufe is not None \
                and vorhanden["grade_reference"] != stufe:
            self.conn.execute(
                "UPDATE students SET grade_reference = ? WHERE student_id = ?",
                (stufe, student_id))
        self.conn.commit()

        self.sitzungen[student_id] = Lernsitzung(session=session)
        return {"student_id": student_id,
                "klassenstufe": routing.student_grade(self.conn, student_id),
                "bearbeitet": self._bearbeitet(student_id),
                "fortsetzung": vorhanden is not None}

    def _sitzung(self, student_id: str) -> Lernsitzung:
        lauf = self.sitzungen.get(student_id)
        if lauf is None:
            raise Abgelehnt("Keine laufende Sitzung. Zuerst /api/sitzung aufrufen.")
        return lauf

    def _bearbeitet(self, student_id: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) n FROM task_attempts WHERE student_id = ?",
            (student_id,)).fetchone()["n"]

    # ---------------------------------------------------------------- Aufgabe

    def aufgabe(self, body: dict) -> dict:
        lauf = self._sitzung(self._student(body))
        entscheidung, spec = self._naechste(lauf)
        if spec is None:
            return {"ende": {"grund": entscheidung.stop_reason,
                             "erklaerung": entscheidung.explanation,
                             "bearbeitet": self._bearbeitet(lauf.session.student_id)}}
        lauf.begonnen = self.clock.now()
        task = attempts.load_task(self.conn, entscheidung.selected_task)
        return {
            "aufgabe": spec,
            "antwortform": _antwortform(task, spec),
            "stuetze": lauf.stuetze,
            "bearbeitet": self._bearbeitet(lauf.session.student_id),
            # §89/§88: "Warum diese Aufgabe?" muss beantwortbar sein - auch
            # fuer die Schueler:in. Die Begruendung nennt den Grund der
            # Auswahl, keinen Zustand und keine Hypothese.
            "warum": {"grund": entscheidung.reason,
                      "erklaerung": entscheidung.explanation},
        }

    def _naechste(self, lauf: Lernsitzung):
        """Die naechste Aufgabe, ohne eine zweite Entscheidung zu erzeugen."""
        while True:
            if lauf.offen is None:
                entscheidung, spec = lauf.session.render_next()
            else:
                entscheidung, lauf.offen = lauf.offen, None
                spec = None
                if entscheidung.selected_task:
                    spec = self._render(entscheidung.selected_task)

            if spec is None:
                lauf.offen = entscheidung
                return entscheidung, None

            # §3: Vorschlaege, die uebergangen wurden, durch die naechstbeste
            # Alternative aus dem Protokoll ersetzen.
            while entscheidung.selected_task in lauf.uebergangen:
                naechste = next((a for a in entscheidung.alternatives
                                 if a["task_id"] not in lauf.uebergangen), None)
                if naechste is None:
                    lauf.uebergangen.clear()
                    break
                _uebersteuern(self.conn, entscheidung, naechste)
                spec = self._render(entscheidung.selected_task)
            lauf.offen = entscheidung
            return entscheidung, spec

    def _render(self, task_id: str) -> dict:
        return renderer.render(attempts.load_task(self.conn, task_id))

    # ---------------------------------------------------------------- Antwort

    def antwort(self, body: dict) -> dict:
        lauf = self._sitzung(self._student(body))
        if lauf.offen is None or lauf.offen.selected_task is None:
            raise Abgelehnt("Keine offene Aufgabe. Zuerst /api/aufgabe aufrufen.")
        entscheidung = lauf.offen
        task = attempts.load_task(self.conn, entscheidung.selected_task)

        if "answer" not in body:
            raise Abgelehnt("Feld 'answer' fehlt.")
        ereignisse = _ereignisse(body.get("events"))
        dauer = None
        if lauf.begonnen is not None:
            dauer = round((self.clock.now() - lauf.begonnen).total_seconds(), 1)

        turn = lauf.session.submit(Submission(
            task_id=entscheidung.selected_task,
            answer=body["answer"],
            events=ereignisse,
            # §62 sagt zweierlei, und beides gilt: speichern ja, auswerten
            # nein. Der Sperrschluessel evidence.time_seconds_used_for_inference
            # steht auf false, eine Pruefregel haelt ihn dort.
            time_seconds=dauer,
            support_used=lauf.stuetze,
            selected_by_reason=entscheidung.reason,
            selected_by_rule=entscheidung.rule_triggered))
        self.conn.commit()

        lauf.offen = turn.next_decision
        lauf.begonnen = None
        lauf.stuetze = False

        # §105 Schritt 4. Bewusst nur das: kein Fehlercode (§59 ist eine
        # Beobachtung fuer die Lehrkraft, keine Rueckmeldung an das Kind),
        # kein Statuswechsel, keine Hypothese (§106).
        antwort: dict[str, Any] = {
            "richtig": turn.is_correct,
            "bearbeitet": self._bearbeitet(lauf.session.student_id),
        }
        if self.zeige_loesung and not turn.is_correct:
            antwort["loesung"] = _loesung(task)
        return antwort

    # ------------------------------------------------------------ Simulation

    def vorschlag(self, body: dict) -> dict:
        """Eine Antwort vorschlagen, ohne sie abzugeben (§123 Simulation).

        Die vorgeschlagene Antwort geht denselben Weg wie jede andere: sie
        wird in das Eingabefeld gesetzt und muss abgeschickt werden. Eine
        Abkuerzung am Scoring vorbei wuerde Versuche erzeugen, die nie
        bewertet wurden - und §123 prueft die Engine, nicht eine zweite,
        heimliche Engine daneben.
        """
        lauf = self._sitzung(self._student(body))
        if lauf.offen is None or lauf.offen.selected_task is None:
            raise Abgelehnt("Keine offene Aufgabe.")
        task = attempts.load_task(self.conn, lauf.offen.selected_task)
        art = body.get("art", "richtig")
        if art not in ("richtig", "falsch"):
            raise Abgelehnt("art muss 'richtig' oder 'falsch' sein.")
        if art == "richtig":
            antwort = simulation.correct_answer_for(task)
        else:
            antwort = simulation.plausible_wrong_answer(
                self.conn, task, attempts.task_features(self.conn, task["task_id"]))
        spec = self._render(task["task_id"])
        return {"answer": antwort,
                "events": simulation.events_for(task, spec, art == "richtig")}

    # --------------------------------------------------------------- Befehle

    def uebergehen(self, body: dict) -> dict:
        """§3: den Vorschlag uebergehen. Das System entscheidet nicht endgueltig."""
        lauf = self._sitzung(self._student(body))
        if lauf.offen is None or lauf.offen.selected_task is None:
            raise Abgelehnt("Keine offene Aufgabe.")
        lauf.uebergangen.add(lauf.offen.selected_task)
        lauf.offen = None
        self.conn.commit()
        return {"uebergangen": sorted(lauf.uebergangen)}

    def stuetze(self, body: dict) -> dict:
        """§33: die naechste Antwort als 'mit Unterstuetzung geloest' erfassen."""
        lauf = self._sitzung(self._student(body))
        lauf.stuetze = bool(body.get("an", not lauf.stuetze))
        return {"stuetze": lauf.stuetze}

    def beenden(self, body: dict) -> dict:
        student_id = self._student(body)
        self.sitzungen.pop(student_id, None)
        self.conn.commit()
        return {"bearbeitet": self._bearbeitet(student_id),
                "auswertung": f"mathkomp student {student_id}"}

    @staticmethod
    def _student(body: dict) -> str:
        student_id = str(body.get("student_id", "")).strip()
        if not STUDENT_ID.match(student_id):
            raise Abgelehnt("Ungültige Kennung.")
        return student_id


# -------------------------------------------------------------------- Helfer


def _uebersteuern(conn: sqlite3.Connection, entscheidung, alternative: dict) -> None:
    """§3 Uebersteuerung, protokolliert nach §89.

    Wortgleich zum Terminal (``interactive._override``): next_task() hat die
    Zeile bereits geschrieben, bevor jemand den Vorschlag uebergehen konnte.
    Eine zweite Zeile wuerde zwei Entscheidungen behaupten, wo eine getroffen
    wurde; deshalb wird die bestehende korrigiert.
    """
    entscheidung.selected_task = alternative["task_id"]
    entscheidung.reason = alternative["reason"]
    entscheidung.rule_triggered = "TEACHER_OVERRIDE"
    entscheidung.confidence = "LOW"
    entscheidung.explanation = (
        f"Vorschlag uebergangen (§3). Stattdessen {alternative['task_id']},"
        f" Begruendung {alternative['reason']}, Score {alternative['score']}."
        " Die Auswahl stammt von der Lehrkraft, nicht vom System.")
    conn.execute(
        "UPDATE routing_decisions SET selected_task = ?, rule_triggered = ?,"
        " confidence = ? WHERE decision_id = ?",
        (entscheidung.selected_task, "TEACHER_OVERRIDE", entscheidung.confidence,
         entscheidung.decision_id))


def _ereignisse(roh: Any) -> list[dict]:
    """Interaktionsereignisse pruefen (§61).

    Ungepruefte Ereignisse landen direkt in ``interaction_events`` und damit
    in der Grundlage fuer ERR_OMISSION und ERR_DOUBLE_COUNT (§42). Ein Eintrag
    ohne event_type wuerde den Import abbrechen, einer mit falschem Typ eine
    Beobachtung vortaeuschen.
    """
    if roh is None:
        return []
    if not isinstance(roh, list):
        raise Abgelehnt("events muss eine Liste sein.")
    if len(roh) > 2000:
        raise Abgelehnt("Zu viele Ereignisse.")
    geprueft = []
    for e in roh:
        if not isinstance(e, dict) or not isinstance(e.get("event_type"), str):
            raise Abgelehnt("Jedes Ereignis braucht ein event_type.")
        geprueft.append({"event_type": e["event_type"],
                         "object_id": e.get("object_id"),
                         "value": e.get("value")})
    return geprueft


def _antwortform(task: dict, spec: dict) -> dict:
    """Welche Form die Antwort haben muss - die Form, nicht die Antwort.

    Die Oberflaeche baut daraus ihr Eingabefeld. ``renderer.render`` nennt bei
    ENTER aus demselben Grund schon ``input_type``; hier kommt die Regel
    dazu, nach der bewertet wird, weil sie die Form mitbestimmt (etwa
    GROUP_PARTITION mit mehreren Feldern).
    """
    correct = json.loads(task["correct_answer"]) if isinstance(task["correct_answer"], str) \
        else task["correct_answer"]
    form = {"rule": task["scoring_rule"], "felder": None}
    if task["scoring_rule"] == "GROUP_PARTITION":
        # Die Feldnamen stehen in der Musterantwort, die Werte bleiben hier.
        form["felder"] = sorted(k for k, v in correct.items()
                                if isinstance(v, (int, float)))
    elif task["scoring_rule"] in ("SEQUENCE_EXACT", "SET_EXACT"):
        form["felder"] = spec["interaction"].get("fields")
    return form


def _loesung(task: dict) -> str:
    """Die richtige Loesung als Text - nur wenn der Server mit --loesung laeuft.

    Ob eine Schueler:in die Loesung sofort sehen soll, ist eine
    fachdidaktische Entscheidung. §1 verbietet, sie hier eigenmaechtig zu
    treffen; die Voreinstellung ist deshalb die zurueckhaltende.
    """
    correct = json.loads(task["correct_answer"]) if isinstance(task["correct_answer"], str) \
        else task["correct_answer"]
    for key in ("value", "selection", "sequence", "expression"):
        if key in correct:
            wert = correct[key]
            return ", ".join(str(v) for v in wert) if isinstance(wert, list) else str(wert)
    if "accepted" in correct:
        return " oder ".join(str(v) for v in correct["accepted"])
    return ", ".join(f"{k}={v}" for k, v in correct.items())


# --------------------------------------------------------------------- HTTP


class Handler(BaseHTTPRequestHandler):
    server_version = "mathkomp-lernen"
    sys_version = ""

    lauf: Lernlauf
    ui_root: Path

    # ------------------------------------------------------------ Antworten

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
            " img-src 'self' data:; connect-src 'self'; base-uri 'none';"
            " form-action 'none'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message}, status)

    # ------------------------------------------------------------- Routing

    def do_GET(self) -> None:  # noqa: N802 - von BaseHTTPRequestHandler vorgegeben
        zerlegt = urlparse(self.path)
        path = unquote(zerlegt.path)
        try:
            if path == "/api/katalog":
                with self.lauf.lock:
                    return self._json(self.lauf.katalog())
            if path.startswith("/api/"):
                return self._error(
                    405, "Dieser Endpunkt schreibt und verlangt deshalb POST.")
            return self._static(path)
        except BrokenPipeError:
            pass
        except Exception as exc:  # pragma: no cover - Notbremse
            self._error(500, f"{type(exc).__name__}: {exc}")

    do_HEAD = do_GET

    def do_POST(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        try:
            if not path.startswith("/api/"):
                return self._error(404, f"Nicht gefunden: {path}")
            self._pruefe_herkunft()
            body = self._body()
            endpunkt = {
                "/api/sitzung": self.lauf.sitzung_starten,
                "/api/aufgabe": self.lauf.aufgabe,
                "/api/antwort": self.lauf.antwort,
                "/api/vorschlag": self.lauf.vorschlag,
                "/api/weiter": self.lauf.uebergehen,
                "/api/stuetze": self.lauf.stuetze,
                "/api/ende": self.lauf.beenden,
            }.get(path)
            if endpunkt is None:
                return self._error(404, f"Unbekannter Endpunkt: {path}")
            with self.lauf.lock:
                return self._json(endpunkt(body))
        except Abgelehnt as exc:
            self._error(400, str(exc))
        except UndeliverableTask as exc:
            # §113: ein unvollstaendiges Item wird nicht ausgeliefert. Das ist
            # kein Serverfehler, sondern die zugesagte Weigerung.
            self._error(409, str(exc))
        except BrokenPipeError:
            pass
        except Exception as exc:  # pragma: no cover - Notbremse
            self._error(500, f"{type(exc).__name__}: {exc}")

    def _pruefe_herkunft(self) -> None:
        """Nur Anfragen der eigenen Oberflaeche schreiben lassen.

        Der Server schreibt in die Datenbank und laeuft auf einem Port, den
        jede Seite im selben Browser kennt. Ein Formular auf einer fremden
        Seite kann ohne Vorabanfrage POST senden - aber nur mit den
        Inhaltstypen von HTML-Formularen, nie mit application/json. Beides
        zusammen - erzwungener Inhaltstyp und geprueftes Origin - laesst eine
        fremde Seite nicht an die Sitzung.
        """
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise Abgelehnt("Content-Type muss application/json sein.")
        origin = self.headers.get("Origin")
        if origin:
            erlaubt = {f"http://{self.server.server_address[0]}:{self.server.server_address[1]}",
                       f"http://localhost:{self.server.server_address[1]}"}
            if origin not in erlaubt:
                raise Abgelehnt(f"Fremde Herkunft: {origin}")

    def _body(self) -> dict:
        laenge = int(self.headers.get("Content-Length") or 0)
        if laenge > MAX_BODY:
            raise Abgelehnt("Anfrage zu groß.")
        roh = self.rfile.read(laenge) if laenge else b"{}"
        try:
            body = json.loads(roh.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise Abgelehnt(f"Kein gültiges JSON: {exc}") from None
        if not isinstance(body, dict):
            raise Abgelehnt("Der Rumpf muss ein JSON-Objekt sein.")
        return body

    def _static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        ziel = (self.ui_root / path.lstrip("/")).resolve()
        if not ziel.is_relative_to(self.ui_root.resolve()):
            return self._error(403, "Pfad ausserhalb des UI-Verzeichnisses")
        suffix = ziel.suffix.lower()
        if suffix not in ALLOWED_SUFFIXES or not ziel.is_file():
            return self._error(404, f"Nicht gefunden: {path}")
        ctype = mimetypes.types_map.get(suffix, "application/octet-stream")
        if ctype.startswith("text/") or suffix in (".js", ".json", ".svg"):
            ctype = f"{ctype}; charset=utf-8"
        self._send(200, ziel.read_bytes(), ctype)

    def log_message(self, fmt: str, *args) -> None:
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(fmt, *args)


def serve(db_path: Path, host: str = "127.0.0.1", port: int = 8766,
          ui_root: Path | None = None, zeige_loesung: bool = False) -> None:
    root = (ui_root or UI_ROOT).resolve()
    if not (root / "index.html").is_file():
        raise FileNotFoundError(f"Kein index.html unter {root}")
    if not db_path.is_file():
        raise FileNotFoundError(
            f"Keine Datenbank unter {db_path}. Zuerst: mathkomp build")

    lauf = Lernlauf(db_path, zeige_loesung=zeige_loesung)
    aufgaben = lauf.conn.execute("SELECT COUNT(*) n FROM tasks").fetchone()["n"]
    handler = type("BoundHandler", (Handler,), {"lauf": lauf, "ui_root": root})
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Datenbank:   {db_path} (schreibend - Sitzungen werden erfasst)")
    print(f"Aufgaben:    {aufgaben}")
    print(f"Oberflaeche: http://{host}:{port}/")
    if zeige_loesung:
        print("Loesungen:   werden nach einer falschen Antwort angezeigt (--loesung)")
    print("Beenden mit ctrl-C.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        httpd.server_close()
        lauf.close()


__all__ = ["serve", "Lernlauf", "Abgelehnt", "Handler", "UI_ROOT"]
