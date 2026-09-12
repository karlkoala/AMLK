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
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mathkomp import cli, db, importer, server  # noqa: E402

CONTENT = ROOT / "content"


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
        assert conn.execute("SELECT COUNT(*) FROM competencies").fetchone()[0] == 54
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
    assert conn.execute("SELECT COUNT(*) FROM competencies").fetchone()[0] == 54
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
