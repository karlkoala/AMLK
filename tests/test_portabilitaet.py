"""Was unter Windows und unter macOS gleich sein muss.

Das Projekt ist ausschliesslich unter Windows entwickelt worden. Dabei haben
mehrere Eigenschaften des Betriebssystems Fehler verdeckt, die es im Code gibt:
eine Dateisperre, die ein Loeschen verhindert hat, ein `resolve()`, das
Schreibweisen korrigiert, und ein Dateiname, in dem '?' gar nicht vorkommen
kann. Auf macOS und Linux trifft nichts davon zu.

Die Tests hier pinnen deshalb nicht Plattformverhalten, sondern das Gegenteil:
dass das Programm selbst entscheidet und nicht das Dateisystem fuer es.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mathkomp import cli, db, importer, server  # noqa: E402

CONTENT = ROOT / "content"


def _kompetenzen_in_content() -> int:
    """Wieviele Kompetenzen content/ mitbringt.

    Keine feste Zahl: content/ waechst - mit Klasse 5 bis 10 kam ein zweiter
    Ordner dazu. Eine eingefrorene Zahl liesse die Pruefungen hier an der
    Datenmenge scheitern statt an dem, worum es ihnen geht: dass die
    geoeffnete Datei die gemeinte ist und lesbar bleibt.
    """
    return sum(len(json.loads(p.read_text(encoding="utf-8"))["competencies"])
               for p in sorted(CONTENT.glob("**/competencies.json")))


def _gebaut(pfad: Path) -> Path:
    """Eine echte Datenbankdatei mit Content, ohne erhobene Daten."""
    conn = db.connect(pfad)
    db.init_schema(conn)
    with db.transaction(conn):
        importer.import_all(conn, CONTENT)
    conn.close()
    return pfad


# ------------------------------------------------- Schreibschutz der Ansicht


@pytest.mark.parametrize("ordner", ["Kunde #3", "frage?zeichen", "prozent%41hex",
                                    "mit leerzeichen"])
def test_schreibschutz_ueberlebt_sonderzeichen_im_pfad(tmp_path, ordner):
    """§89: eine Betrachtung darf keine Diagnostik veraendern.

    Der Pfad wurde in die SQLite-URI eingesetzt statt kodiert. Ein '#' oder '?'
    im Verzeichnisnamen beendet die URI dann vor ``mode=ro``: SQLite oeffnet
    eine andere Datei, legt sie notfalls an, und der Schreibschutz ist weg -
    ohne Warnung, bei leerer Oberflaeche. Unter Windows blieb das unentdeckt,
    weil '?' dort kein gueltiger Dateiname ist; auf APFS ist er einer.
    """
    try:
        verzeichnis = tmp_path / ordner
        verzeichnis.mkdir()
    except OSError:
        pytest.skip(f"Dateiname {ordner!r} auf diesem Dateisystem nicht erlaubt")

    ziel = _gebaut(verzeichnis / "db.sqlite3")
    conn = server._readonly(ziel)
    try:
        geoeffnet = conn.execute("PRAGMA database_list").fetchone()["file"]
        assert Path(geoeffnet).resolve() == ziel.resolve(), \
            "Geoeffnet wurde eine andere Datei als die gemeinte"
        assert conn.execute("SELECT COUNT(*) FROM competencies").fetchone()[0] \
            == _kompetenzen_in_content()
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE beweis (x)")
    finally:
        conn.close()

    assert not (tmp_path / ordner.split("#")[0].split("?")[0].strip()).is_file(), \
        "SQLite hat eine Datei am abgeschnittenen Pfad angelegt"


# ------------------------------------------------- erhobene Daten vs. Neubau


def test_build_force_verweigert_das_loeschen_erhobener_daten(tmp_path, capsys):
    """Der Schutz lag im Betriebssystem, jetzt liegt er im Programm.

    Unter Windows wirft ``unlink()`` auf eine geoeffnete Datenbank
    PermissionError - eine nebenher laufende ``session`` war dadurch zufaellig
    geschuetzt. Unter macOS und Linux verschwindet nur der Verzeichniseintrag:
    die Sitzung schreibt in den namenlosen Inode weiter und verliert beim
    Beenden alles, ohne dass irgendwo ein Fehler erscheint.
    """
    pfad = _gebaut(tmp_path / "mathkomp.sqlite3")
    conn = db.connect(pfad)
    conn.execute("INSERT INTO students (student_id, created_at) VALUES ('KIND-01', '2026-01-01T00:00:00')")
    conn.commit()
    conn.close()

    args = argparse.Namespace(db=str(pfad), content=str(CONTENT),
                              force=True, discard_data=False)
    assert cli.cmd_build(args) == 2
    assert pfad.is_file(), "Die Datei wurde trotz Abbruch geloescht"

    meldung = capsys.readouterr().err
    assert "students" in meldung and "--discard-data" in meldung

    conn = db.connect(pfad)
    assert conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 1
    conn.close()


def test_build_force_mit_discard_data_baut_neu(tmp_path):
    """Der ausdrueckliche Weg bleibt offen - er muss nur ausdruecklich sein."""
    pfad = _gebaut(tmp_path / "mathkomp.sqlite3")
    conn = db.connect(pfad)
    conn.execute("INSERT INTO students (student_id, created_at) VALUES ('KIND-01', '2026-01-01T00:00:00')")
    conn.commit()
    conn.close()

    args = argparse.Namespace(db=str(pfad), content=str(CONTENT),
                              force=True, discard_data=True)
    assert cli.cmd_build(args) == 0
    conn = db.connect(pfad)
    assert conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM competencies").fetchone()[0] \
        == _kompetenzen_in_content()
    conn.close()


def test_erhobene_daten_kennt_alle_tabellen_der_user_state_ebene(conn):
    """§85: die USER-STATE-Ebene ist genau das, was content/ nicht zurueckgibt.

    Faende ``_erhobene_daten`` eine dieser Tabellen nicht, verschwiegen die
    Warnung und der Abbruch genau den Teil, um den es geht.
    """
    vorhanden = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    fehlen = set(cli.USER_STATE_TABELLEN) - vorhanden
    assert not fehlen, f"Im Schema nicht vorhanden: {sorted(fehlen)}"


# ------------------------------------------- keine Aussage ohne Datengrundlage


def test_lesende_befehle_brechen_bei_leerer_datenbank_ab(tmp_path, capsys):
    """Regeln gegen Nichts zu pruefen ergibt keine Aussage.

    ``validate`` meldete auf einer leeren Datenbank drei Verstoesse gegen §75,
    §62 und §115 - genau die drei Sperren, mit denen dieses Projekt seine
    strukturelle Absicherung begruendet. Gemeldet wurde das Fehlen der
    Konfiguration als ihre Verletzung.
    """
    pfad = tmp_path / "leer.sqlite3"
    conn = db.connect(pfad)
    db.init_schema(conn)
    conn.close()

    for befehl in (cli.cmd_validate, cli.cmd_report):
        args = argparse.Namespace(db=str(pfad))
        with pytest.raises(cli.DatenbankUnbrauchbar) as fehler:
            befehl(args)
        assert "keinen Content" in str(fehler.value)


def test_lesender_befehl_legt_keine_datenbank_an(tmp_path):
    """``sqlite3.connect()`` legt eine fehlende Datei stillschweigend an.

    Wer ``validate`` vor ``build`` aufrief, hatte danach eine leere Datenbank
    am Standardpfad - und der naechste ``build`` verlangte ``--force``, ohne
    dass je etwas aufgebaut worden waere.
    """
    pfad = tmp_path / "gibtsnicht.sqlite3"
    with pytest.raises(cli.DatenbankUnbrauchbar):
        cli.cmd_validate(argparse.Namespace(db=str(pfad)))
    assert not pfad.exists(), "Der lesende Befehl hat eine Datei angelegt"


# ------------------------------------------------------- Auslieferung der UI


def test_ui_dateien_werden_unabhaengig_von_der_schreibweise_erkannt():
    """``resolve()`` korrigiert die Schreibweise nur unter Windows.

    Auf dem gross-/kleinschreibungsunabhaengigen APFS findet ``is_file()`` die
    Datei ebenfalls, aber ``suffix`` bliebe ".JS" - dieselbe URL waere hier 200
    und dort 404.
    """
    assert all(s == s.lower() for s in server.ALLOWED_SUFFIXES)
    quelltext = (ROOT / "src" / "mathkomp" / "server.py").read_text(encoding="utf-8")
    assert "target.suffix.lower()" in quelltext, \
        "Die Endung wird wieder ungenormt verglichen"


def test_importpfade_der_oberflaeche_stimmen_buchstabengenau():
    """Auf einem gross-/kleinschreibungsabhaengigen Dateisystem gaebe es sonst
    keinen 404, sondern eine Oberflaeche, die gar nicht erst startet."""
    import posixpath
    import re

    ui = ROOT / "ui"
    bekannt = {p.relative_to(ui).as_posix() for p in ui.rglob("*") if p.is_file()}
    quellen = [ui / "index.html"] + sorted(ui.rglob("*.js"))
    muster = re.compile(r'(?:from|src|href)\s*=?\s*["\']([\w./-]+\.(?:js|css|html))["\']')

    geprueft = 0
    for datei in quellen:
        basis = datei.parent.relative_to(ui).as_posix()
        for treffer in muster.findall(datei.read_text(encoding="utf-8")):
            ziel = posixpath.normpath(posixpath.join(basis, treffer)).lstrip("./")
            assert ziel in bekannt, \
                f"{datei.relative_to(ui).as_posix()} verweist auf {ziel!r}, das es so nicht gibt"
            geprueft += 1
    assert geprueft >= 12, f"Nur {geprueft} Verweise gefunden - das Muster greift nicht mehr"


# ------------------------------------------------------ Kodierung der Quellen


def test_alle_textdateien_sind_utf8():
    """SPEC_VOLLTEXT.txt war cp1252 - unter Windows lesbar, auf macOS Zeichensalat.

    Und jedes kuenftige ``read_text()`` darauf waere hier durchgelaufen und
    dort mit UnicodeDecodeError gestorben.
    """
    endungen = {".py", ".js", ".json", ".sql", ".html", ".css", ".md", ".txt",
                ".toml", ".editorconfig", ".gitignore"}
    schlecht = []
    for pfad in ROOT.rglob("*"):
        if not pfad.is_file() or any(t in pfad.parts for t in
                                     ("__pycache__", ".pytest_cache", ".venv", ".git")):
            continue
        if pfad.suffix.lower() not in endungen and pfad.name not in (".gitignore", ".editorconfig"):
            continue
        roh = pfad.read_bytes()
        try:
            roh.decode("utf-8")
        except UnicodeDecodeError as fehler:
            schlecht.append(f"{pfad.relative_to(ROOT)}: {fehler}")
        if roh.startswith(b"\xef\xbb\xbf"):
            schlecht.append(f"{pfad.relative_to(ROOT)}: BOM")
    assert not schlecht, "\n".join(schlecht)


# --------------------------------------------------- Befehle in den Meldungen


def test_keine_plattformgebundenen_startbefehle_in_meldungen():
    """``py`` gibt es nur unter Windows, ``python`` auf einem frischen macOS gar nicht.

    Die Oberflaeche und die Fehlermeldungen der Kommandozeile nannten beides
    als Handlungsanweisung - der Leser auf dem Mac haette keinen Befehl gehabt,
    der funktioniert. ``mathkomp`` heisst nach ``pip install -e .`` ueberall gleich.

    Geprueft werden Zeichenkettenliterale, also das, was am Ende jemand liest
    und abtippt. Der Hilfetext in ``cli.py`` nennt ``python3 -m …`` und
    ``py -m …`` weiterhin ausdruecklich nebeneinander - dort ist der
    Plattformunterschied der Gegenstand und keine Anweisung.
    """
    import re

    muster = re.compile(r'["\'][^"\']*\b(?:py|python|python3)\s+-m\s+mathkomp')
    treffer = []
    for pfad in list((ROOT / "src" / "mathkomp").glob("*.py")) + \
                list((ROOT / "ui").rglob("*.js")):
        for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
            if muster.search(zeile):
                treffer.append(f"{pfad.relative_to(ROOT)}:{nr}: {zeile.strip()}")
    assert not treffer, "Plattformgebundener Startbefehl in einer Meldung:\n" + "\n".join(treffer)


# ------------------------------------------------------ Das Startsymbol Mac

def test_paket_uebergibt_keine_erhobenen_daten_und_ein_klickbares_symbol(tmp_path):
    """Das fertige Archiv, nicht die Absicht des Packers.

    Drei Zusagen der Anleitung haengen daran: dass beim Entpacken genau ein
    oberster Ordner entsteht und dieser nicht heisst wie das Python-Paket in
    src/mathkomp (die Anleitung nennt den Namen deshalb gar nicht mehr, siehe
    ENTSCHEIDUNGEN.md D-60), dass die Startsymbole ein Ausfuehrungsrecht
    mitbringen (sonst oeffnet der Doppelklick den Text im Editor), und dass
    keine erhobenen Daten mitreisen (§86, siehe ENTSCHEIDUNGEN.md D-53).

    Die Hostkennung wird eigens geprueft, und das ist der Kern. Der Modus
    stand hier lange richtig und war trotzdem wirkungslos: ``ZipInfo`` setzt
    ``create_system`` unter Windows auf 0 (MS-DOS), und bei dieser Kennung
    liest kein Entpacker die oberen 16 Bit als Unix-Modus. Ein Test, der nur
    das x-Bit abfragt, haette das Paket durchgewinkt.
    """
    import zipfile

    sys.path.insert(0, str(ROOT / "tools"))
    import paket_fuer_mac

    ziel = tmp_path / "paket.zip"
    paket_fuer_mac.packen(ziel)

    with zipfile.ZipFile(ziel) as archiv:
        eintraege = archiv.infolist()
        namen = [e.filename for e in eintraege]

        oberste = {n.split("/")[0] for n in namen}
        assert oberste == {paket_fuer_mac.PAKETNAME}, \
            f"Nicht genau ein Ordner oben: {oberste}"

        # Der oberste Ordner darf nicht heissen wie das Python-Paket in
        # src/. Diese Doppelbelegung hat die Anleitung einmal einen Ordner
        # "mathkomp" beschreiben lassen, in dem die Startsymbole lägen -
        # sie liegen aber ganz oben, und über GitHub heißt der Ordner
        # ohnehin nach dem Repository.
        assert paket_fuer_mac.PAKETNAME != "mathkomp", (
            "Der Paketordner heisst wie das Python-Paket src/mathkomp - "
            "zwei verschiedene Dinge unter einem Namen")

        daten = [n for n in namen if n.endswith(".sqlite3")]
        assert not daten, f"Erhobene Daten im Paket: {daten}"

        rest = [n for n in namen
                if "__pycache__" in n or "/.venv/" in n or n.endswith(".DS_Store")]
        assert not rest, f"Zielrechner-Reste im Paket: {rest}"

        symbole = [e for e in eintraege if e.filename.endswith(".command")]
        erwartet = {f"{paket_fuer_mac.PAKETNAME}/START-MAC.command",
                    f"{paket_fuer_mac.PAKETNAME}/SITZUNG-MAC.command"}
        assert {e.filename for e in symbole} == erwartet, \
            f"Andere Startsymbole als erwartet: {[e.filename for e in symbole]}"

        for e in symbole:
            modus = e.external_attr >> 16
            assert e.create_system == 3, (
                f"{e.filename}: Hostkennung {e.create_system} statt 3 (Unix) - "
                "der Modus darunter wird nicht gelesen")
            assert modus & 0o111, \
                f"{e.filename} ohne Ausfuehrungsrecht (Modus {modus:o})"
            assert b"\r\n" not in archiv.read(e.filename), \
                f"Windows-Zeilenenden in {e.filename}"


def test_anleitung_zitiert_keine_meldung_die_es_nicht_gibt():
    """Die Fehlertabelle ist nur so viel wert, wie ihre linke Spalte trifft.

    Sie zitierte einmal einen englischen Gatekeeper-Satz, den ein
    deutschsprachiger Mac gar nicht anzeigt - wer danach suchte, fand nichts
    und war allein. Geprueft wird deshalb die Richtung, die damals versagt
    hat: jedes in Anfuehrungszeichen gesetzte Zitat muss woertlich in einem
    der Skripte oder in der Oberflaeche vorkommen.

    Die Gegenrichtung - jede Meldung des Skripts hat eine Tabellenzeile -
    steht hier bewusst nicht. Sie waere richtig, aber sie wuerde bei jeder
    neuen Abbruchmeldung fehlschlagen, auch bei einer, die niemand je sieht.
    """
    import re

    anleitung = (ROOT / "ANLEITUNG-MAC.md").read_text(encoding="utf-8")
    quellen = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("START-MAC.command", "SITZUNG-MAC.command", "ui/index.html"))

    #: Wortlaut, den nicht dieses Programm schreibt, sondern der Browser.
    FREMD = {"nicht erreichbar"}

    zitate = re.findall(r"\u201e([^\u201c\"]+)\"", anleitung)
    assert len(zitate) >= 10, f"Nur {len(zitate)} Zitate gefunden - greift das Muster noch?"

    fehlend = [z for z in zitate
               if z.rstrip(" \u2026").strip() not in quellen and z not in FREMD]
    assert not fehlend, (
        "Die Anleitung zitiert Meldungen, die so nirgends erscheinen:\n"
        + "\n".join(f"  \u201e{z}\u201c" for z in fehlend))


def test_alle_startsymbole_sind_auf_einem_mac_startbar():
    """Jedes ``*.command`` im Projektordner muss auf einem Mac anspringen.

    Zwei Shells bringt macOS von Haus aus mit, und sie sind verschieden alt.
    bash steht dort seit dem Lizenzwechsel auf einer Fassung von 2007: was
    bash 4 dazugebracht hat - assoziative Arrays, ``mapfile`` -, scheitert
    auf dem Zielrechner. zsh dagegen ist die Standardshell und aktuell. Die
    Einschraenkung auf bash 3.2 gilt deshalb nur fuer bash-Skripte; welche
    Shell gemeint ist, sagt die Shebang-Zeile.

    Der Rest gilt unabhaengig von der Shell, weil er nichts mit ihr zu tun
    hat: Unix-Zeilenenden, ``set -u`` als erster Befehl, und der Wechsel in
    den eigenen Ordner, bevor irgendetwas angefasst wird.

    Gesucht wird mit ``glob`` statt mit Dateinamen: ``SITZUNG-MAC.command``
    ist spaeter dazugekommen, und genau solche Nachzuegler fallen aus einer
    Pruefung heraus, die ihre Dateien einzeln aufzaehlt.
    """
    import re

    mac_shells = (b"#!/bin/bash\n", b"#!/bin/zsh\n")

    skripte = sorted(ROOT.glob("*.command"))
    assert len(skripte) >= 2, f"Erwartet werden mindestens zwei, gefunden: {skripte}"

    nur_bash4 = {
        r"declare\s+-A": "assoziatives Array (bash 4)",
        r"local\s+-A": "assoziatives Array (bash 4)",
        r"\bmapfile\b": "mapfile (bash 4)",
        r"\breadarray\b": "readarray (bash 4)",
        r"\$\{[A-Za-z_][A-Za-z0-9_]*\^\^": "Grossschreibung ${x^^} (bash 4)",
        r"\$\{[A-Za-z_][A-Za-z0-9_]*,,": "Kleinschreibung ${x,,} (bash 4)",
        r"&>>": "&>> (bash 4)",
        r";;&": ";;& in case (bash 4)",
    }

    for skript in skripte:
        roh = skript.read_bytes()
        assert b"\r\n" not in roh, f"Windows-Zeilenenden in {skript.name}"
        shebang = next((s for s in mac_shells if roh.startswith(s)), None)
        assert shebang is not None, (
            f"{skript.name} nennt keine Shell, die auf einem Mac vorhanden ist:"
            f" {[s.decode().strip() for s in mac_shells]}")

        text = roh.decode("utf-8")
        # Nur Code, keine Prosa: der Kopf der Skripte zaehlt die verbotenen
        # Konstrukte namentlich auf, damit die naechste Person sie kennt.
        code = "\n".join(z for z in text.splitlines()
                         if not z.lstrip().startswith("#"))
        # Nur bash ist auf dem Mac alt. Fuer ein zsh-Skript waere diese Liste
        # keine Vorsicht, sondern ein Verbot ohne Grund.
        if shebang == b"#!/bin/bash\n":
            gefunden = [grund for muster, grund in nur_bash4.items()
                        if re.search(muster, code)]
            assert not gefunden, f"{skript.name} braucht bash 4: " + ", ".join(gefunden)

        zeilen = text.splitlines()
        befehle = [z.strip() for z in zeilen
                   if z.strip() and not z.strip().startswith("#")]
        assert befehle[0] == "set -u", f"{skript.name} beginnt mit {befehle[0]!r}"

        # Das cd muss nicht die erste Zeile sein - die Funktionsdefinitionen
        # stehen bewusst davor, damit auch der frueheste Abbruch schon einen
        # Satz sagen kann. Es muss aber vor dem ersten Befehl stehen, der
        # etwas anfasst: ein doppelgeklicktes .command startet im
        # Benutzerordner, und was davor zugreift, greift dort zu.
        #
        # Denselben Gedanken schreiben die Shells verschieden: bash nimmt
        # dirname "$0", zsh nimmt ${0:A:h} und loest dabei sogar noch
        # Verknuepfungen auf. Gemeint ist beidemal "der Ordner, in dem ich
        # liege". Der Weg darf ueber eine Variable gehen - dann zaehlt die
        # Zeile, die diese Variable benutzt.
        greift_zu = re.compile(r"\s*(mkdir|rm|curl|open|touch|mv|cp)\s")
        aus_dollar_null = re.compile(r'\$\(dirname "\$0"\)|\$\{0:A:h\}')
        ueber_variable = [m.group(1) for z in zeilen
                          if aus_dollar_null.search(z)
                          and (m := re.match(r"([A-Za-z_]\w*)=", z.strip()))]
        wechsel = next((i for i, z in enumerate(zeilen)
                        if z.strip().startswith("cd ")
                        and (aus_dollar_null.search(z)
                             or any(name in z for name in ueber_variable))), None)
        assert wechsel is not None, f"{skript.name} wechselt nie in seinen Ordner"
        zugriff = next((i for i, z in enumerate(zeilen)
                        if greift_zu.match(z) and not z.lstrip().startswith("#")), None)
        if zugriff is not None:
            assert wechsel < zugriff, (
                f"{skript.name}: Zeile {zugriff + 1} greift auf Dateien zu, bevor "
                f"Zeile {wechsel + 1} in den richtigen Ordner wechselt")
