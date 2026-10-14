# -*- coding: utf-8 -*-
"""Mit einem Kind arbeiten - auf einem Windows-PC.

Das, was hinter dem Doppelklick auf SITZUNG-WINDOWS.bat steckt.

Warum es diese Datei gibt: START-WINDOWS.bat oeffnet die Analyseoberflaeche,
also die Ansicht auf das, was schon erhoben wurde. Die Erhebung selbst laeuft
im Fenster, und sie waere sonst nur ueber einen Befehl in der README
erreichbar. Wer dieses Programm benutzen soll, ohne eine Eingabeaufforderung
zu bedienen, kaeme an das eigentliche Werkzeug nicht heran.

Warum die Abfrage hier steht und nicht in der .bat: `set /p` in cmd.exe
fuehrt aus, was jemand eintippt, und laesst bei leerer Eingabe den vorigen
Wert stehen - in diesem Zusammenhang waere das die Kennung des vorigen
Kindes. Ausserdem zeigt cmd nicht zuverlaessig an, was tatsaechlich
ankommt: aus eingetipptem A^B wird am Bildschirm AB, waehrend das Programm
A^B bekaeme. Bei einer pseudonymen Kennung, die nachvollziehbar bleiben
muss (§86), ist das nicht hinnehmbar. Pythons input() liest Text als Text.
"""

import os
import subprocess
import sys

from start import (DATENBANK, abbruch, in_den_eigenen_ordner, sag,
                   standort_pruefen, trennlinie, venv_python,
                   warte_auf_enter, _umgebung)


def kennung_erfragen():
    """§86: gespeichert wird eine pseudonyme Kennung, nie ein Klarname.

    Das Programm kann das nicht nachpruefen - es sieht nur eine Zeichenkette.
    Deshalb steht der Hinweis hier, wo die Entscheidung faellt, und nicht in
    einer Fussnote. Eine Namenserkennung waere das Gegenteil einer Abhilfe:
    sie wuerde eine Sicherheit vortaeuschen, die es nicht gibt, und
    ausgerechnet an Kuerzeln scheitern, die wie Namen aussehen.
    """
    sag("  Unter welcher Kennung soll gearbeitet werden?")
    sag("")
    sag("  Ein Kuerzel, kein Name - zum Beispiel KIND-01 oder A3.")
    sag("  Der echte Name des Kindes darf hier nicht stehen und wird vom")
    sag("  Programm auch nirgends gebraucht.")
    sag("")
    sag("  Eine bekannte Kennung setzt die Arbeit fort, eine neue beginnt neu.")
    sag("")

    while True:
        try:
            kennung = input("  Kennung: ").strip()
        except (EOFError, KeyboardInterrupt):
            sag("")
            abbruch("Abgebrochen. Es wurde nichts gespeichert.")
        if kennung:
            return kennung
        sag("  Ohne Kennung geht es nicht.")


def stufe_erfragen():
    sag("")
    sag("  In welcher Klassenstufe ist das Kind?")
    sag("  Das ist nur ein Bezugsrahmen, keine Erwartung (§87).")
    sag("  Leer lassen ist erlaubt.")
    sag("")
    try:
        return input("  Klassenstufe (z. B. 3, oder leer): ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def main():
    ordner = in_den_eigenen_ordner()
    standort_pruefen()

    sag("")
    sag("  Mit einem Kind arbeiten")
    sag("  Kompetenzanalyse - Zahl und Operation")
    trennlinie()

    # Diese Datei richtet bewusst nichts ein. Wer hier landet, ohne dass das
    # Programm bereit ist, soll den einen Weg gehen, den die Anleitung kennt -
    # und nicht zwei Startsymbole haben, die beide dasselbe koennen.
    python = venv_python(ordner)
    if not os.path.isfile(python):
        abbruch(
            "Das Programm ist auf diesem PC noch nicht eingerichtet.",
            "",
            "Bitte zuerst einmal START-WINDOWS.bat doppelklicken und warten,",
            "bis sich die Oberflaeche im Browser oeffnet. Danach geht es hier",
            "weiter.")

    if not os.path.isfile(DATENBANK):
        abbruch(
            "Die Datenbank fehlt noch.",
            "",
            "Bitte zuerst einmal START-WINDOWS.bat doppelklicken.")

    kennung = kennung_erfragen()
    stufe = stufe_erfragen()

    # Zurueckzeigen, was gespeichert wird. Das ist der eigentliche Gewinn
    # gegenueber der cmd-Fassung: die Person sieht die Kennung genau so, wie
    # sie in der Datenbank landet - Sonderzeichen eingeschlossen.
    trennlinie()
    sag("  Gespeichert wird unter der Kennung:  " + kennung)
    if stufe:
        sag("  Bezugsrahmen Klassenstufe:           " + stufe)
    sag("")
    sag("  Es geht los. Zum vorzeitigen Beenden: strg und C zusammen")
    sag("  druecken. Danach wird zweimal nachgefragt - erst nach der")
    sag("  Eingabetaste, dann von Windows selbst mit 'Batchvorgang")
    sag("  abbrechen (J/N)?'; dort J eintippen und Eingabetaste.")
    sag("  Alles bis dahin bleibt gespeichert.")
    trennlinie()

    befehl = [python, "-m", "mathkomp", "--db", DATENBANK, "session", kennung]
    if stufe:
        befehl += ["--grade", stufe]

    try:
        ende = subprocess.call(befehl, env=_umgebung())
    except KeyboardInterrupt:
        ende = 0

    trennlinie()
    # Nicht `!= 0` allein pruefen und dann "Fertig" sagen: bricht jemand mit
    # strg-c ab, ist der Rueckgabewert auf Windows stark negativ. Ein
    # `if errorlevel 1` in cmd haette das durchgelassen und ausgerechnet im
    # ungewoehnlichen Fall die falsche Auskunft gegeben.
    if ende != 0:
        sag("  Der Durchlauf wurde vorzeitig beendet.")
        sag("  Alles, was bis dahin beantwortet wurde, ist gespeichert.")
    else:
        sag("  Fertig. Was dabei herausgekommen ist, zeigt")
        sag("  START-WINDOWS.bat in der Analyseoberflaeche - dort oben die")
        sag("  Kennung '" + kennung + "' auswaehlen.")
    warte_auf_enter()
    return 0


if __name__ == "__main__":
    # Kein sys.path-Eingriff noetig: wird eine Datei ueber ihren Pfad
    # aufgerufen, stellt Python ihren Ordner selbst an den Anfang des
    # Suchpfads. Der Import von start.py oben findet sie deshalb - und er
    # muss oben stehen, weil ein Eingriff hier unten laengst zu spaet kaeme.
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sag("")
        sag("  Abgebrochen.")
        warte_auf_enter()
        sys.exit(1)
