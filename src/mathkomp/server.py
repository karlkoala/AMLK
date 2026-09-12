"""HTTP-Server fuer die Analyseoberflaeche.

Zwei Aufgaben: die Dateien aus ``ui/`` ausliefern und die Endpunkte aus
``api.py`` als JSON bereitstellen. Mehr nicht - insbesondere keine Berechnung,
die nicht schon im Backend steht.

Die Verbindung wird **schreibgeschuetzt** geoeffnet (``mode=ro``). Das ist
keine Vorsichtsmassnahme, sondern eine fachliche: eine Betrachtung darf keine
Diagnostik veraendern. Wuerde die Oberflaeche etwa ``routing.next_task()``
aufrufen, um die naechste Aufgabe anzuzeigen, entstuende bei jedem Seitenaufruf
eine neue Zeile in ``routing_decisions`` - und §89 protokolliert Entscheidungen,
nicht Betrachtungen. Der Schreibschutz macht diesen Fehler unmoeglich statt
unwahrscheinlich.

Gebunden wird auf 127.0.0.1. Die Daten sind pseudonym (§86), aber sie gehoeren
trotzdem nicht ins Netz, nur weil jemand einen Server startet.

Nur Standardbibliothek, wie das uebrige Projekt.
"""

from __future__ import annotations

import json
import mimetypes
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from . import api
from .clock import Clock
from .config import Config

UI_ROOT = Path(__file__).resolve().parents[2] / "ui"

#: Erlaubte Dateiendungen. Eine Positivliste, damit der Server nichts
#: ausliefert, was jemand spaeter versehentlich in ui/ ablegt.
ALLOWED_SUFFIXES = {".html", ".css", ".js", ".json", ".svg", ".woff2", ".map"}


def _readonly(path: Path) -> sqlite3.Connection:
    """Schreibgeschuetzte Verbindung - und der Nachweis, dass sie es ist.

    Der Pfad wird in die URI *kodiert* eingesetzt, nicht angehaengt. Ein ``#``
    oder ``?`` im Verzeichnisnamen beendet die URI sonst vor dem Parameter:
    aus ``file:/…/Kunde #3/mathkomp.sqlite3?mode=ro`` liest SQLite die Datei
    ``/…/Kunde``, legt sie notfalls neu an, und ``mode=ro`` ist verschwunden -
    ohne Warnung. Die im Modulkopf zugesagte Eigenschaft "eine Betrachtung
    darf keine Diagnostik veraendern" waere damit aufgehoben, und die
    Oberflaeche zeigte eine leere Datenbank statt eines Fehlers.

    Unter Windows ist das latent, weil ``?`` dort kein gueltiger Dateiname
    ist. Auf APFS ist er es. Der Schutz lag also im Dateisystem, nicht im
    Code. Deshalb wird zusaetzlich nachgesehen, welche Datei SQLite
    tatsaechlich geoeffnet hat: nur wenn das die gemeinte ist, stimmt auch
    alles andere an dieser Verbindung.
    """
    ziel = path.resolve()
    conn = sqlite3.connect("file:" + quote(ziel.as_posix(), safe="/:") + "?mode=ro",
                           uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    geoeffnet = conn.execute("PRAGMA database_list").fetchone()["file"]
    if not geoeffnet or Path(geoeffnet).resolve() != ziel:
        conn.close()
        raise sqlite3.OperationalError(
            f"Geoeffnet wurde {geoeffnet or '(keine Datei)'}, gemeint war {ziel}. "
            "Der Pfad enthaelt vermutlich ein Zeichen, das SQLite in einer URI "
            "anders liest. Datenbank an einen Pfad ohne '#', '?' oder '%' legen "
            "oder mit --db ausdruecklich angeben.")
    return conn


class Handler(BaseHTTPRequestHandler):
    server_version = "mathkomp"
    sys_version = ""

    # Vom Server gesetzt.
    db_path: Path
    ui_root: Path

    # ------------------------------------------------------------ Antworten

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # Die Oberflaeche laedt nichts von aussen; das haelt sie dabei.
        #
        # style-src erlaubt 'unsafe-inline', script-src nicht. Die Trennung ist
        # Absicht: die wirksame Schranke ist die gegen eingeschleusten Code,
        # und die bleibt streng. Berechnete Breiten und Positionen dagegen
        # entstehen zur Laufzeit; Chrome prueft dafuer auch den Weg ueber das
        # CSSOM, sodass ohne diese Lockerung keine Balkengrafik darstellbar
        # waere. Fremdtext gelangt ausschliesslich ueber textContent in die
        # Seite, nie ueber innerHTML - eingeschleustes CSS hat damit keinen
        # Eintrittspunkt.
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
        body = json.dumps(payload, ensure_ascii=False, indent=None).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message}, status)

    # ----------------------------------------------------------- Weiterleitung

    def do_GET(self) -> None:  # noqa: N802 - von BaseHTTPRequestHandler vorgegeben
        path = unquote(urlparse(self.path).path)
        try:
            if path.startswith("/api/"):
                self._api(path[len("/api/"):])
            else:
                self._static(path)
        except BrokenPipeError:
            pass
        except Exception as exc:  # pragma: no cover - Notbremse, nie stillschweigend
            self._error(500, f"{type(exc).__name__}: {exc}")

    do_HEAD = do_GET

    def _api(self, route: str) -> None:
        conn = _readonly(self.db_path)
        try:
            cfg, clock = Config(conn), Clock()
            if route == "catalog":
                return self._json(api.catalog(conn))
            if route == "students":
                return self._json({"students": api.students(conn)})
            if route.startswith("student/"):
                student_id = route[len("student/"):].strip("/")
                known = {s["student_id"] for s in api.students(conn)}
                if student_id not in known:
                    return self._error(404, f"Unbekannte Schueler-ID: {student_id}")
                return self._json(api.student_profile(conn, student_id, cfg, clock))
            if route == "config":
                # §41/§35: Schwellenwerte sind Daten. Die Debug-Ansicht zeigt
                # sie mitsamt Status und Spezifikationsstelle, damit sichtbar
                # ist, welche Regel welchen Wert benutzt - und welche Werte
                # ausdruecklich UNDEFINED sind (§1).
                return self._json({"config": [
                    dict(r) for r in conn.execute(
                        "SELECT config_key, value, value_type, status, spec_section,"
                        " description FROM system_config ORDER BY config_key")]})
            return self._error(404, f"Unbekannter Endpunkt: /api/{route}")
        finally:
            conn.close()

    def _static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        target = (self.ui_root / path.lstrip("/")).resolve()
        if not target.is_relative_to(self.ui_root.resolve()):
            return self._error(403, "Pfad ausserhalb des UI-Verzeichnisses")
        # Kleingeschrieben verglichen, weil `resolve()` nur unter Windows die
        # Schreibweise auf dem Datentraeger zurueckgibt. Auf macOS findet
        # `is_file()` die Datei ebenfalls (APFS ist gross-/kleinschreibungs-
        # unabhaengig), aber `suffix` bliebe ".JS" - dieselbe URL waere hier
        # 200 und dort 404.
        suffix = target.suffix.lower()
        if suffix not in ALLOWED_SUFFIXES or not target.is_file():
            return self._error(404, f"Nicht gefunden: {path}")
        ctype = mimetypes.types_map.get(suffix, "application/octet-stream")
        if ctype.startswith("text/") or suffix in (".js", ".json", ".svg"):
            ctype = f"{ctype}; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    def log_message(self, fmt: str, *args) -> None:
        # Die Voreinstellung schreibt jede Anfrage nach stderr und macht die
        # Konsole unlesbar. Fehler weiterhin melden.
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(fmt, *args)


def serve(db_path: Path, host: str = "127.0.0.1", port: int = 8765,
          ui_root: Path | None = None) -> None:
    root = (ui_root or UI_ROOT).resolve()
    if not (root / "index.html").is_file():
        raise FileNotFoundError(f"Kein index.html unter {root}")

    # Ein Frueherkennungstest: liest die Datenbank ueberhaupt?
    conn = _readonly(db_path)
    try:
        anzahl = len(api.students(conn))
    finally:
        conn.close()

    handler = type("BoundHandler", (Handler,), {"db_path": db_path, "ui_root": root})
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Datenbank:   {db_path} (schreibgeschuetzt, {anzahl} Schueler:innen)")
    print(f"Oberflaeche: http://{host}:{port}/")
    # "Strg" steht auf keiner Mac-Tastatur; "ctrl" auf jeder, auch auf einer
    # deutschen Windows-Tastatur daneben.
    print("Beenden mit ctrl-C.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        httpd.server_close()
