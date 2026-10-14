#!/bin/bash
#
# Mit einem Kind arbeiten — Mac.
#
# Doppelklicken. Fragt nach der Kennung des Kindes und startet den
# Aufgabendurchlauf im Fenster.
#
# Warum es diese Datei gibt: START-MAC.command oeffnet die Analyse-
# oberflaeche — also die Ansicht auf das, was schon erhoben wurde. Die
# Erhebung selbst laeuft im Fenster, und sie war vorher nur ueber einen
# Befehl in der README erreichbar. Wer dieses Programm benutzen soll, ohne
# ein Terminal zu bedienen, kam damit an das eigentliche Werkzeug nicht
# heran.
#
# Wie START-MAC.command: fuer /bin/bash 3.2.57 geschrieben.

set -u

sag() { printf '%s\n' "$*"; }

trennlinie() { printf '\n%s\n\n' "────────────────────────────────────────────────────────"; }

warte_auf_enter() {
  printf '\n'
  if [ -t 0 ]; then
    read -r -p "Zum Schliessen die Eingabetaste druecken. " _ || true
  fi
}

abbruch() {
  printf '\n'
  printf '  %s\n' "$@" >&2
  warte_auf_enter
  exit 1
}

cd "$(dirname "$0")" 2>/dev/null || abbruch \
  "Der Ordner dieses Startsymbols laesst sich nicht oeffnen."

for noetig in pyproject.toml content ui src; do
  [ -e "$noetig" ] || abbruch \
    "Diese Startdatei liegt nicht mehr in ihrem Ordner." \
    "" \
    "Sie gehoert in den entpackten Programmordner, zusammen mit allem" \
    "anderen, was beim Auspacken entstanden ist. Alleine kann sie nichts tun." \
    "" \
    "An dieser Stelle fehlt: $noetig"
done

clear 2>/dev/null || true
sag ""
sag "  Mit einem Kind arbeiten"
sag "  Kompetenzanalyse — Zahl und Operation"
trennlinie

# Diese Datei richtet bewusst nichts ein. Wer hier landet, ohne dass das
# Programm bereit ist, soll den einen Weg gehen, den die Anleitung kennt —
# und nicht zwei Startsymbole haben, die beide dasselbe koennen.
[ -x .venv/bin/python ] || abbruch \
  "Das Programm ist auf diesem Mac noch nicht eingerichtet." \
  "" \
  "Bitte zuerst einmal START-MAC.command doppelklicken und warten, bis" \
  "sich die Oberflaeche im Browser oeffnet. Danach geht es hier weiter."

[ -f mathkomp.sqlite3 ] || abbruch \
  "Die Datenbank fehlt noch." \
  "" \
  "Bitte zuerst einmal START-MAC.command doppelklicken."

MATHKOMP=(.venv/bin/python -m mathkomp)

# ------------------------------------------------------------- Die Kennung

# §86: gespeichert wird eine pseudonyme Kennung, nie ein Klarname. Das
# Programm kann das nicht nachpruefen — es sieht nur eine Zeichenkette.
# Deshalb steht der Hinweis hier, wo die Entscheidung faellt, und nicht in
# einer Fussnote.
sag "  Unter welcher Kennung soll gearbeitet werden?"
sag ""
sag "  Ein Kuerzel, kein Name — zum Beispiel KIND-01 oder A3."
sag "  Der echte Name des Kindes darf hier nicht stehen und wird vom"
sag "  Programm auch nirgends gebraucht."
sag ""
sag "  Eine bekannte Kennung setzt die Arbeit fort, eine neue beginnt neu."
sag ""

KENNUNG=""
while [ -z "$KENNUNG" ]; do
  read -r -p "  Kennung: " KENNUNG || abbruch "Abgebrochen."
  if [ -z "$KENNUNG" ]; then
    sag "  Ohne Kennung geht es nicht."
  fi
done

sag ""
sag "  In welcher Klassenstufe ist das Kind?"
sag "  Das ist nur ein Bezugsrahmen, keine Erwartung (§87)."
sag "  Leer lassen ist erlaubt."
sag ""
read -r -p "  Klassenstufe (z. B. 3, oder leer): " STUFE || STUFE=""

# Das Array wird aufgebaut, nicht zusammengestueckelt: so bleiben Leerzeichen
# in der Kennung heil, und eine leere Klassenstufe wird gar nicht erst
# uebergeben statt als leeres Argument.
BEFEHL=("${MATHKOMP[@]}" session "$KENNUNG")
if [ -n "$STUFE" ]; then
  BEFEHL=("${BEFEHL[@]}" --grade "$STUFE")
fi

trennlinie
sag "  Es geht los. Zum vorzeitigen Beenden: ctrl und C zusammen druecken."
sag "  Alles bis dahin bleibt gespeichert."
trennlinie

"${BEFEHL[@]}"
ENDE=$?

trennlinie
if [ "$ENDE" -ne 0 ]; then
  sag "  Der Durchlauf wurde mit einer Meldung beendet (siehe oben)."
else
  sag "  Fertig. Was dabei herausgekommen ist, zeigt START-MAC.command"
  sag "  in der Analyseoberflaeche — dort oben die Kennung '$KENNUNG'"
  sag "  auswaehlen."
fi
warte_auf_enter
