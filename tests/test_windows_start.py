"""Die Windows-Startsymbole: dass sie startbar sind, und dass sie nichts loeschen.

Warum eine eigene Datei: test_portabilitaet.py prueft die Uebergabe an einen
Mac und stellt dabei ueberall die umgekehrte Forderung - LF statt CRLF,
Ausfuehrungsrecht, Shebang. Die beiden Regelwerke in eine Datei zu legen
hiesse, in jedem zweiten Test eine Ausnahme zu formulieren.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "src"))
from mathkomp import cli  # noqa: E402


def _start_modul():
    """tools/start.py laden, ohne dass tools ein Paket sein muss."""
    spec = importlib.util.spec_from_file_location(
        "_start_unter_test", ROOT / "tools" / "start.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


# ------------------------------------------------------------ Die Huellen


def test_beide_startsymbole_sind_auf_einem_windows_pc_startbar():
    """Eine .bat scheitert nicht, sie tut lautlos etwas anderes.

    Deshalb wird hier nicht auf Fehlerfreiheit geprueft, sondern auf die
    Abwesenheit genau der Konstruktionen, die gemessen still danebengehen.
    """
    skripte = sorted(ROOT.glob("*.bat"))
    assert len(skripte) >= 2, f"Erwartet werden zwei Startsymbole, gefunden: {skripte}"

    #: Was in einer .bat lautlos etwas anderes tut. Die Begruendung zu jedem
    #: Eintrag steht im Kopf von tools/start.py.
    STILL_FALSCH = {
        "call :": "call kehrt zurueck - ein exit /b dahinter bricht nicht ab",
        "set /p": "set /p fuehrt Eingetipptes aus und behaelt bei leerer Eingabe den alten Wert",
        "EnableDelayedExpansion": "loescht jedes Ausrufezeichen aus den Pfaden",
        "^": "im Klammerblock wird der Trenner zu Text",
        "%ERRORLEVEL%": "wird beim Einlesen ersetzt, also vor der Ausfuehrung",
    }

    for skript in skripte:
        roh = skript.read_bytes()

        assert not roh.startswith(b"\xef\xbb\xbf"), f"{skript.name}: BOM zerlegt die erste Zeile"
        fremd = [(i, b) for i, b in enumerate(roh) if b > 0x7F]
        assert not fremd, (
            f"{skript.name}: Zeichen ausserhalb ASCII an {fremd[:3]} - eine Konsole "
            "liest eine .bat in der Codepage 850, nicht in UTF-8")

        assert b"\r\n" in roh, f"{skript.name}: keine Windows-Zeilenenden"
        assert roh.count(b"\n") == roh.count(b"\r\n"), (
            f"{skript.name}: einzelne LF ohne CR - die .editorconfig des Projekts "
            "schreibt LF vor, fuer *.bat muss der Abschnitt sie ueberstimmen")

        # Eine .bat, die durch eine POSIX-Werkzeugkette gelaufen ist, sieht
        # richtig aus und tut etwas anderes: aus 2>nul wird 2>/dev/null.
        for rest in (b"/dev/", b"#!/"):
            assert rest not in roh, f"{skript.name}: POSIX-Rest {rest!r} im Text"

        text = roh.decode("ascii")
        code = "\n".join(z for z in text.splitlines()
                         if not z.strip().lower().startswith("rem "))

        for muster, grund in STILL_FALSCH.items():
            assert muster not in code, f"{skript.name}: {muster!r} - {grund}"

        # Klammerbloecke sind der Ort, an dem fast alle dieser Fallen
        # zuschnappen. Eine Huelle braucht keine.
        for zeile in code.splitlines():
            nackt = zeile.strip()
            assert not nackt.endswith("("), (
                f"{skript.name}: Klammerblock in {nackt!r} - jede Fehlerbehandlung "
                "gehoert auf ein eigenes Label")

        befehle = [z.strip() for z in code.splitlines() if z.strip()]
        assert befehle[0] == "@echo off", f"{skript.name} beginnt mit {befehle[0]!r}"
        assert 'cd /d "%~dp0"' in befehle, (
            f"{skript.name} wechselt nie in seinen eigenen Ordner")

        # Die Huelle bleibt duenn. Waechst sie, wandert Logik zurueck nach
        # cmd - und dieser Test ist die einzige Stelle, die das bemerkt.
        assert len(befehle) <= 40, (
            f"{skript.name} hat {len(befehle)} Befehlszeilen. Alles, was eine "
            "Bedingung oder eine Eingabe braucht, gehoert nach tools/*.py")

        assert "pause" in code, f"{skript.name}: ohne pause verschwindet jede Meldung"


def test_jedes_startsymbol_ruft_seine_eigene_python_datei():
    paare = {
        "START-WINDOWS.bat": "tools\\start.py",
        "SITZUNG-WINDOWS.bat": "tools\\sitzung.py",
    }
    for name, ziel in paare.items():
        text = (ROOT / name).read_text(encoding="ascii")
        assert ziel in text, f"{name} ruft {ziel} nicht auf"
        assert (ROOT / ziel.replace("\\", "/")).is_file(), f"{ziel} fehlt"


def test_start_py_laeuft_auch_unter_einem_zu_alten_python():
    """Der Versionshinweis muss ankommen, nicht am Einlesen scheitern.

    tools/start.py laeuft unter dem Python des Rechners - notfalls einem zu
    alten. Enthaelt die Datei Syntax, die dieses Python noch nicht kennt,
    bekommt die Person statt des deutschen Hinweises einen englischen
    SyntaxError, und das Fenster ist weg, bevor sie ihn liest.
    """
    quelle = (ROOT / "tools" / "start.py").read_text(encoding="utf-8")
    # 3.8 ist bewusst aelter als die eigene Untergrenze von 3.11: der
    # Hinweis soll auch dort noch lesbar herauskommen.
    compile(quelle, "start.py", "exec", dont_inherit=True)
    for neu in ("match ", ":=", "->", "list[", "dict[", "str | "):
        assert neu not in quelle, (
            f"{neu!r} in tools/start.py - ein aelteres Python bricht damit schon "
            "beim Einlesen ab, statt den Versionshinweis zu zeigen")


# ------------------------------------------------- Die Zusage aus §86


def _datenbank(pfad: Path, tabellen: dict[str, int]) -> Path:
    conn = sqlite3.connect(pfad)
    for name, zeilen in tabellen.items():
        conn.execute(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
        for i in range(zeilen):
            conn.execute(f"INSERT INTO {name} VALUES ({i + 1})")
    conn.commit()
    conn.close()
    return pfad


def test_windows_start_loescht_nur_was_nachweislich_leer_ist(tmp_path):
    """Die Richtung, in die die Unsicherheit faellt, ist hier alles.

    Eine fruehere Fassung fing jede Ausnahme ab und wertete sie als "leer,
    darf weg". Eine Datenbank kann aber auch deshalb unlesbar sein, weil
    nebenan eine Sitzung laeuft oder ein Virenscanner sie festhaelt - und
    dann stehen erhobene Daten darin, die aus content/ nicht zurueckkommen.
    """
    start = _start_modul()

    fehlt = tmp_path / "gibtsnicht.sqlite3"
    assert start.datenbank_pruefen(str(fehlt)) == start.LEER

    leer = _datenbank(tmp_path / "leer.sqlite3",
                      {"students": 0, "competencies": 0})
    assert start.datenbank_pruefen(str(leer)) == start.LEER

    fertig = _datenbank(tmp_path / "fertig.sqlite3",
                        {"students": 3, "competencies": 40})
    assert start.datenbank_pruefen(str(fertig)) == start.BRAUCHBAR

    # Ein Kind angelegt, aber der Fachinhalt fehlt: unbrauchbar - und
    # trotzdem unantastbar.
    halb = _datenbank(tmp_path / "halb.sqlite3", {"students": 1})
    assert start.datenbank_pruefen(str(halb)) == start.MIT_DATEN

    kaputt = tmp_path / "kaputt.sqlite3"
    kaputt.write_bytes(b"SQLite format 3\x00" + b"\x17" * 4000)
    assert start.datenbank_pruefen(str(kaputt)) == start.MIT_DATEN


@pytest.mark.parametrize("tabelle", cli.USER_STATE_TABELLEN)
def test_daten_in_jeder_einzelnen_erhebungstabelle_schuetzen_die_datei(
        tmp_path, tabelle):
    """Nicht nur ``students`` zaehlt.

    Ein abgebrochener Durchlauf kann Versuche hinterlassen haben, bevor das
    Kind angelegt war. Die alte Fassung fragte nur nach ``students``, haette
    diese Datei fuer leer gehalten und geloescht.
    """
    start = _start_modul()
    pfad = _datenbank(tmp_path / f"{tabelle}.sqlite3", {tabelle: 1})
    assert start.datenbank_pruefen(str(pfad)) == start.MIT_DATEN, (
        f"Daten in {tabelle} schuetzen die Datei nicht")


def test_beide_startsymbole_kennen_dieselben_erhebungstabellen():
    """Mac und Windows muessen dieselbe Zusage geben.

    Sonst loescht das eine Startsymbol, was das andere schuetzt - und welches
    davon jemand doppelklickt, ist Zufall.
    """
    start = _start_modul()
    assert set(start.ERHEBUNGSTABELLEN) == set(cli.USER_STATE_TABELLEN), (
        "tools/start.py und cli.USER_STATE_TABELLEN sind auseinandergelaufen")

    mac = (ROOT / "START-MAC.command").read_text(encoding="utf-8")
    for tabelle in cli.USER_STATE_TABELLEN:
        assert f'"{tabelle}"' in mac, (
            f"START-MAC.command fragt nicht nach {tabelle} - die Mac-Fassung "
            "gibt damit eine schwaechere Zusage als die Windows-Fassung")
    assert "quick_check" in mac, (
        "START-MAC.command prueft die Datei nicht auf Unversehrtheit, bevor es "
        "sie fuer leer erklaert")


# ------------------------------------------------------- Die Fehlertabelle


def test_anleitung_windows_zitiert_keine_meldung_die_es_nicht_gibt():
    """Dieselbe Pruefung wie fuer den Mac, fuer die zweite Anleitung.

    Sie hat sich sofort bewaehrt: als die Abbruchmeldung zur Datenbank
    umformuliert wurde, zitierten beide Anleitungen noch den alten Wortlaut -
    und wer danach im Fenster gesucht haette, haette nichts gefunden.

    Fremde Woerter sind hier haeufiger als beim Mac, weil auf dem Weg zum
    Doppelklick Windows selbst mitredet. Sie stehen unten namentlich, damit
    ein Tippfehler in einem eigenen Zitat nicht als "fremd" durchrutscht.
    """
    import re

    anleitung = (ROOT / "ANLEITUNG-WINDOWS.md").read_text(encoding="utf-8")
    quellen = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("tools/start.py", "tools/sitzung.py",
                     "START-WINDOWS.bat", "SITZUNG-WINDOWS.bat",
                     "ui/index.html"))

    #: Wortlaut, den nicht dieses Programm schreibt, sondern Windows oder
    #: der Browser.
    FREMD = {
        "Datei \u00f6ffnen \u2013 Sicherheitswarnung",
        "Batchvorgang abbrechen (J/N)?",
        "nicht erreichbar",
        "l\u00e4sst",
    }

    zitate = re.findall(r"\u201e([^\u201c\"]+)\"", anleitung)
    assert len(zitate) >= 10, f"Nur {len(zitate)} Zitate gefunden - greift das Muster noch?"

    fehlend = [z for z in zitate
               if z.rstrip(" \u2026").strip() not in quellen and z not in FREMD]
    assert not fehlend, (
        "Die Anleitung zitiert Meldungen, die so nirgends erscheinen:\n"
        + "\n".join(f"  \u201e{z}\u201c" for z in fehlend))
