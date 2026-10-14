# -*- coding: utf-8 -*-
"""Startet die Kompetenzanalyse auf einem Windows-PC.

Das, was hinter dem Doppelklick auf START-WINDOWS.bat steckt.

WARUM DIE LOGIK HIER STEHT UND NICHT IN DER .bat
------------------------------------------------
Die Mac-Fassung (START-MAC.command) traegt ihre ganze Sorgfalt in bash. Die
naheliegende Windows-Fassung waere dieselbe Datei in cmd.exe uebersetzt. Das
ist gemessen der falsche Weg, aus vier Gruenden, die alle dasselbe gemeinsam
haben: cmd scheitert nicht, sondern tut lautlos etwas anderes.

  1. `call :abbruch ...` gefolgt von `exit /b 1` beendet das Skript NICHT.
     Es kehrt aus dem Unterprogramm zurueck, und die naechste Zeile laeuft.
     Woertlich uebersetzt hiesse das: "Auf diesem PC fehlt Python" erscheint,
     und danach loescht das Skript die Arbeitsumgebung.
  2. Innerhalb eines Klammerblocks macht `^&` aus dem Trenner Text, und
     %ERRORLEVEL% liefert den Wert von VOR dem Block.
  3. `set /p` fuehrt aus, was jemand eintippt, und laesst bei leerer Eingabe
     den vorigen Wert stehen - in einer Sitzung waere das das falsche Kind.
  4. Das Gegenmittel gegen (2) und (3), `setlocal EnableDelayedExpansion`,
     loescht das Ausrufezeichen aus jedem Pfad. Ein Ordner "Klasse 3a! Sommer"
     ist danach unauffindbar. Die beiden Pflichtabsicherungen einer grossen
     .bat schliessen einander also aus - es gibt keine richtige Fassung.

Deshalb ist START-WINDOWS.bat nur eine Huelle von wenigen Zeilen, die genau
eine Entscheidung trifft (ist ueberhaupt ein Python da?), und alles Weitere
steht hier.

WAS DIESE DATEI VORAUSSETZT
---------------------------
Nichts ausser der Standardbibliothek. Sie laeuft unter dem Python des
Rechners, nicht unter dem der Arbeitsumgebung - die legt sie ja erst an.
Deshalb ist sie bewusst in altem, schlichtem Python geschrieben: keine
Typannotationen, kein match, nichts, was ein zu altes Python schon beim
Einlesen mit einem SyntaxError beenden wuerde. Ein zu altes Python soll
einen deutschen Satz bekommen, keinen englischen Stapelauszug.
"""

import os
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

PORT = 8765
ADRESSE = "http://127.0.0.1:%d/" % PORT
PROTOKOLL = "einrichtung.log"
DATENBANK = "mathkomp.sqlite3"

#: Mindestversion. 3.11 wegen des Sprachstands im Projekt, SQLite 3.38 wegen
#: json_valid() in einer CHECK-Bedingung des Schemas.
MIND_PYTHON = (3, 11)
MIND_SQLITE = (3, 38)


# --------------------------------------------------------------- Sprechen

def sag(text=""):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def trennlinie():
    sag("")
    sag("-" * 60)
    sag("")


def warte_auf_enter():
    """Ohne das schliesst sich das Fenster, bevor irgendjemand liest.

    Das gilt auf Windows staerker als auf dem Mac: eine .bat nimmt ihr
    Fenster beim Ende mit, und nach strg-c fragt cmd "Batchvorgang
    abbrechen (J/N)?" und ueberspringt danach jede weitere Zeile der .bat.
    Ein `pause` dort hinten wuerde also gerade dann nicht laufen, wenn man
    es braucht. Deshalb wartet Python selbst, solange es noch lebt.
    """
    sag("")
    try:
        input("Zum Schliessen die Eingabetaste druecken. ")
    except (EOFError, KeyboardInterrupt):
        pass


def abbruch(*zeilen):
    sag("")
    for zeile in zeilen:
        sag("  " + zeile)
    warte_auf_enter()
    sys.exit(1)


# --------------------------------------------------------------- Standort

def in_den_eigenen_ordner():
    """Der Projektordner liegt eine Ebene ueber tools/.

    Die .bat wechselt zwar schon mit `cd /d "%~dp0"` dorthin, aber sie ist
    nicht der einzige Weg hierher, und ein falsches Arbeitsverzeichnis
    aeussert sich spaeter als fehlende Internetverbindung.
    """
    ordner = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        os.chdir(ordner)
    except OSError:
        abbruch("Der Ordner des Programms laesst sich nicht oeffnen.",
                "",
                "Liegt er auf einem Netzlaufwerk oder einem Stick, der nicht",
                "mehr angeschlossen ist?",
                "",
                "Gesucht wurde hier: " + ordner)
    return ordner


def standort_pruefen():
    """Wird nur die Startdatei irgendwohin gezogen, fehlt drumherum alles.

    Ohne diese Probe legt das Programm am neuen Ort eine Arbeitsumgebung an,
    scheitert spaeter und beschuldigt dafuer die Internetverbindung.
    """
    for noetig in ("pyproject.toml", "content", "ui", "src"):
        if not os.path.exists(noetig):
            abbruch(
                "Dieses Startsymbol liegt nicht mehr in seinem Ordner.",
                "",
                "Es gehoert in den entpackten Programmordner, zusammen mit",
                "allem anderen, was beim Auspacken entstanden ist. Alleine",
                "kann es nichts tun.",
                "",
                "Haeufigster Grund: die ZIP-Datei wurde nie ausgepackt, und",
                "der Doppelklick ging in das Vorschaufenster hinein. Bitte",
                "die ZIP-Datei erst auspacken, dann den entstandenen Ordner",
                "oeffnen und dort starten.",
                "",
                "An dieser Stelle fehlt: " + noetig)


# ----------------------------------------------------------------- Sperre

class Sperre(object):
    """Verhindert, dass zwei Fenster gleichzeitig einrichten.

    Zwei Doppelklicks kurz hintereinander waehrend der Einrichtung: das
    zweite Fenster wuerde .venv mitten im Aufbau loeschen, und das erste
    meldete dafuer eine fehlende Internetverbindung.

    Auf dem Mac ist die Sperre ein Verzeichnis, das ein EXIT-trap wieder
    wegraeumt. Auf Windows gibt es kein trap, und der haeufigste Weg, dieses
    Programm zu beenden, ist das Schliessen des Fensters - dabei laeuft
    weder `finally` noch `atexit`. Eine selbst angelegte und selbst zu
    loeschende Sperre wuerde also liegenbleiben und das Programm dauerhaft
    unstartbar machen; die Person muesste eine versteckte Datei loeschen,
    von der sie nichts weiss.

    Deshalb sperrt hier nicht die Existenz der Datei, sondern ein vom
    Betriebssystem gehaltenes Schloss darauf. Windows gibt es beim
    Prozessende von sich aus frei - auch nach einem harten Abbruch, auch
    nach einem Stromausfall. Die Datei darf danach liegenbleiben: sie
    sperrt nichts.
    """

    def __init__(self, pfad=".start.lock"):
        self.pfad = pfad
        self.handle = None

    def nehmen(self):
        try:
            self.handle = open(self.pfad, "a+b")
        except OSError:
            # Kein Schreibrecht im eigenen Ordner. Das ist ein eigener
            # Fehler, aber keiner, der einen zweiten Start bedeutet -
            # also nicht als belegte Sperre melden.
            return True
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, IOError):
            self.handle.close()
            self.handle = None
            return False
        return True


# ----------------------------------------------------------------- Python

def python_pruefen():
    """Der Python, unter dem diese Datei gerade laeuft."""
    if sys.version_info[:2] < MIND_PYTHON:
        abbruch(
            "Das Python auf diesem PC ist zu alt.",
            "",
            "Gebraucht wird Version %d.%d oder neuer, gefunden wurde %s."
            % (MIND_PYTHON[0], MIND_PYTHON[1],
               ".".join(str(n) for n in sys.version_info[:3])),
            "",
            "So geht es:",
            "  1. https://www.python.org/downloads/ im Browser oeffnen",
            "  2. die grosse gelbe Schaltflaeche anklicken",
            "  3. die geladene Datei doppelklicken und dem",
            "     Installationsfenster folgen",
            "  4. danach dieses Startsymbol hier erneut doppelklicken")

    import sqlite3
    if sqlite3.sqlite_version_info < MIND_SQLITE:
        abbruch(
            "Das SQLite dieses Python ist zu alt fuer dieses Programm.",
            "",
            "Gebraucht wird %d.%d, gefunden wurde %s."
            % (MIND_SQLITE[0], MIND_SQLITE[1], sqlite3.sqlite_version),
            "",
            "Abhilfe: eine aktuelle Python-Version von",
            "https://www.python.org/downloads/ installieren und erneut starten.")


# ------------------------------------------------- Arbeitsumgebung (.venv)

def venv_python(ordner="."):
    unterordner = "Scripts" if os.name == "nt" else "bin"
    name = "python.exe" if os.name == "nt" else "python"
    return os.path.join(ordner, ".venv", unterordner, name)


def umgebung_brauchbar(ordner):
    """Nicht ob sich das Programm laden laesst, sondern von WO.

    Die Arbeitsumgebung merkt sich beim Einrichten den absoluten Pfad dieses
    Ordners. Wird er spaeter verschoben, zeigt sie ins Leere - das faellt
    auf. Wird er KOPIERT, zeigt sie weiter auf das Original, und dann
    arbeitet die Kopie still mit den Dateien des Originals. Auch mit dessen
    Datenbank: cli.DEFAULT_DB leitet sich aus dem Ort des Pakets ab, nicht
    aus dem Arbeitsverzeichnis. Wer den Ordner dupliziert, um "eine
    Sicherung zu haben", und dann in der Kopie mit einem Kind arbeitet,
    schreibt dessen Daten in genau die Datei, die er sichern wollte (§86).

    Eine blosse Existenzpruefung auf .venv\\Scripts\\python.exe wuerde das
    zuverlaessig uebersehen: die Datei ist da und startet auch.
    """
    python = venv_python(ordner)
    if not os.path.isfile(python):
        return False
    programm = (
        "import pathlib, sys, mathkomp\n"
        "hier = pathlib.Path(sys.argv[1]).resolve()\n"
        "sys.exit(0 if hier in pathlib.Path(mathkomp.__file__).resolve().parents else 1)\n")
    return _still(python, "-c", programm, ordner, cwd=ordner) == 0


def umgebung_anlegen(ordner):
    if os.path.isdir(".venv"):
        sag("  Die Arbeitsumgebung gehoert nicht zu diesem Ordner.")
        sag("  (Der Ordner wurde verschoben, umbenannt oder kopiert.)")
        sag("  Sie wird neu angelegt - dafuer wird noch einmal kurz Internet")
        sag("  gebraucht.")
        import shutil
        shutil.rmtree(".venv", ignore_errors=True)
    else:
        sag("  Erster Start - die Arbeitsumgebung wird eingerichtet.")
        sag("  Das dauert meist eine halbe Minute - bei langsamer Verbindung")
        sag("  auch einige Minuten. Dafuer wird einmalig Internet gebraucht.")
    sag("  Bitte das Fenster offen lassen und nicht noch einmal doppelklicken.")
    sag("")

    sag("  ... Arbeitsumgebung anlegen")
    if _still(sys.executable, "-m", "venv", ".venv") != 0:
        abbruch(
            "Die Arbeitsumgebung liess sich nicht anlegen.",
            "",
            "Haeufigster Grund auf einem Windows-PC: der Ordner liegt an einer",
            "Stelle, an der das Programm nichts anlegen darf - etwa in einem",
            "OneDrive-Ordner, der gerade nicht verfuegbar ist, oder in",
            "'Programme'.",
            "",
            "Abhilfe: den ganzen Programmordner in den eigenen Benutzerordner",
            "ziehen (im Explorer links unter dem eigenen Namen) und erneut",
            "starten.")

    # Kein --quiet: das hier ist der einzige lange Schritt, und ein Fenster,
    # das eine halbe Minute nichts schreibt, ist genau das, was jemanden zum
    # Abbrechen bringt. --no-cache-dir, damit die Zusage "nichts ausserhalb
    # dieses Ordners" auch wirklich stimmt.
    sag("  ... Programm installieren - jetzt laufen Zeilen durch:")
    sag("")
    ergebnis = subprocess.call([
        venv_python(ordner), "-m", "pip", "install",
        "--disable-pip-version-check", "--no-cache-dir",
        "--progress-bar", "off", "--timeout", "20", "--retries", "2",
        "-e", "."])
    if ergebnis != 0:
        abbruch(
            "Die Installation ist fehlgeschlagen.",
            "",
            "Besteht gerade eine Internetverbindung? Sie wird nur fuer diesen",
            "einen Schritt gebraucht, danach laeuft alles ohne Netz.",
            "",
            "Ist das Netz in Ordnung, sperrt moeglicherweise das Schul- oder",
            "Firmennetz den Paketserver pypi.org. Dann bitte beim Absender",
            "melden und die letzten Zeilen oben mitschicken.")
    sag("")
    sag("  ... fertig.")
    sag("")


# -------------------------------------------------------------- Datenbank

#: Die neun Tabellen, in denen erhobene Daten stehen. Aus content/ kaeme
#: nichts davon zurueck. Identisch mit cli.USER_STATE_TABELLEN - hier noch
#: einmal, weil diese Datei laeuft, bevor das Paket installiert ist.
ERHEBUNGSTABELLEN = (
    "students", "task_attempts", "attempt_error_codes", "interaction_events",
    "evidence_events", "routing_decisions", "student_competency_state",
    "student_competency_facets", "student_hypotheses",
)

BRAUCHBAR, LEER, MIT_DATEN = 0, 1, 2


def datenbank_pruefen(pfad=DATENBANK):
    """Drei Antworten, und die dritte ist die, auf die es ankommt.

    Frueher stand an dieser Stelle "wenn die Datei fehlt, baue sie". Bricht
    der Aufbau ab, bleibt eine Datei mit Schema und ohne Inhalt liegen; sie
    existiert, also baute der naechste Start nicht mehr, und die Oberflaeche
    brach mit "0 Kompetenzknoten" ab. Der Zustand heilte nie von selbst.

    Die naheliegende Reparatur - "unbrauchbar, also weg damit" - ist
    schlimmer als das Problem. Eine Datenbank kann auch deshalb unlesbar
    sein, weil sie gerade von einer laufenden Sitzung benutzt wird, weil ein
    Virenscanner sie festhaelt oder weil sie auf einem OneDrive-Platzhalter
    liegt, der noch nicht geladen ist. In all diesen Faellen enthaelt sie
    erhobene Daten, und die sind unwiederbringlich (§86).

    Deshalb gilt hier die strenge Richtung: geloescht wird nur, was
    NACHWEISLICH heil UND NACHWEISLICH leer ist. Jede Unsicherheit - jede
    Ausnahme, jede nicht beantwortete Frage - faellt auf MIT_DATEN und damit
    auf "nicht anfassen".
    """
    if not os.path.isfile(pfad):
        return LEER

    import sqlite3
    try:
        conn = sqlite3.connect(pfad)
    except sqlite3.Error:
        return MIT_DATEN

    try:
        # Erst die Frage, ob die Datei ueberhaupt heil ist. Ohne sie kann
        # eine beschaedigte Datei bei jeder folgenden Frage eine Ausnahme
        # werfen, die sich von "leer" nicht unterscheiden laesst.
        try:
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                return MIT_DATEN
        except sqlite3.Error:
            return MIT_DATEN

        try:
            vorhanden = set(r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"))
        except sqlite3.Error:
            return MIT_DATEN

        # Jede Erhebungstabelle einzeln, mit eigenem try: eine einzige
        # unlesbare Tabelle darf nicht dazu fuehren, dass die Datei als leer
        # gilt. Eine Tabelle, die es nicht gibt, ist dagegen nachweislich
        # ohne Daten - das ist der normale Zustand nach einem halben Aufbau.
        for tabelle in ERHEBUNGSTABELLEN:
            if tabelle not in vorhanden:
                continue
            try:
                if conn.execute("SELECT COUNT(*) FROM %s" % tabelle).fetchone()[0]:
                    break
            except sqlite3.Error:
                return MIT_DATEN
        else:
            # Nachweislich heil, nachweislich ohne erhobene Daten. Nur
            # dieser Weg fuehrt zum Loeschen.
            return LEER

        # Es sind Daten drin. Bleibt die Frage, ob auch der Fachinhalt da
        # ist - nur dann ist die Datei brauchbar statt bloss schuetzenswert.
        try:
            if conn.execute("SELECT COUNT(*) FROM competencies").fetchone()[0]:
                return BRAUCHBAR
        except sqlite3.Error:
            pass
        return MIT_DATEN
    finally:
        conn.close()


def datenbank_aufbauen(ordner):
    zustand = datenbank_pruefen()

    if zustand == MIT_DATEN:
        abbruch(
            "Die Datenbank in diesem Ordner ist unvollstaendig, enthaelt aber",
            "schon erhobene Daten. Sie wird deshalb weder angetastet noch neu",
            "aufgebaut - dabei gingen diese Daten verloren.",
            "",
            "Meistens ist ein frueherer Aufbau mittendrin abgebrochen worden.",
            "Moeglich ist auch, dass die Datei gerade von etwas anderem",
            "festgehalten wird: einem Virenscanner, einer Sicherung, oder",
            "einem Fenster, das hart beendet wurde. Dann hilft ein Neustart",
            "des Rechners und ein zweiter Versuch.",
            "",
            "Hilft das nicht, bitte beim Absender melden. Die Datei heisst",
            DATENBANK + " und liegt in diesem Ordner. Sie bitte nicht",
            "loeschen - die erhobenen Daten lassen sich daraus retten.")

    if zustand == BRAUCHBAR:
        return

    if os.path.isfile(DATENBANK):
        sag("  Ein frueherer Aufbau ist unvollstaendig geblieben und wird")
        sag("  wiederholt.")
        try:
            os.remove(DATENBANK)
        except OSError:
            abbruch(
                "Die unvollstaendige Datenbank laesst sich nicht wegraeumen.",
                "",
                "Wird gerade in einem anderen Fenster mit einem Kind",
                "gearbeitet? Dann dort bitte erst beenden.")
        # del meldet auch dann Erfolg, wenn die Datei noch da ist. Also
        # nachsehen, statt es zu glauben.
        if os.path.isfile(DATENBANK):
            abbruch("Die unvollstaendige Datenbank liess sich nicht wegraeumen.")

    # Unter anderem Namen aufbauen und erst am Ende umbenennen. Ein Abbruch
    # laesst dann nur eine .neu-Datei liegen, die der naechste Start
    # wegraeumt - und niemals eine halbe Datenbank an ihrem richtigen Platz.
    neu = DATENBANK + ".neu"
    if os.path.isfile(neu):
        try:
            os.remove(neu)
        except OSError:
            pass

    python = venv_python(ordner)
    protokoll = open(PROTOKOLL, "a", encoding="utf-8")
    try:
        sag("  ... Datenbank aus dem Fachinhalt aufbauen")
        if _protokolliert(python, ["--db", neu, "build"], protokoll) != 0:
            abbruch(
                "Die Datenbank liess sich nicht aufbauen.",
                "",
                "Die Einzelheiten stehen in der Datei " + PROTOKOLL + " in",
                "diesem Ordner. Bitte diese Datei beim Melden mitschicken.")

        sag("  ... die sieben Beispielprofile durchspielen, damit etwas zu")
        sag("      sehen ist")
        if _protokolliert(python, ["--db", neu, "simulate"], protokoll) != 0:
            abbruch(
                "Die Beispielprofile liessen sich nicht durchspielen.",
                "",
                "Die Einzelheiten stehen in der Datei " + PROTOKOLL + ".")
    finally:
        protokoll.close()

    try:
        os.replace(neu, DATENBANK)
    except OSError:
        abbruch("Die fertige Datenbank liess sich nicht an ihren Platz legen.")
    sag("")


# ---------------------------------------------------------- Unterprozesse

def _umgebung():
    """PYTHONUTF8 ist auf Windows nicht Feinschliff, sondern Pflicht.

    build und simulate schreiben ihre Ausgabe in die Protokolldatei. Sobald
    Pythons Ausgabe umgeleitet ist, benutzt sie auf einem deutschen Windows
    nicht UTF-8, sondern cp1252 - und ein einziges Zeichen ausserhalb davon
    beendet den Aufbau mit einem UnicodeEncodeError. Das Skript wuerde dafuer
    die Internetverbindung beschuldigen.
    """
    umgebung = os.environ.copy()
    umgebung["PYTHONUTF8"] = "1"
    umgebung["PYTHONIOENCODING"] = "utf-8"
    return umgebung


def _still(programm, *argumente, **benannt):
    """Aufruf ohne Ausgabe. `cwd` ausdruecklich benannt, nie erraten.

    Eine fruehere Fassung leitete das Arbeitsverzeichnis aus der Zahl der
    Argumente ab. Damit wurde aus `-m venv .venv` ein Aufruf im Ordner
    ".venv" - einem Ordner, den es in genau diesem Moment noch nicht gibt.
    """
    try:
        return subprocess.call(
            [programm] + list(argumente),
            cwd=benannt.get("cwd"), env=_umgebung(),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return 1


def _kinder_sterben_mit_uns():
    """Ein Auftragsobjekt, das seine Prozesse beim eigenen Ende mitnimmt.

    Gemessenes Problem: wird dieses Fenster geschlossen, stirbt zwar das
    Startskript, aber der Server laeuft weiter und bedient Port 8765 munter
    weiter. Der naechste Doppelklick fragt dann "laeuft es schon?", bekommt
    ein Ja und meldet "Das Programm laeuft bereits in einem anderen Fenster"
    - ein Fenster, das es nicht gibt. Das ist eine Sackgasse, aus der eine
    nicht technikaffine Person nicht herausfindet: der Ausweg waere der
    Task-Manager.

    Aufraeumen im Skript hilft dagegen nicht. Beim Schliessen des Fensters
    laeuft weder `finally` noch `atexit`, und genau das ist der haeufigste
    Weg, dieses Programm zu beenden.

    Windows hat dafuer ein eigenes Mittel: ein Job-Objekt mit der
    Eigenschaft KILL_ON_JOB_CLOSE. Sobald die letzte Kennung darauf
    verschwindet - und das tut sie, wenn dieser Prozess endet, egal auf
    welche Weise -, beendet das Betriebssystem alles, was darin steckt.
    Kein Aufraeumcode, der laufen muesste.

    Gibt None zurueck, wenn das nicht geht; dann bleibt es beim alten
    Verhalten, statt dass der Start daran scheitert.
    """
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class GRENZEN(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class ZAEHLER(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in (
                "ReadOperationCount", "WriteOperationCount",
                "OtherOperationCount", "ReadTransferCount",
                "WriteTransferCount", "OtherTransferCount")]

        class ERWEITERT(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", GRENZEN),
                ("IoInfo", ZAEHLER),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        auftrag = kernel.CreateJobObjectW(None, None)
        if not auftrag:
            return None

        angaben = ERWEITERT()
        angaben.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(
                auftrag, 9,  # JobObjectExtendedLimitInformation
                ctypes.byref(angaben), ctypes.sizeof(angaben)):
            kernel.CloseHandle(auftrag)
            return None
        return auftrag
    except Exception:
        return None


def _server_starten(befehl):
    """Startet den Server und wartet auf ihn - aber unter dem Auftragsobjekt.

    Popen statt call, weil erst die Prozesskennung gebraucht wird, um das
    Kind dem Auftragsobjekt zuzuordnen. Zugeordnet wird, bevor irgendetwas
    anderes passiert; bis dahin kann ein Fensterschliessen noch eine Luecke
    lassen, aber sie ist Millisekunden breit statt stundenlang.

    Das Kind selbst startet auf diesem Rechner noch ein weiteres - der
    Python der Arbeitsumgebung reicht an den darunterliegenden Interpreter
    weiter. Das Auftragsobjekt erfasst beide, weil es den ganzen Baum
    aufnimmt und nicht nur den einen Prozess.
    """
    auftrag = _kinder_sterben_mit_uns()
    prozess = subprocess.Popen(befehl, env=_umgebung())
    if auftrag:
        try:
            import ctypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.AssignProcessToJobObject(auftrag, int(prozess._handle))
        except Exception:
            pass
    return prozess.wait()


def _protokolliert(python, argumente, protokoll):
    protokoll.flush()
    try:
        return subprocess.call(
            [python, "-m", "mathkomp"] + argumente, env=_umgebung(),
            stdout=protokoll, stderr=subprocess.STDOUT)
    except OSError:
        return 1


# ------------------------------------------------------------ Laeuft schon?

def antwortet_schon():
    """Nicht "antwortet irgendwer auf 8765", sondern ob es dieses Programm ist.

    Diese Frage ist auf Windows wichtiger als auf dem Mac: Windows laesst
    zwei Server gleichzeitig auf dieselbe Adresse binden, ohne zu klagen.
    Der zweite Start scheitert also nicht von selbst - er wuerde stumm einen
    zweiten Server danebenstellen, und welchen der Browser dann zeigt, ist
    Zufall. Diese Probe ist die einzige Stelle, an der das auffaellt.

    Gefragt wird deshalb /api/catalog - das hat sonst niemand.

    Das kurze Zeitlimit ist gemessen noetig: ein laufender eigener Server
    antwortet in unter 50 ms, waehrend ein geschlossener Port auf Windows
    rund zwei Sekunden braucht, um "da ist nichts" zu sagen. Ohne Zeitlimit
    begaenne jeder normale Start mit zwei Sekunden schwarzem Fenster.
    """
    try:
        antwort = urlopen(ADRESSE + "api/catalog", timeout=0.3)
    except Exception:
        # Jede Ausnahme heisst "laeuft nicht". Bei kurzem Zeitlimit kommt
        # nicht ConnectionRefusedError zurueck, sondern TimeoutError - eine
        # Aufzaehlung einzelner Fehlerarten waere hier falsch.
        return False
    try:
        return antwort.getcode() == 200
    finally:
        antwort.close()


def browser_oeffnen_wenn_bereit():
    """Erst oeffnen, wenn der Server wirklich antwortet.

    Sonst zeigt der Browser eine Fehlerseite, und der naechste Handgriff
    waere neu laden zu muessen - fuer jemanden, der gerade zum ersten Mal
    startet, ist das der Moment, in dem er aufgibt.
    """
    import webbrowser
    for _ in range(40):
        if antwortet_schon():
            webbrowser.open(ADRESSE)
            return
        time.sleep(0.25)


# -------------------------------------------------------------------- Lauf

def main():
    ordner = in_den_eigenen_ordner()
    standort_pruefen()

    sag("")
    sag("  Kompetenzanalyse - Zahl und Operation")
    sag("  " + ordner)
    trennlinie()

    # Der zweite Doppelklick ist der haeufigste Handgriff ueberhaupt: es
    # dauert jemandem zu lange, oder das Fenster ist hinter dem Browser
    # verschwunden. Die Kopfzeilen stehen bewusst davor - sonst begaenne
    # jeder Start mit einem leeren Fenster.
    if antwortet_schon():
        import webbrowser
        sag("  Das Programm laeuft bereits in einem anderen Fenster.")
        sag("  Die Oberflaeche wird dort erneut geoeffnet.")
        webbrowser.open(ADRESSE)
        trennlinie()
        sag("  Dieses Fenster hier wird nicht gebraucht und kann geschlossen")
        sag("  werden.")
        warte_auf_enter()
        return 0

    sperre = Sperre()
    if not sperre.nehmen():
        abbruch(
            "Das Programm wird gerade in einem anderen Fenster gestartet.",
            "",
            "Bitte dort warten, bis die Oberflaeche im Browser erscheint.",
            "Dieses Fenster hier kann geschlossen werden.")

    python_pruefen()

    if not umgebung_brauchbar(ordner):
        umgebung_anlegen(ordner)

    datenbank_aufbauen(ordner)

    threading.Thread(target=browser_oeffnen_wenn_bereit, daemon=True).start()

    sag("  Die Oberflaeche oeffnet sich gleich im Browser.")
    sag("  Falls nicht, diese Adresse dort eingeben:  " + ADRESSE)
    trennlinie()
    sag("  Dieses Fenster ist das laufende Programm. Es muss offen bleiben -")
    sag("  auch wenn der Browser sich gleich davorschiebt.")
    sag("")
    sag("  Zum Beenden:  strg und C zusammen druecken.")
    sag("  Oder das Fenster schliessen.")
    trennlinie()

    try:
        ende = _server_starten(
            [venv_python(ordner), "-m", "mathkomp",
             "--db", DATENBANK, "ui", "--port", str(PORT)])
    except KeyboardInterrupt:
        ende = 0

    if ende != 0:
        abbruch(
            "Das Programm hat sich mit einer Meldung beendet (siehe oben).",
            "",
            "Bitte ein Bild des ganzen Fensters an den Absender schicken.")

    sag("")
    sag("  Beendet. Die Oberflaeche im Browser holt jetzt keine neuen Zahlen")
    sag("  mehr.")
    warte_auf_enter()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Ohne das steht hier ein englischer Stapelauszug, und das Fenster
        # ist weg, bevor jemand ihn lesen kann.
        sag("")
        sag("  Abgebrochen.")
        warte_auf_enter()
        sys.exit(1)
