"""Packt den Uebergabestand als ZIP fuer einen Mac.

Warum nicht einfach `Compress-Archive`: ein ZIP aus PowerShell speichert keine
Unix-Rechte. Die .command-Dateien kaemen damit ohne Ausfuehrungsrecht an, und ein
Doppelklick darauf oeffnete den Text im Editor statt das Programm zu starten.
Die Datei hier setzt das Recht ausdruecklich (0755) und legt alles unter einen
Ordner `mathkomp/`, damit beim Entpacken auf dem Mac immer derselbe Name
herauskommt — die Anleitung kann sich dann darauf berufen.

Nicht mitgepackt wird alles, was auf dem Zielrechner neu entsteht: Bytecode,
Testzwischenstaende, die virtuelle Umgebung — und `mathkomp.sqlite3`. Diese
Datei enthaelt erhobene Daten (§86) und laesst sich aus `content/` vollstaendig
neu erzeugen; wird sie mituebergeben, liefert `simulate` ausserdem ein falsches
Ergebnis (siehe ENTSCHEIDUNGEN.md, D-53).

    py tools/paket_fuer_mac.py
"""

from __future__ import annotations

import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIEL = ROOT.parent / "mathkomp-fuer-mac.zip"

#: Oberster Ordner im Archiv. Beim Entpacken heisst der Ordner auf dem Mac
#: genauso - darauf beruft sich die Anleitung.
PAKETNAME = "mathkomp"

MITNEHMEN = ("content", "src", "tests", "tools", "ui")
EINZELDATEIEN = (
    "pyproject.toml", "README.md", "ANLEITUNG-MAC.md", "ENTSCHEIDUNGEN.md",
    "OFFENE_FRAGEN.md", "SPEC_VOLLTEXT.txt",
    "START-MAC.command", "SITZUNG-MAC.command",
    ".editorconfig", ".gitignore",
)

AUSLASSEN_ORDNER = {"__pycache__", ".pytest_cache", ".venv", ".git", "node_modules"}
AUSLASSEN_ENDUNGEN = {".pyc", ".pyo", ".sqlite3"}
AUSLASSEN_NAMEN = {".DS_Store"}

#: Ausfuehrbar, weil sie doppelgeklickt werden.
AUSFUEHRBAR = (".command", ".sh")


def uebernehmen(pfad: Path) -> bool:
    if pfad.name in AUSLASSEN_NAMEN or pfad.suffix.lower() in AUSLASSEN_ENDUNGEN:
        return False
    return not any(teil in AUSLASSEN_ORDNER for teil in pfad.parts)


def sammeln() -> list[Path]:
    dateien: list[Path] = []
    for ordner in MITNEHMEN:
        wurzel = ROOT / ordner
        if not wurzel.is_dir():
            raise SystemExit(f"Ordner fehlt: {wurzel}")
        dateien += [p for p in sorted(wurzel.rglob("*")) if p.is_file() and uebernehmen(p)]
    for name in EINZELDATEIEN:
        pfad = ROOT / name
        if not pfad.is_file():
            raise SystemExit(f"Datei fehlt: {pfad}")
        dateien.append(pfad)
    return dateien


def zeilenenden_pruefen(dateien: list[Path]) -> None:
    """Ein Startskript mit CRLF scheitert auf dem Mac an seiner eigenen ersten Zeile.

    Die Fehlermeldung lautet dann ``/bin/bash^M: bad interpreter`` und sagt
    niemandem etwas. Ein Editor unter Windows macht das ungefragt, deshalb wird
    es hier vor dem Packen geprueft und nicht erst dort bemerkt.
    """
    kaputt = [p for p in dateien
              if p.suffix.lower() in AUSFUEHRBAR and b"\r\n" in p.read_bytes()]
    if kaputt:
        raise SystemExit(
            "Windows-Zeilenenden in einem Startskript - auf dem Mac nicht lauffaehig:\n"
            + "\n".join(f"  {p.relative_to(ROOT)}" for p in kaputt))


def packen(ziel: Path = ZIEL) -> None:
    dateien = sammeln()
    zeilenenden_pruefen(dateien)

    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archiv:
        for pfad in dateien:
            innen = f"{PAKETNAME}/{pfad.relative_to(ROOT).as_posix()}"
            eintrag = zipfile.ZipInfo(innen, date_time=(2026, 1, 1, 0, 0, 0))
            eintrag.compress_type = zipfile.ZIP_DEFLATED
            rechte = 0o755 if pfad.suffix.lower() in AUSFUEHRBAR else 0o644
            # Die oberen 16 Bit von external_attr sind der Unix-Modus. Ohne
            # sie kommt jede Datei mit den Vorgaberechten des Entpackers an.
            eintrag.external_attr = (stat.S_IFREG | rechte) << 16
            # ... und ohne die Hostkennung "Unix" liest sie niemand. ZipInfo
            # setzt sie unter Windows auf 0 (MS-DOS); ein Entpacker wertet den
            # Modus dann nicht aus und vergibt eigene Vorgaberechte. Das
            # Ausfuehrungsrecht waere gesetzt, aber nicht adressiert - der
            # Doppelklick auf dem Mac oeffnete den Text im Editor.
            eintrag.create_system = 3
            archiv.writestr(eintrag, pfad.read_bytes())

    nachsehen(ziel)

    groesse = ziel.stat().st_size
    print(f"{ziel}")
    print(f"{len(dateien)} Dateien, {groesse / 1024 / 1024:.1f} MB")


def nachsehen(ziel: Path) -> None:
    """Das fertige Archiv aufmachen und die Rechte dort ablesen.

    Die Zeile "ausfuehrbar: ..." stand hier frueher aus der Endungsliste -
    gemeldet wurde also die Absicht, nie das Ergebnis. Genau darin liegt der
    Fehler, der lange unbemerkt blieb: der Modus war gesetzt, die Hostkennung
    aber MS-DOS, und damit las ihn kein Entpacker. Was hier steht, ist jetzt
    aus dem Archiv gelesen.
    """
    with zipfile.ZipFile(ziel) as archiv:
        eintraege = [e for e in archiv.infolist()
                     if Path(e.filename).suffix.lower() in AUSFUEHRBAR]
        if not eintraege:
            raise SystemExit("Kein Startskript im Archiv - der Doppelklick haette nichts zu klicken.")
        for e in eintraege:
            modus = e.external_attr >> 16
            if e.create_system != 3 or not modus & 0o111:
                raise SystemExit(
                    f"{e.filename} kaeme ohne Ausfuehrungsrecht an "
                    f"(Hostkennung {e.create_system}, Modus {modus:o}).")
            print(f"  ausfuehrbar: {e.filename}  ({modus & 0o777:o}, Unix)")


if __name__ == "__main__":
    sys.exit(packen())
