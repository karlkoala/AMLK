"""Die Analyseoberflaeche: Architekturregeln, Server, Auslieferung.

Der Implementierungsauftrag macht einige Regeln verbindlich, die sich nicht
durch Ansehen sichern lassen, weil sie erst beim naechsten Umbau brechen:

* "Das Frontend soll ausschliesslich Daten darstellen, die vom bestehenden MVP
  bzw. Backend geliefert werden."
* "Baue eine saubere Datenzugriffsschicht" - also genau eine Stelle, die laedt.
* "Farben niemals als einzige Information verwenden."
* "Liefere eine tatsaechlich ausfuehrbare UI und nicht nur Wireframes."

Die Tests hier pruefen deshalb den Quelltext der Oberflaeche mechanisch und
fahren den Server einmal wirklich hoch. Sie ersetzen keinen Blick auf die
Seite - sie halten fest, was ein Blick nicht zuverlaessig erkennt.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mathkomp import db, importer, interactive, server, simulation
from mathkomp.clock import FixedClock
from mathkomp.config import Config

WURZEL = Path(__file__).resolve().parents[1]
UI = WURZEL / "ui"
ANSICHTEN_VERZEICHNIS = UI / "views"

#: Die Hauptnavigation, die der Auftrag mindestens verlangt - als Titel, wie
#: sie in der Navigationsleiste stehen.
GEFORDERTE_ANSICHTEN = [
    "Übersicht", "Kompetenzkarte", "Fehleranalyse", "Darstellung",
    "Hypothesen", "Evidenz", "Aufgabenverlauf", "Debug",
]


def quelle(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8")


def ohne_kommentare(pfad: Path) -> str:
    """Quelltext ohne Kommentare.

    Noetig, weil die Oberflaeche die Regeln, an die sie sich haelt, im Text
    zitiert - "UNKNOWN ist ein gueltiger Zustand und kein Defizit" steht so in
    uebersicht.js. Ein Zitat ist keine Regel im Code, und ein Test, der es als
    solche zaehlt, wuerde genau die Begruendungen austreiben, auf die es
    ankommt.
    """
    text = re.sub(r"/\*.*?\*/", "", quelle(pfad), flags=re.S)
    return "\n".join(re.sub(r"//.*$", "", zeile) for zeile in text.splitlines())


def ansichtsdateien() -> list[Path]:
    return sorted(ANSICHTEN_VERZEICHNIS.glob("*.js"))


def alle_js() -> list[Path]:
    return sorted(UI.glob("*.js")) + ansichtsdateien()


# --------------------------------------------------------- Datenzugriffsschicht


def test_nur_data_js_laedt_daten():
    """Die Datenzugriffsschicht ist genau eine Datei.

    Der Auftrag verlangt sie, damit die Datenquelle austauschbar bleibt. Waere
    auch nur ein fetch() in einer Ansicht, muesste beim Anschluss an eine
    andere Quelle jede Ansicht angefasst werden - und die Regel, dass die
    Oberflaeche nur darstellt, waere nicht mehr an einer Stelle pruefbar.
    """
    treffer = [p.relative_to(WURZEL).as_posix() for p in alle_js()
               if re.search(r"\bfetch\s*\(", quelle(p))]
    assert treffer == ["ui/data.js"], f"fetch() ausserhalb der Zugriffsschicht: {treffer}"


def test_keine_umgehung_der_zugriffsschicht():
    """Auch nicht ueber einen anderen Weg ins Netz."""
    verboten = ("XMLHttpRequest", "navigator.sendBeacon", "EventSource",
                "new WebSocket", "import(")
    treffer = [(p.name, wort) for p in alle_js() for wort in verboten
               if wort in quelle(p)]
    assert not treffer, f"Netzzugriff ausserhalb von data.js: {treffer}"


def test_fremdtext_kommt_nie_als_markup_in_die_seite():
    """Aufgabentexte und Antworten sind Fremdtext. Sie gehen ausschliesslich
    ueber textContent in die Seite - davon haengt ab, dass der Server
    ``script-src 'self'`` streng halten kann."""
    verboten = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write",
                "eval(", "new Function(")
    treffer = []
    for p in alle_js():
        text = quelle(p)
        for wort in verboten:
            for zeile in text.splitlines():
                if wort in zeile and not zeile.lstrip().startswith(("*", "//", "/*")):
                    treffer.append(f"{p.name}: {zeile.strip()}")
    assert not treffer, "Markup aus Zeichenketten:\n  " + "\n  ".join(treffer)


# ------------------------------------------------- Keine fachliche Logik vorn


def test_keine_statuswerte_im_frontend(conn):
    """Der Kern der Regel "keine eigenen fachlichen Entscheidungen".

    Kaeme ein Statusbegriff wie SECURE oder SUPPORT_FOCUS im Frontend vor,
    stuende dort eine Regel darueber, was er bedeutet - genau das, was der
    Auftrag mit ``if correct: level += 1`` verbietet. Die Gruppierung liefert
    das Backend als ``resource_class``; die Oberflaeche liest sie nur.
    """
    begriffe = {r["term"] for r in conn.execute(
        "SELECT term FROM vocabulary_terms WHERE vocabulary = 'COMPETENCY_STATUS'")}
    treffer = [f"{p.name}: {b}" for p in alle_js() for b in begriffe
               if re.search(rf"\b{b}\b", ohne_kommentare(p))]
    assert not treffer, f"Kompetenzstatus im Frontend ausgewertet: {treffer}"


def test_hypothesenstatus_wird_vorn_nicht_ausgewertet(conn):
    """Dieselbe Regel eine Ebene tiefer.

    Ob eine Hypothese GERADE geprueft wird, haengt an zwei Bedingungen: die
    Kontrollaufgabe ist offen UND der Status ist noch einer der aktiven. Die
    Oberflaeche hat lange nur die erste Haelfte geprueft - an drei Stellen, zwei
    davon unvollstaendig. Die Bedingung steht jetzt als
    ``hypothesis_test.is_active`` im Vertrag; ein Vergleich gegen einen
    HYPOTHESIS_STATUS- oder Pruefzustandswert im Frontend waere ihr Nachbau.
    """
    # Geprueft wird der Vergleich auf PLANNED - der war die halbe Regel. DONE
    # sagt nur, ob die Kontrollaufgabe bearbeitet wurde, und ist eine Anzeige.
    # Dass jeder HYPOTHESIS_STATUS ein eigenes Zeichen und sein deutsches Wort
    # traegt, prueft `test_jeder_hypothesenstatus_hat_ein_zeichen`; die Zuordnung
    # Status -> Darstellung ist erlaubt, die Zuordnung Status -> Entscheidung
    # nicht.
    assert conn.execute(
        "SELECT COUNT(*) FROM vocabulary_terms WHERE vocabulary = 'HYPOTHESIS_STATUS'"
    ).fetchone()[0] > 0, "Vokabular vorhanden"
    treffer = [f"{p.name}: PLANNED" for p in alle_js()
               if re.search(r'===\s*"PLANNED"', ohne_kommentare(p))]
    assert not treffer, f"Hypothesenregel im Frontend nachgebaut: {treffer}"


def test_keine_schwellenwerte_im_frontend(conn):
    """§41/§35: Schwellenwerte sind Daten. Ein zweiter Wert im Frontend koennte
    von dem abweichen, mit dem die Engine gerechnet hat."""
    schluessel = [r["config_key"] for r in conn.execute(
        "SELECT config_key FROM system_config"
        " WHERE value_type IN ('int', 'float') AND value IS NOT NULL")]
    treffer = [f"{p.name}: {k}" for p in alle_js() for k in schluessel
               if k in ohne_kommentare(p)]
    assert not treffer, f"Konfigurationswert im Frontend nachgebaut: {treffer}"


def test_ansichten_runden_gelieferte_zahlen_nicht_weg():
    """Gerundet wird nicht, wo die Zahl die Aussage traegt.

    ``toFixed(1)`` hat aus 2.9375 und 2.8750 zweimal "2.9" gemacht. In dreizehn
    protokollierten Entscheidungen stand der Hoechstwert danach mehrfach da -
    ausgerechnet in der Ansicht, die erklaeren soll, warum diese Aufgabe gewaehlt
    wurde. Vier Nachkommastellen sind erlaubt, denn so genau liefert die Engine.
    """
    treffer = []
    for p in ansichtsdateien():
        for nummer, zeile in enumerate(ohne_kommentare(p).splitlines(), 1):
            for stellen in re.findall(r"toFixed\((\d)\)", zeile):
                if int(stellen) < 4:
                    treffer.append(f"{p.name}:{nummer} toFixed({stellen})")
    assert not treffer, "Zahl in einer Ansicht weggerundet:\n  " + "\n  ".join(treffer)


def test_keine_prozentwerte_in_den_ansichten():
    """§117 verbietet den Prozentwert. Ein Prozentzeichen darf deshalb nur als
    CSS-Breite vorkommen - also in dom.js, nicht in einer Ansicht, die Text
    erzeugt."""
    treffer = []
    for p in ansichtsdateien():
        for nummer, zeile in enumerate(quelle(p).splitlines(), 1):
            if "%" in zeile and "width" not in zeile and "basis" not in zeile:
                treffer.append(f"{p.name}:{nummer} {zeile.strip()}")
    assert not treffer, "Prozentzeichen in einer Ansicht:\n  " + "\n  ".join(treffer)


# --------------------------------------------- Farbe nie als einzige Information


def _js_schluessel(text: str, name: str) -> set[str]:
    """Die Schluessel eines exportierten Objektliterals aus labels.js."""
    treffer = re.search(rf"export const {name} = \{{(.*?)\n\}};", text, re.S)
    assert treffer, f"{name} nicht gefunden"
    return set(re.findall(r"([A-Z][A-Z_]+)\s*:", treffer.group(1)))


@pytest.fixture(scope="module")
def zeichen() -> dict[str, set[str]]:
    text = quelle(UI / "labels.js")
    return {name: _js_schluessel(text, name)
            for name in ("KLASSE", "HYPOTHESE_ZEICHEN", "RICHTUNG_ZEICHEN")}


def test_jede_ressourcenklasse_hat_ein_zeichen(zeichen):
    """"Farben niemals als einzige Information verwenden."

    Geprueft gegen den Vertrag, nicht gegen eine Liste im Test: kaeme eine
    vierte Gruppe dazu, waere sie ohne Zeichen nur an der Farbe zu erkennen.
    """
    from mathkomp import api
    assert zeichen["KLASSE"] == set(api.RESOURCE_CLASS_LABEL)


def test_jeder_hypothesenstatus_hat_ein_zeichen(conn, zeichen):
    begriffe = {r["term"] for r in conn.execute(
        "SELECT term FROM vocabulary_terms WHERE vocabulary = 'HYPOTHESIS_STATUS'")}
    assert not begriffe - zeichen["HYPOTHESE_ZEICHEN"], \
        f"Hypothesenstatus nur farblich unterscheidbar: {sorted(begriffe - zeichen['HYPOTHESE_ZEICHEN'])}"


def test_jede_evidenzrichtung_hat_ein_zeichen(conn, zeichen):
    begriffe = {r["term"] for r in conn.execute(
        "SELECT term FROM vocabulary_terms WHERE vocabulary = 'EVIDENCE_DIRECTION'")}
    assert not begriffe - zeichen["RICHTUNG_ZEICHEN"], \
        f"Evidenzrichtung nur farblich unterscheidbar: {sorted(begriffe - zeichen['RICHTUNG_ZEICHEN'])}"


def test_die_sechs_ebenen_der_grundregel_sind_unterscheidbar():
    """Die Grundregel des Auftrags: Beobachtung, Fehler, Evidenz,
    Kompetenzzustand, Hypothese und Hypothesenpruefung duerfen nicht
    gleichgesetzt werden. Jede Ebene traegt dafuer ein eigenes Kuerzel."""
    text = quelle(UI / "labels.js")
    block = re.search(r"export const EBENE = \{(.*?)\n\};", text, re.S)
    assert block
    ebenen = dict(re.findall(r"(\w+):\s*\[\"(\w)\"", block.group(1)))
    assert set(ebenen) == {"beobachtung", "fehler", "evidenz", "zustand",
                           "hypothese", "pruefung"}
    assert len(set(ebenen.values())) == 6, "Zwei Ebenen teilen sich ein Kuerzel"


# ---------------------------------------------------------------- Navigation


def test_alle_geforderten_ansichten_sind_in_der_navigation():
    text = quelle(UI / "app.js")
    block = re.search(r"const ANSICHTEN = \[(.*?)\n\];", text, re.S)
    assert block, "ANSICHTEN nicht gefunden"
    titel = re.findall(r'"[a-z]+",\s*"([^"]+)"', block.group(1))
    assert len(titel) >= 8, f"Der Auftrag verlangt mindestens acht Bereiche, gefunden: {titel}"
    for gefordert in GEFORDERTE_ANSICHTEN:
        assert any(gefordert in t for t in titel), f"Bereich fehlt: {gefordert}"


def test_jedes_ansichtsmodul_ist_eingebunden():
    """Kein verwaistes Modul - und keine Ansicht, die es nur als Datei gibt."""
    text = quelle(UI / "app.js")
    for datei in ansichtsdateien():
        assert f"./views/{datei.name}" in text, f"{datei.name} wird nicht importiert"


def test_jedes_ansichtsmodul_liefert_render():
    for datei in ansichtsdateien():
        text = quelle(datei)
        assert "export default" in text, f"{datei.name} hat keinen Standardexport"
        assert re.search(r"\brender\s*\(", text), f"{datei.name} hat kein render()"


# ------------------------------------------------------- Der laufende Server


@pytest.fixture(scope="module")
def datenbank(tmp_path_factory) -> Path:
    """Eine Datei-Datenbank mit einem echten Durchlauf.

    Als Datei und nicht im Speicher, weil der Server sie schreibgeschuetzt
    ueber einen eigenen URI oeffnet - genau das soll mitgeprueft werden.
    """
    pfad = tmp_path_factory.mktemp("ui") / "mathkomp.sqlite3"
    conn = db.connect(str(pfad))
    db.init_schema(conn)
    with db.transaction(conn):
        importer.import_all(conn, WURZEL / "content")
    simulation.run(conn, "UI-TEST", simulation.policy_basic_difficulty,
                   FixedClock(), max_turns=4, cfg=Config(conn))
    conn.commit()
    conn.close()
    return pfad


@pytest.fixture(scope="module")
def adresse(datenbank):
    handler = type("BoundHandler", (server.Handler,),
                   {"db_path": datenbank, "ui_root": UI.resolve()})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def hole(adresse: str, pfad: str):
    with urllib.request.urlopen(f"{adresse}{pfad}", timeout=10) as antwort:
        return antwort.status, antwort.headers, antwort.read()


def status_von(adresse: str, pfad: str) -> int:
    try:
        return hole(adresse, pfad)[0]
    except urllib.error.HTTPError as fehler:
        return fehler.code


def test_die_oberflaeche_laeuft_wirklich(adresse):
    """"Liefere eine tatsaechlich ausfuehrbare UI und nicht nur Wireframes."
    Das Geruest und alles, was es nachlaedt, muss ausgeliefert werden."""
    status, kopf, rumpf = hole(adresse, "/")
    assert status == 200
    assert kopf["Content-Type"].startswith("text/html")
    seite = rumpf.decode("utf-8")
    assert '<div id="inhalt"' in seite or 'id="inhalt"' in seite

    module = ["/app.css", "/app.js", "/data.js", "/dom.js", "/labels.js"]
    module += [f"/views/{p.name}" for p in ansichtsdateien()]
    fehlend = [pfad for pfad in module if status_von(adresse, pfad) != 200]
    assert not fehlend, f"Nicht ausgeliefert: {fehlend}"


def test_alle_endpunkte_antworten(adresse):
    for pfad, schluessel in (("/api/catalog", "competency_nodes"),
                             ("/api/students", "students"),
                             ("/api/student/UI-TEST", "competency_states"),
                             ("/api/config", "config")):
        status, kopf, rumpf = hole(adresse, pfad)
        assert status == 200, pfad
        assert kopf["Content-Type"].startswith("application/json"), pfad
        daten = json.loads(rumpf)
        assert schluessel in daten and daten[schluessel], pfad


def test_unbekannte_kennung_und_endpunkt_ergeben_404(adresse):
    assert status_von(adresse, "/api/student/GIBT-ES-NICHT") == 404
    assert status_von(adresse, "/api/erfunden") == 404


def test_der_server_liefert_nichts_ausserhalb_von_ui(adresse):
    """Weder ueber einen Pfad nach oben noch ueber eine fremde Endung."""
    assert status_von(adresse, "/../src/mathkomp/api.py") in (403, 404)
    assert status_von(adresse, "/../../mathkomp.sqlite3") in (403, 404)
    assert status_von(adresse, "/%2e%2e/src/mathkomp/api.py") in (403, 404)


def test_die_seite_laedt_nichts_von_aussen(adresse):
    """Die Inhaltsrichtlinie. ``script-src`` bleibt streng - eingeschleuster
    Code ist die Schranke, auf die es ankommt."""
    _status, kopf, _rumpf = hole(adresse, "/")
    richtlinie = kopf["Content-Security-Policy"]
    assert richtlinie
    assert "script-src 'self';" in richtlinie
    assert "unsafe-inline" not in richtlinie.split("style-src")[0]
    for regel in ("default-src 'self'", "connect-src 'self'",
                  "frame-ancestors 'none'", "base-uri 'none'"):
        assert regel in richtlinie, regel


def test_ansehen_veraendert_die_diagnostik_nicht(adresse, datenbank):
    """Die wichtigste Eigenschaft des Servers.

    §89 protokolliert Entscheidungen, nicht Betrachtungen. Wuerde die
    Oberflaeche die naechste Aufgabe selbst berechnen lassen, entstuende bei
    jedem Seitenaufruf eine Entscheidungszeile - und das Protokoll behauptete
    Diagnostik, die nie stattgefunden hat.
    """
    tabellen = ("routing_decisions", "evidence_events", "task_attempts",
                "student_hypotheses", "student_competency_state")

    def zaehle():
        conn = db.connect(str(datenbank))
        try:
            return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    for t in tabellen}
        finally:
            conn.close()

    vorher = zaehle()
    for pfad in ("/", "/api/catalog", "/api/students", "/api/student/UI-TEST",
                 "/api/student/UI-TEST", "/api/config"):
        assert status_von(adresse, pfad) == 200
    assert zaehle() == vorher, "Ein Seitenaufruf hat Daten veraendert"


# ----------------------------------------- Was die Oberflaeche aufgedeckt hat


def test_ein_durchlauf_protokolliert_genau_eine_entscheidung_je_zug(conn):
    """Entscheidung D-35.

    Die Debug-Ansicht zeigt das Entscheidungsprotokoll - und machte damit
    sichtbar, dass die Eingabeschleife ``next_task()`` ein zweites Mal
    aufrief, obwohl ``submit()`` die Auswahl nach §120 Schritt 7 bereits
    getroffen hatte. Jeder Zug stand doppelt im Protokoll.

    Erwartet: eine Entscheidung je Zug plus die erste, und kein Befehl
    zwischendurch erzeugt eine weitere - denn ein Befehl trifft keine
    Entscheidung.
    """
    eingaben = iter(["0", ":hilfe", ":loesung", "0", "0"])
    interactive.run(conn, "UI-CLI", grade=3, max_tasks=3,
                    read=lambda _: next(eingaben, ":ende"),
                    write=lambda _: None)

    versuche = conn.execute(
        "SELECT COUNT(*) FROM task_attempts WHERE student_id = 'UI-CLI'").fetchone()[0]
    entscheidungen = conn.execute(
        "SELECT COUNT(*) FROM routing_decisions WHERE student_id = 'UI-CLI'").fetchone()[0]
    assert versuche == 3
    assert entscheidungen == versuche + 1, \
        "Je Zug genau eine Entscheidung, dazu die erste vor dem ersten Zug"

    doppelt = conn.execute(
        "SELECT selected_task, previous_task, COUNT(*) c FROM routing_decisions"
        " WHERE student_id = 'UI-CLI' GROUP BY selected_task, previous_task"
        " HAVING c > 1").fetchall()
    assert not doppelt, f"Identische Entscheidungen im Protokoll: {[tuple(r) for r in doppelt]}"
