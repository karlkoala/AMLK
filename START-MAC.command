#!/bin/bash
#
# Kompetenzanalyse starten — Mac.
#
# Doppelklicken. Beim ersten Mal richtet dieses Skript alles ein (das dauert
# ein bis zwei Minuten), danach startet es nur noch. Es ist derselbe Klick,
# immer.
#
# Was es tut, in einem Satz: es legt neben dem Programm eine abgeschlossene
# Arbeitsumgebung an (.venv), baut die Datenbank aus dem Inhalt in content/
# und oeffnet die Analyseoberflaeche im Browser. Es laedt nichts aus dem Netz
# ausser den Paketen, die "pip" braucht, und es aendert nichts ausserhalb
# dieses Ordners.
#
# Geschrieben fuer /bin/bash, und das ist auf macOS bis heute 3.2.57 — also
# keine assoziativen Arrays, kein mapfile, kein ${x^^}. Festgehalten in
# tests/test_portabilitaet.py.

set -u

# --------------------------------------------------------------- Sprechen

# Die Funktionen stehen vor allem anderen, damit auch der frueheste Abbruch
# schon einen Satz sagen kann statt nur stumm zu verschwinden.

sag() { printf '%s\n' "$*"; }

trennlinie() { printf '\n%s\n\n' "────────────────────────────────────────────────────────"; }

warte_auf_enter() {
  printf '\n'
  # Ohne Tastatur (etwa beim Aufruf aus einem anderen Skript) nicht haengen.
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

# --------------------------------------------------------------- Standort

# Ein doppelgeklicktes .command startet im Benutzerordner, nicht dort, wo es
# liegt. Ohne diese Zeile sucht das Skript alles an der falschen Stelle.
cd "$(dirname "$0")" 2>/dev/null || abbruch \
  "Der Ordner dieses Startsymbols laesst sich nicht oeffnen."

# Wird nur diese eine Datei irgendwohin gezogen — auf den Schreibtisch, ins
# Dock, in einen anderen Ordner —, dann fehlt drumherum alles. Ohne diese
# Probe legt das Skript am neuen Ort eine Arbeitsumgebung an, scheitert
# spaeter und beschuldigt dafuer die Internetverbindung.
for noetig in pyproject.toml content ui src; do
  [ -e "$noetig" ] || abbruch \
    "Diese Startdatei liegt nicht mehr in ihrem Ordner." \
    "" \
    "Sie gehoert in den Ordner 'mathkomp', zusammen mit allem anderen, was" \
    "beim Auspacken entstanden ist. Alleine kann sie nichts tun." \
    "" \
    "An dieser Stelle fehlt: $noetig"
done

PORT=8765
ORDNER="$(pwd)"
PROTOKOLL="einrichtung.log"

clear 2>/dev/null || true
sag ""
sag "  Kompetenzanalyse — Zahl und Operation"
sag "  $ORDNER"
trennlinie

# ------------------------------------------------------- Laeuft es schon?

# Der zweite Doppelklick ist der haeufigste Handgriff ueberhaupt: es dauert
# jemandem zu lange, oder das Fenster ist hinter dem Browser verschwunden.
# Ohne diese Abfrage stirbt der zweite Lauf an einem belegten Port und meldet
# einen Fehler, waehrend die Oberflaeche daneben tadellos laeuft.
#
# Gefragt wird nicht "antwortet irgendwer auf 8765", sondern ob es dieses
# Programm ist — /api/catalog hat sonst niemand.
if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/api/catalog" 2>/dev/null; then
  sag "  Das Programm laeuft bereits in einem anderen Fenster."
  sag "  Die Oberflaeche wird dort erneut geoeffnet."
  open "http://127.0.0.1:$PORT/" 2>/dev/null
  trennlinie
  sag "  Dieses Fenster hier wird nicht gebraucht und kann geschlossen werden."
  warte_auf_enter
  exit 0
fi

# ----------------------------------------------------------------- Sperre

# Zwei Doppelklicks kurz hintereinander, waehrend die Einrichtung laeuft: das
# zweite Fenster wuerde .venv mitten im Aufbau loeschen, und das erste meldete
# dafuer eine fehlende Internetverbindung. Die Sperre ist ein Ordner, weil
# mkdir auf jedem Dateisystem unteilbar ist.
sperre_nehmen() {
  local alt
  if mkdir .start.lock 2>/dev/null; then
    printf '%s' "$$" > .start.lock/pid
    return 0
  fi
  # Eine Sperre kann von einem abgestuerzten Lauf stehengeblieben sein. Dann
  # gehoert sie niemandem mehr und muss weg — sonst startet hier nie wieder
  # etwas, und das waere schlimmer als das Problem, das sie loest.
  alt="$(cat .start.lock/pid 2>/dev/null || true)"
  if [ -n "$alt" ] && kill -0 "$alt" 2>/dev/null; then
    return 1
  fi
  rm -rf .start.lock
  mkdir .start.lock 2>/dev/null || return 1
  printf '%s' "$$" > .start.lock/pid
  return 0
}

sperre_nehmen || abbruch \
  "Das Programm wird gerade in einem anderen Fenster gestartet." \
  "" \
  "Bitte dort warten, bis die Oberflaeche im Browser erscheint." \
  "Dieses Fenster hier kann geschlossen werden."

BROWSER_PID=""

aufraeumen() {
  if [ -n "$BROWSER_PID" ]; then
    kill "$BROWSER_PID" 2>/dev/null
  fi
  rm -rf .start.lock
}
trap aufraeumen EXIT

# ----------------------------------------------------------------- Python

# Mindestens 3.11. Was macOS selbst mitbringt (/usr/bin/python3) ist 3.9 und
# damit zu alt; es wird hier bewusst nicht einmal angefasst, weil der blosse
# Aufruf ohne installierte Entwicklerwerkzeuge ein Systemfenster oeffnet.
python_taugt() {
  "$1" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)' \
    >/dev/null 2>&1
}

python_suchen() {
  local kandidat pfad
  for kandidat in python3.14 python3.13 python3.12 python3.11; do
    pfad="$(command -v "$kandidat" 2>/dev/null)" || continue
    if python_taugt "$pfad"; then printf '%s' "$pfad"; return 0; fi
  done
  for pfad in /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 \
              /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    [ -x "$pfad" ] || continue
    if python_taugt "$pfad"; then printf '%s' "$pfad"; return 0; fi
  done
  return 1
}

PYTHON="$(python_suchen)" || abbruch \
  "Auf diesem Mac fehlt ein ausreichend neues Python." \
  "" \
  "Gebraucht wird Version 3.11 oder neuer. Das, was macOS selbst" \
  "mitbringt, ist aelter und reicht nicht." \
  "" \
  "So geht es:" \
  "  1. https://www.python.org/downloads/ im Browser oeffnen" \
  "  2. die grosse gelbe Schaltflaeche anklicken (Download Python 3.x)" \
  "  3. die geladene Datei (Endung .pkg) doppelklicken und dem" \
  "     Installationsfenster folgen" \
  "  4. danach dieses Startsymbol hier erneut doppelklicken" \
  "" \
  "Die Installation fragt einmal nach dem Kennwort des Macs. Dafuer muss" \
  "das eigene Konto Administrator sein — fragt das Fenster nach einem" \
  "anderen Benutzernamen, verwaltet jemand anderes diesen Mac."

# Diese Probe steht hier und nicht spaeter: sie gilt dem gefundenen Python,
# und wer sie erst nach dem Einrichten stellt, laesst jemanden zwei Minuten
# lang etwas installieren, das danach ohnehin abgelehnt wird.
# 3.38 ist die Untergrenze, weil das Schema json_valid() in CHECK benutzt.
"$PYTHON" -c 'import sqlite3, sys; sys.exit(0 if sqlite3.sqlite_version_info >= (3, 38) else 1)' \
  >/dev/null 2>&1 || abbruch \
  "Das SQLite dieses Python ist zu alt fuer dieses Programm." \
  "" \
  "Abhilfe: eine aktuelle Python-Version von" \
  "https://www.python.org/downloads/ installieren und erneut starten."

# ------------------------------------------------- Arbeitsumgebung (.venv)

# Die Arbeitsumgebung merkt sich beim Einrichten den absoluten Pfad dieses
# Ordners. Wird er spaeter verschoben, zeigt sie ins Leere; wird er kopiert,
# zeigt sie auf das Original weiter hinten auf der Platte und arbeitet still
# mit fremden Dateien. Deshalb wird hier nicht gefragt, ob sich das Programm
# laden laesst, sondern von wo.
umgebung_brauchbar() {
  [ -x .venv/bin/python ] || return 1
  .venv/bin/python -c '
import pathlib, sys
import mathkomp
hier = pathlib.Path(sys.argv[1]).resolve()
sys.exit(0 if hier in pathlib.Path(mathkomp.__file__).resolve().parents else 1)
' "$ORDNER" >/dev/null 2>&1
}

if ! umgebung_brauchbar; then
  if [ -d .venv ]; then
    sag "  Die Arbeitsumgebung gehoert nicht zu diesem Ordner."
    sag "  (Der Ordner wurde verschoben, umbenannt oder kopiert.)"
    sag "  Sie wird neu angelegt — dafuer wird noch einmal kurz Internet gebraucht."
    rm -rf .venv
  else
    sag "  Erster Start — die Arbeitsumgebung wird eingerichtet."
    sag "  Das dauert ein bis zwei Minuten und braucht einmalig Internet."
  fi
  sag "  Bitte das Fenster offen lassen und nicht noch einmal doppelklicken."
  sag ""

  sag "  … Arbeitsumgebung anlegen"
  "$PYTHON" -m venv .venv || abbruch \
    "Die Arbeitsumgebung liess sich nicht anlegen." \
    "" \
    "Haeufigster Grund auf einem Mac: der Ordner liegt an einer Stelle, auf" \
    "die das Terminal nicht zugreifen darf. Wurde beim Start einmal gefragt," \
    "ob auf Schreibtisch oder Dokumente zugegriffen werden darf, und lautete" \
    "die Antwort 'Nicht erlauben', laesst sich das hier wieder aendern:" \
    "Systemeinstellungen > Datenschutz & Sicherheit > Dateien und Ordner." \
    "" \
    "Einfacher: den ganzen Ordner 'mathkomp' in den Benutzerordner ziehen" \
    "(im Finder: Menue 'Gehe zu' > 'Benutzerordner') und erneut starten."

  # Kein --quiet: das hier ist der einzige lange Schritt, und ein Fenster, das
  # minutenlang nichts schreibt, ist genau das, was jemanden zum Abbrechen
  # bringt. --progress-bar off haelt die Ausgabe ruhig, ohne sie stumm zu
  # machen. --no-cache-dir, damit die Zusage "nichts ausserhalb dieses
  # Ordners" auch wirklich stimmt. Und nur -e "." statt -e ".[dev]": die
  # Testwerkzeuge braucht hier niemand, und jedes Paket weniger ist ein
  # moeglicher Netzfehler weniger.
  sag "  … Programm installieren — der lange Schritt, jetzt laufen Zeilen durch:"
  sag ""
  .venv/bin/python -m pip install --disable-pip-version-check --no-cache-dir \
      --progress-bar off --timeout 20 --retries 2 -e "." \
    || abbruch \
    "Die Installation ist fehlgeschlagen." \
    "" \
    "Besteht gerade eine Internetverbindung? Sie wird nur fuer diesen" \
    "einen Schritt gebraucht, danach laeuft alles ohne Netz." \
    "" \
    "Ist das Netz in Ordnung, sperrt moeglicherweise das Schul- oder" \
    "Firmennetz den Paketserver pypi.org. Dann bitte beim Absender melden" \
    "und die letzten Zeilen oben mitschicken."

  sag ""
  sag "  … fertig."
  sag ""
fi

# Ab hier steht das Programm bereit. Aufgerufen wird es immer ueber den
# Python der Arbeitsumgebung, nie ueber den Namen "mathkomp" allein — der
# haengt daran, ob die Umgebung im Fenster aktiviert ist.
MATHKOMP=(.venv/bin/python -m mathkomp)

# -------------------------------------------------------------- Datenbank

# Frueher stand hier "wenn die Datei fehlt, baue sie". Das war die schlimmste
# Stelle des Skripts: bricht der Aufbau ab — Fenster geschlossen, Content
# fehlerhaft —, bleibt eine Datei mit Schema und ohne Inhalt liegen. Sie
# existiert, also baute der naechste Doppelklick nicht mehr, und die
# Oberflaeche brach mit "0 Kompetenzknoten" ab. Der Zustand heilte nie von
# selbst, und der Ausweg waere ein Befehl im Terminal gewesen.
#
# Deshalb drei Antworten statt zwei: 0 = brauchbar, 1 = unbrauchbar und leer
# (darf weg), 2 = unbrauchbar, aber mit erhobenen Daten darin. Der dritte
# Fall wird niemals automatisch geloescht (§86).
datenbank_pruefen() {
  [ -f mathkomp.sqlite3 ] || return 1
  .venv/bin/python -c '
import sqlite3, sys
try:
    c = sqlite3.connect("file:mathkomp.sqlite3?mode=ro", uri=True)
    inhalt = c.execute("select count(*) from competencies").fetchone()[0]
    kinder = c.execute("select count(*) from students").fetchone()[0]
except Exception:
    sys.exit(1)
if inhalt and kinder:
    sys.exit(0)
sys.exit(2 if kinder else 1)
' >/dev/null 2>&1
}

datenbank_pruefen
ZUSTAND=$?

if [ "$ZUSTAND" -eq 2 ]; then
  abbruch \
    "Die Datenbank in diesem Ordner ist beschaedigt, enthaelt aber bereits" \
    "erhobene Daten. Sie wird deshalb nicht angetastet." \
    "" \
    "Bitte beim Absender melden. Die Datei heisst mathkomp.sqlite3 und" \
    "liegt in diesem Ordner."
fi

if [ "$ZUSTAND" -ne 0 ]; then
  if [ -f mathkomp.sqlite3 ]; then
    sag "  Ein frueherer Aufbau ist unvollstaendig geblieben und wird wiederholt."
    rm -f mathkomp.sqlite3
  fi

  # Unter anderem Namen aufbauen und erst am Ende umbenennen. Ein Abbruch
  # laesst dann nur eine .neu-Datei liegen, die der naechste Start wegraeumt.
  NEU="mathkomp.sqlite3.neu"
  rm -f "$NEU"

  sag "  … Datenbank aus dem Fachinhalt aufbauen"
  "${MATHKOMP[@]}" --db "$NEU" build >>"$PROTOKOLL" 2>&1 || abbruch \
    "Die Datenbank liess sich nicht aufbauen." \
    "" \
    "Die Einzelheiten stehen in der Datei $PROTOKOLL in diesem Ordner." \
    "Bitte diese Datei beim Melden mitschicken."

  sag "  … die sieben Beispielprofile durchspielen, damit etwas zu sehen ist"
  "${MATHKOMP[@]}" --db "$NEU" simulate >>"$PROTOKOLL" 2>&1 || abbruch \
    "Die Beispielprofile liessen sich nicht durchspielen." \
    "" \
    "Die Einzelheiten stehen in der Datei $PROTOKOLL in diesem Ordner."

  mv "$NEU" mathkomp.sqlite3 || abbruch \
    "Die fertige Datenbank liess sich nicht an ihren Platz legen."
  sag ""
fi

# ---------------------------------------------------------------- Browser

# Erst oeffnen, wenn der Server wirklich antwortet — sonst zeigt der Browser
# eine Fehlerseite, und der naechste Handgriff waere neu laden zu muessen.
(
  i=0
  while [ "$i" -lt 60 ]; do
    if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/" 2>/dev/null; then
      open "http://127.0.0.1:$PORT/" 2>/dev/null
      exit 0
    fi
    i=$((i + 1))
    sleep 0.25
  done
) &
BROWSER_PID=$!

sag "  Die Oberflaeche oeffnet sich gleich im Browser."
sag "  Falls nicht, diese Adresse dort eingeben:  http://127.0.0.1:$PORT/"
trennlinie
sag "  Dieses Fenster ist das laufende Programm. Es muss offen bleiben —"
sag "  auch wenn der Browser sich gleich davorschiebt."
sag ""
sag "  Zum Beenden:  ctrl und C zusammen druecken."
sag "  Oder das Fenster schliessen; der Mac fragt dann einmal nach, ob die"
sag "  laufenden Programme beendet werden sollen — das mit 'Beenden'"
sag "  bestaetigen."
trennlinie

"${MATHKOMP[@]}" ui --port "$PORT"
ENDE=$?

if [ "$ENDE" -ne 0 ]; then
  abbruch \
    "Das Programm hat sich mit einem Fehler beendet (siehe oben)." \
    "" \
    "Steht dort etwas von 'Adresse' oder 'Port': ein anderes Programm" \
    "benutzt gerade $PORT. Dann hilft ein Neustart des Macs." \
    "" \
    "Sonst bitte ein Bild des ganzen Fensters an den Absender schicken."
fi

sag ""
sag "  Beendet. Die Oberflaeche im Browser holt jetzt keine neuen Zahlen mehr."
warte_auf_enter
