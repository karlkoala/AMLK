# MVP V1.0 — Adaptives Mathematik-Lern- und Kompetenzsystem

Vollständige Umsetzung der Spezifikation *MVP V1.0, Version 1.0* — Sprint 1 bis 12 nach
§104. Alle Abschnittsverweise (§NN) im Code, im Content und in dieser Datei beziehen sich
auf diese Spezifikation.

> **§124, der wichtigste Satz für die Entwicklung**
> Baue kein Quizsystem, das richtige und falsche Antworten zählt. Baue einen
> Kompetenzgraphen, der mit möglichst wenigen gezielt ausgewählten Aufgaben herausfindet,
> was eine Schüler:in sicher kann, wo eine Schwierigkeit beginnt, unter welchen
> Bedingungen sie auftritt, welche mathematische Voraussetzung dafür relevant sein könnte
> und welcher nächste Datenpunkt den größten zusätzlichen Informationswert besitzt.

## Schnellstart

**0. Einmalig einrichten.** Eine virtuelle Umgebung anlegen und das Projekt
hineininstallieren. Danach steht der Befehl `mathkomp` zur Verfügung — auf jedem
System gleich geschrieben, ohne `PYTHONPATH` und ohne die Frage, ob der
Interpreter `python`, `python3` oder `py` heißt.

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

Unter Windows in PowerShell:

```powershell
py -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e ".[dev]"
```

Der Selbsttest der Voraussetzungen — Python ≥ 3.11 und ein SQLite, das
`json_valid()` kennt (beides wird gebraucht, siehe unten):

```bash
python -c "import sys,sqlite3;print(sys.version.split()[0], sqlite3.sqlite_version, sqlite3.connect(':memory:').execute(\"select json_valid('[]')\").fetchone()[0])"
```

**1. Datenbank aus dem Content aufbauen.**

```bash
mathkomp build
```

`build` legt die Datei `mathkomp.sqlite3` an. Existiert sie schon, ist `--force`
nötig — und enthält sie bereits erhobene Schüler:innendaten, verweigert `build`
den Neuaufbau und nennt, was verloren ginge. Content kommt aus `content/`
zurück, eine Sitzung mit einem Kind nicht.

**2. Prüfen, dass alles stimmt.** 19 Prüfregeln gegen die Spezifikation:

```bash
mathkomp validate
```

**3. Mit einem Kind arbeiten.** Das ist der eigentliche Betrieb — die
Schüler:innenansicht aus §105. Die ID ist frei wählbar und pseudonym (§86: **kein
Klarname**):

```bash
mathkomp session KIND-01 --grade 3
```

Das System zeigt eine Aufgabe, nimmt die Antwort entgegen, wählt die nächste. `:hilfe`
zeigt die Befehle, `:ende` beendet. Über `:warum` wird sichtbar, weshalb gerade diese
Aufgabe kommt (§89); `:weiter` übergeht den Vorschlag, weil nach §3 die Lehrkraft
übersteuern darf.

**4. Ergebnis ansehen.** Die Lehrkraftansicht nach §106:

```bash
mathkomp student KIND-01
```

**5. Die Analyseoberfläche öffnen.** Dieselben Daten im Browser, nach dem
Implementierungsauftrag für die UI — acht Bereiche von der Übersicht über die
Kompetenzkarte bis zum Entscheidungsprotokoll:

```bash
mathkomp ui
```

Dann `http://127.0.0.1:8765/` aufrufen. Der Server bindet **nur lokal** und öffnet die
Datenbank **schreibgeschützt**: eine Betrachtung darf keine Diagnostik verändern (§89).
Die Oberfläche rechnet nichts aus — sie zeigt ausschließlich, was `api.py` liefert.
`--port` und `--host` ändern die Voreinstellung.

Die sechs simulierten Testfälle laufen jeweils bis zur Entscheidung „nicht weiter testen"
(§73) durch. Wer den anderen Fall sehen will — eine noch offene, vom System vorgeschlagene
Aufgabe —, bricht eine Sitzung nach wenigen Aufgaben ab: `session DEMO-01 --grade 3
--max-tasks 4`. Die Übersicht zeigt den Vorschlag dann als ausstehend an.

Ohne Kind ausprobieren geht auch — `simulate` spielt die sechs Testfälle aus §98–§103 mit
vorgegebenem Antwortverhalten durch:

```bash
mathkomp simulate
```

Die Tests (`pytest` kommt aus dem `[dev]`-Extra in Schritt 0):

```bash
pytest tests -q
```

Weitere Kommandos und Schalter: `report` (Content-Übersicht), `routes <task_id>` (Routen
einer Aufgabe), `student <id> --profile` (Zielbild nach §118), `student <id> --trail`
(Entscheidungsprotokoll nach §89), `simulate --case C` (einzelner Testfall),
`session <id> --focus ZO06_PLACE_VALUE` (Teilgraph einschränken, §3/§74),
`session <id> --diagnose` (Fehlercodes, Status und Hypothesen mitschreiben — das gehört
nach §106 in die Lehrkraftansicht und ist deshalb **nicht** voreingestellt).

## Voraussetzungen

**Keine Laufzeitabhängigkeiten** — nur Standardbibliothek. Gebraucht werden aber:

| | | |
|---|---|---|
| Python | ≥ 3.11 | `pyproject.toml` setzt diese Untergrenze; `pip` bricht darunter ab |
| SQLite | ≥ 3.38 | `schema.sql` nutzt 29 `GENERATED … VIRTUAL`-Spalten (ab 3.31) und 13 `CHECK (json_valid(…))` — Funktionsnamen in `CHECK` löst SQLite schon beim `CREATE TABLE` auf, ohne JSON1 stirbt der Build |
| pytest | ≥ 8 | nur für die Tests, im `[dev]`-Extra |

**macOS.** `python3` aus den Xcode Command Line Tools ist 3.9.6 und damit zu alt.
Erst ein eigenes Python installieren, etwa `brew install python@3.12`, dann
Schritt 0. Ohne aktivierte virtuelle Umgebung lehnt Homebrew-`pip` die
Installation nach PEP 668 mit `externally-managed-environment` ab — das ist
kein Fehler des Projekts, sondern der fehlende Schritt 0.

**Windows.** `PYTHONUTF8=1` setzen, sonst zerlegt die Konsole das §-Zeichen.
Öffnet `python` den Microsoft Store, ist es der Store-Platzhalter; dann `py`
verwenden. Beides erledigt sich innerhalb der aktivierten virtuellen Umgebung.

**Ohne Installation** geht es auch — dann muss `PYTHONPATH=src` gesetzt sein und
statt `mathkomp …` heißt es `python3 -m mathkomp …` (macOS, Linux) oder
`py -m mathkomp …` (Windows). Nur `pip install -e .` wird unterstützt, nicht
`pip install .`: `content/`, `ui/` und der Standardpfad der Datenbank liegen
neben dem Paket, nicht darin, und wären nach einem Kopier-Install nicht mehr
auffindbar.

## Übergabe an eine andere Person

Weitergegeben wird der **Quellbaum ohne erzeugte Dateien**. Das Projekt ist kein
Git-Repository, die `.gitignore` filtert beim Kopieren also nichts — vor dem
Packen von Hand aufräumen:

```bash
find . -name __pycache__ -type d -prune -exec rm -rf {} + && rm -rf .pytest_cache *.egg-info .venv
```

**`mathkomp.sqlite3` gehört nicht dazu.** Sie enthält erhobene Daten (§86) und
lässt sich aus `content/` vollständig neu erzeugen — zwei frische Builds ergeben
dieselbe Datei. Wird sie dennoch mitgegeben, findet `simulate` die acht Profile
bereits vor, spielt je Fall nur einen Schritt und meldet *„§123 Kriterium 20 —
unterschiedliche Pfade: NICHT erfüllt"*: eine falsche Abnahmeaussage aus
richtigen Daten. Wer die erhobenen Daten trotzdem zeigen will, gibt die Datei
unter anderem Namen mit und liest sie nur: `mathkomp --db referenz.sqlite3 ui`.

Die empfangende Person führt dann Schritt 0 bis 5 des Schnellstarts aus. Auf
einem frischen macOS zusätzlich davor: ein eigenes Python installieren, siehe
Voraussetzungen.

Was dabei entsteht: `build` importiert den Content, `simulate` erzeugt aus den
sechs Testfällen §98–§103 die sieben Profile `SIM-A` bis `SIM-F` (Fall E zerfällt
in `SIM-E1` und `SIM-E2`). Das achte Profil des Entwicklungsstands,
`DEMO-LAUFEND`, ist ein bewusst abgebrochener Durchlauf und
entsteht mit `mathkomp session DEMO-LAUFEND --grade 3 --max-tasks 4` — die
Übersicht zeigt danach den offenen Aufgabenvorschlag statt „nicht weiter testen".

## Stand

| | |
|---|---|
| Tabellen | 20 (§78 verlangt 13 als Minimum) |
| Kompetenzknoten | 54, davon 50 im MVP-Umfang, alle beschrieben |
| Relationen | 85, davon 49 von 50 Knoten verbunden |
| Aufgaben | 97 (81 aus §42–57, 16 ergänzt) |
| Merkmalszuordnungen | 478 |
| Aufgabenfamilien | 21 |
| Routen | 33, davon 8 mit Kontextbedingung |
| Konfigurationsschlüssel | 46, davon 0 `UNDEFINED` |
| Vokabulare / Terme | 34 / 259 |
| Prüfregeln | 19 → **0 Fehler**, 3 Hinweise |
| Tests | 169 (1 nur auf Unix-Dateisystemen) |
| Module | 23 |

Die drei verbleibenden Hinweise betreffen bewusst offene fachliche Fragen, siehe
[OFFENE_FRAGEN.md](OFFENE_FRAGEN.md).

## Was das System tut

Ein Durchlauf nach §119 und §120:

```
next_task()                                        submit(answer)
  Wiedervorlage geparkter Knoten (§40)               1. Rohdaten + Beobachtung (§60/§61/§66)
  aktiven Teilgraphen laden (§37/§74)                2. Evidenz erzeugen (§28/§65)
  offene Hypothesen holen (§64)                      3. Zustand + Facetten (§63/§117)
  Routen des letzten Versuchs (§83)                  4. Hypothesen prüfen (§64/§115)
  Kandidaten filtern (§73/§36/§38)                   5. Parken / Reaktivieren (§38/§39)
  TASK_SCORE (§68)                                   6. next_task()
  Entscheidung protokollieren (§89)
```

Elf Score-Summanden entscheiden die Auswahl, alle gewichtet aus `system_config`, alle im
Protokoll einzeln sichtbar. §68 nennt sechs davon; die fünf weiteren machen die
Priorisierung aus §67 im Score sichtbar, statt sie im Code zu verstecken (siehe
ENTSCHEIDUNGEN.md D-06).

## Die sechs Testfälle (§98–§103)

`mathkomp simulate` spielt sie durch. Das ist Kriterium 20 der Definition of
Done: dasselbe System muss bei unterschiedlichem Antwortverhalten unterschiedliche,
fachlich begründete Wege wählen.

| | Verhalten | Beobachteter Pfad | Ergebnis |
|---|---|---|---|
| **A** §98 | löst alles | D3 → D5 → Transfer | `SECURE` → `PARKED` in 3 Aufgaben, keine D1/D2 |
| **B** §99 | nur D1 gelingt | D2 ✗ → Parallel ✗ → ikonisch ✗ → **Bündelung ✓** | `SUPPORT_FOCUS`, Voraussetzung eigenständig belegt |
| **C** §100 | symbolisch nicht, ikonisch ja | D2 SYM ✗✗ → Frageform ✗✗ → D2 IMG ✓✓ | `REPRESENTATION_HYPOTHESIS` |
| **D** §101 | nur mit `COMPENSATION` | Contrast Family vollständig | `UNCERTAIN`, `STRATEGY_DEPENDENCY_HYPOTHESIS` |
| **E** §102 | zwei Kinder, gleiche erste Antwort | A: → ikonisch ✓ / B: → Grundvorstellung ✗ | verschiedene Pfade, verschiedener Status |
| **F** §103 | erst sicher, später Fehler | `PARKED` → 100 Tage → `REACTIVATED` | Wiederholungsprüfung |

Testfall E ist der schärfste: beide Kinder geben auf `6 · 8` dieselbe falsche Antwort mit
demselben Fehlercode. Kind A löst danach die ikonische Variante und erhält eine
Darstellungshypothese; Kind B scheitert auch ikonisch, wird über
`reason = CHECK_PREREQUISITE` zur Grundvorstellung geführt, erzeugt dort
`ERR_OPERATION_CONCEPT` und landet auf `SUPPORT_FOCUS`. §102 verlangt genau das: „Gleiche
Ausgangsantwort darf zu unterschiedlichen Lernpfaden führen."

## Aufbau

```
content/            Fachlicher Inhalt als JSON — die Datenbank ist daraus reproduzierbar
  vocabularies.json      34 kontrollierte Vokabulare (§108: keine Enums im Code)
  sources.json           Quellen nach §109/§110
  competencies.json      Kompetenzknoten aus §7, §9, §10
  relations.json         Kompetenzgraph nach §12/§13
  task_families.json     Aufgabenfamilien nach §25/§58
  tasks.json             Aufgabenbank aus §42–57 plus ergänzte Items
  task_routes.json       Routing als Daten (§83/§84)
  error_codes.json       Fehlercodes aus §59
  config.json            Schwellen und Gewichte aus §35, §41, §68, §95, §96
  _fragments/            Nachweis: die autorisierten Inhalte samt Begründung

src/mathkomp/
  schema.sql        20 Tabellen, drei Ebenen nach §85
  db.py             Verbindung, Schema-Initialisierung
  importer.py       Validierender Import
  validate.py       19 Prüfregeln
  clock.py          injizierbare Zeitquelle (§40, deterministische Simulation)
  ids.py            sprechende Schlüssel (§88/§89: lesbares Protokoll)
  config.py         system_config, `require()` bricht bei UNDEFINED ab (§1)
  scoring.py        Sprint 4: Auswertung und Fehlerklassifikation (§59)
  renderer.py       Sprint 4: Darstellungsvorschrift, verweigert §113-Verstöße
  attempts.py       Sprint 5: Rohdaten und Beobachtungen (§60/§61)
  evidence.py       Sprint 6: Evidenz (§28/§65), Asymmetrie nach §29/§121
  state.py          Sprint 8: Zustand und Facetten (§63/§117/§118)
  hypotheses.py     Sprint 6/10: Hypothesen (§64), Widerlegbarkeit nach §115
  parking.py        Sprint 9: Parken und Reaktivieren (§38/§39)
  routing.py        Sprint 7/10/11: Rule Engine und TASK_SCORE (§67/§68/§119)
  session.py        Ablauf nach §119/§120
  interactive.py    Schueler:innenansicht (§105), Klickfolge nach §42
  teacher.py        Lehrkraftansicht (§106), Protokoll (§89), Zielbild (§118)
  simulation.py     Sprint 12: die sechs Testfälle
  api.py            Datenvertrag zur Oberfläche: die 15 Objektarten des UI-Auftrags
  server.py         lokaler HTTP-Server, Datenbank schreibgeschützt
  cli.py            build / validate / report / routes / session / simulate / student / ui

ui/                 Analyseoberfläche — reine Darstellung, ohne Fachlogik
  index.html        Gerüst, Begriffsleiste zu den sechs Ebenen der Grundregel
  app.css           Farbpalette hell und dunkel; Farbe ist nie die einzige Codierung
  data.js           Datenzugriffsschicht — die einzige Stelle mit `fetch()`
  labels.js         Zeichen zu Zuständen; die Begriffe selbst kommen aus dem Vokabular
  dom.js            Elementbau, durchgängig über `textContent`
  app.js            Wegführung über acht Ansichten
  views/            übersicht, karte, fehleranalyse, darstellung, hypothesen,
                    evidenz, verlauf, debug

tests/              169 Tests, darunter test_portabilitaet.py (Windows/macOS)
tools/              Einmalige Werkzeuge (Fragment-Merge, Korrekturen aus der Prüfrunde)
ENTSCHEIDUNGEN.md   Was die Spezifikation offenlässt und wie entschieden wurde
OFFENE_FRAGEN.md    7 offene, 24 entschiedene fachliche Punkte
SPEC_VOLLTEXT.txt   Extrahierter Volltext der Spezifikation, zum Nachschlagen
.editorconfig       Erzwingt UTF-8 — siehe Schreibkonvention
```

## Die drei Ebenen (§85)

**CONTENT** — `sources`, `competencies`
**LOGIC** — `relations`, `task_families`, `tasks`, `task_features`, `task_routes`,
`error_codes`, `system_config`
**USER STATE** — `students`, `task_attempts`, `interaction_events`, `attempt_error_codes`,
`evidence_events`, `student_competency_state`, `student_competency_facets`,
`student_hypotheses`, `routing_decisions`

## Entscheidungen, die das System erzwingt

**§66 — Beobachtung, Evidenz und Hypothese sind drei Tabellen.**
Die Kette aus §66 (`answer = 58` → `ERR_ZERO_PLACEHOLDER` → `DIRECT_NEGATIVE ZO06` →
`ZERO_PLACEHOLDER_HYPOTHESIS`) läuft über `task_attempts` → `attempt_error_codes` →
`evidence_events` → `student_hypotheses`, in dieser Reihenfolge und in getrennten
Tabellen. `scoring.py` erzeugt nur Beobachtungen, `evidence.py` nur Evidenz,
`hypotheses.py` nur Hypothesen.

**§29 und §121 — die Asymmetrie.**
Eine richtige Antwort erzeugt indirekt positive Evidenz auf den Voraussetzungen. Eine
falsche erzeugt **keine** indirekt negative — das wäre der Schluss „Aufgabe falsch, also
Voraussetzung fehlt". Stattdessen löst der Fehler nach §30 ein Parallelitem aus und erst
nach Replikation nach §31 eine Voraussetzungsprüfung. Ein Test sichert das ab.

**§117 — kein Prozentwert.**
Der Status wird nach Schwierigkeitsstufen getrennt berechnet, nie aggregiert. Eine
reproduzierbare Grenze auf einer Stufe ist `SUPPORT_FOCUS`, Streuung innerhalb einer Stufe
ist `UNCERTAIN` — ein flacher Zähler hätte beides zu „unsicher" verschmolzen. Dazu
`student_competency_facets`: je Kompetenz und Merkmalswert ein Status, über acht
Facettenklassen. Die Lehrkraftansicht enthält kein `%`-Zeichen, ein Test prüft das.

**§115 — Widerlegbarkeit technisch erzwungen.**
Existiert kein Item, das eine Hypothese widerlegen könnte, wird sie nicht eröffnet und das
als `BLOCKED_NOT_FALSIFIABLE` gemeldet. Über diesen Weg wurde F-22 in der Simulation
sichtbar.

**§116 und §32 — Vergleiche halten alles außer einer Variable konstant.**
Eine Abhängigkeitshypothese entsteht nur, wenn die verglichenen Beobachtungen dieselbe
Schwierigkeitsstufe **und** dasselbe Antwortformat haben. Konstant zu halten sind Schwierigkeitsstufe,
Antwortformat und Frageform (`question_form`, 27 Terme, für alle 97 Items belegt). Eine
Prüfregel erzwingt dasselbe für Routen mit `reason = CHANGE_REPRESENTATION` — beim
Einschalten hat sie sofort drei konfundierte Routen gefunden.

**§108 — keine Wertelisten im Code.**
Statt `CHECK (status IN (…))` verweist jede Enum-Spalte per Fremdschlüssel auf
`vocabulary_terms`, umgesetzt über eine generierte Spalte:

```sql
status    TEXT NOT NULL,
_v_status TEXT GENERATED ALWAYS AS ('COMPETENCY_STATUS') VIRTUAL,
FOREIGN KEY (_v_status, status) REFERENCES vocabulary_terms(vocabulary, term)
```

Eine neue Merkmalsklasse ist damit eine Zeile in `vocabularies.json` — keine Migration.
Ein Test scannt das Schema nach hardcodierten Listen; erlaubt sind nur die technischen
Booleans `0`/`1`.

**§84 — Routing als Daten.**
Alle Übergänge in `task_routes`, alle Gewichte in `system_config`. Ein Test durchsucht
`routing.py` nach Aufgaben-IDs in Bedingungen — genau das Anti-Muster aus §84.

**§75 und §62 — zwei Sperren.**
`routing.llm_in_decision_path` und `evidence.time_seconds_used_for_inference` müssen
`false` sein. Ein Test prüft zusätzlich per Syntaxbaum, dass keines der Engine-Module ein
Netzwerk- oder LLM-Modul importiert.

**§59, §86, §87 — strukturell abgesichert.**
`error_codes.is_observation_only` trägt `CHECK (= 1)`, ein Fehlercode kann also nicht zur
Diagnose umgewidmet werden. `students` hat drei Spalten: pseudonyme UUID, Erstellungszeit,
optionale Klassenstufenreferenz — keine für Namen, Geburtsdatum oder Diagnosen. Es gibt
keinen Konfigurationsschlüssel, mit dem eine ADHS-Erkennung einschaltbar wäre.

## Abweichungen vom Wortlaut der Spezifikation

Fünf Stellen, jeweils mit Begründung. Vollständig in
[ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md).

**`task_features` normalisiert statt als Arrays** (§82). `feature_kind` ist selbst ein
Vokabularname, damit ist eine neue Merkmalsklasse ohne Schemaänderung möglich (§108). Die
View `v_task_features_arrays` liefert die Arrays in der Lesart von §82 zurück.

**Mehrwertige `tasks`-Felder als JSON** (§81). Die Feldnamen bleiben 1:1 lesbar; der
Importer validiert gegen `competencies` und die Vokabulare.

**`task_routes` mit `requires_status` und `requires_hypothesis`** (§83). Die Förderrouten
aus §92/§93 dürfen nur bei aktivem `SUPPORT_FOCUS` greifen; ohne diese Spalten hätte die
Bedingung im Code stehen müssen, was §84 verbietet. In der ersten Simulation von Testfall A
war der Fehler sofort sichtbar — Route R013 führte ein Kind mit hoher Kompetenz in die
Förderkette.

**`student_competency_facets` als eigene Tabelle** (§117/§118). §78 nennt sie nicht, aber
ohne sie ist die Aufschlüsselung aus §117 nicht speicherbar.

**Sieben Tabellen mehr als §78** („Mindestens"): `vocabularies`, `vocabulary_terms`
(§108), `students` (§86), `attempt_error_codes` (§66), `student_competency_facets` (§117),
`routing_decisions` (§89), `system_config` (§41).

## Schreibkonvention

Bezeichner sind ASCII und englisch: `competency_id`, `ZO02_NUMBER_UNDERSTANDING`,
`PROBLEMLOESEN`, `NEAR_ROUND_NUMBER`. Deutscher Text steht mit Umlauten und ß: `label_de`
„Problemlösen", `task_prompt` „Zähle die Punkte." Damit bleiben IDs in Dateinamen, URLs und
SQL unproblematisch, während alles, was Kind oder Lehrkraft liest, korrekt geschrieben ist.

Umlaute in Kommentaren sind überwiegend transliteriert (`ue`, `ae`, `oe`), das
Paragraphenzeichen § dagegen nicht — 117-mal in `schema.sql`, in 21 der 23 Module.
Alle Quelldateien sind **UTF-8 ohne BOM und in NFC**; der Editor muss auf UTF-8
stehen, eine `.editorconfig` im Wurzelverzeichnis setzt das durch. Das ist keine
Stilfrage: `scoring.py` bildet in `_OP_ALIASES` die Operatorzeichen `·`, `×`,
`÷`, `−` und `–` auf ASCII ab. Schreibt ein als Latin-1 eingestellter Editor
diese Datei zurück, erkennt `normalize_expression()` die Schreibweisen nicht
mehr — und eine richtige Antwort wird still als falsch gewertet. Ebenso betroffen
wären die lehrkraftsichtbaren Texte in `teacher.py`, `api.py` und unter `ui/`.

## Notation der Item-IDs

Muster `{Kompetenz}-[{Qualifizierer}-]{Schwierigkeit}-{Darstellung}-{Variante}`, wörtlich
aus §42–57 übernommen:

| Kürzel | Bedeutung |
|---|---|
| `I` / `S` / `L` | `IMAGE` / `MATHEMATICAL_SYMBOL` / `NATURAL_LANGUAGE` |
| `ACTION` / `MIXED` | `ACTION` / `MIXED` |
| `GV` / `REL` / `STRATEGY` / `CONTRAST` / `SUP` | Grundvorstellung / Aufgabenbeziehungen / Strategieitem / Contrast Item / Förderitem |

Eine Ausnahme: die drei `ZP05`-Items in §46 tragen kein Darstellungskürzel (F-15, D-16).

## Definition of Done (§123)

Alle 20 Kriterien erfüllt, jedes gegen eine prüfbare Tatsache in der Datenbank getestet
(`tests/test_testfaelle.py::test_definition_of_done`):

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Kompetenzknoten importierbar | 54 Knoten |
| 2 | Relationen datenbankbasiert | 85 Kanten, keine ohne Typ |
| 3 | Aufgaben besitzen Metadaten | 478 Merkmalszuordnungen |
| 4 | Aufgabenfamilien funktionieren | 21 Familien |
| 5 | Parallelitems verfügbar | `parallel_item_id` gesetzt |
| 6 | Fehler als Beobachtungen | `attempt_error_codes` gefüllt |
| 7 | Fehler erzeugen keine Diagnose | Versuche mit Fehlercode ohne Hypothese existieren |
| 8 | Schwierigkeit navigiert | ≥ 3 Stufen in den Testfällen |
| 9 | Skip-Level | Testfall A: D3 → D5, kein D4 |
| 10 | Darstellungswechsel | Routen mit `CHANGE_REPRESENTATION` haben gefeuert |
| 11 | Zahlenstruktur berücksichtigt | `NUMERIC_FEATURE`-Facetten vorhanden |
| 12 | Strategy Variation | `STRATEGY_DEPENDENCY_HYPOTHESIS` eröffnet |
| 13 | Contrast Items ausgelöst | Entscheidungen auf `task_purpose = CONTRAST` |
| 14 | Voraussetzungen rückwärts | Routen mit `CHECK_PREREQUISITE` haben gefeuert |
| 15 | Kompetenzen geparkt | `parked_at` gesetzt |
| 16 | Kompetenzen reaktiviert | `reactivation_reason` gesetzt |
| 17 | Individueller Teilgraph | unterschiedlich große Zustände je Kind, alle kleiner als der Graph |
| 18 | Routing ohne LLM | Konfigurationssperre plus Syntaxbaumtest |
| 19 | Entscheidungen protokolliert | `routing_decisions` gefüllt |
| 20 | Sechs unterschiedliche Pfade | paarweise verschiedene Aufgabenfolgen |

## Nicht gebaut (§107)

Ausdrücklich nicht Bestandteil von V1 und daher auch nicht vorbereitet: ADHS- oder
psychologische Diagnostik, Elternportal, Elternfragebögen, Berufsempfehlungen,
Gruppenmatching, Lernkalender, vollständige Mathematik aller Klassen, alle fünf Leitideen
inhaltlich, automatisches Persönlichkeitsprofil, LLM als zentrale Entscheidungsinstanz.

## Nächste Schritte (§127)

Das System ist funktionsfähig, aber nichts darin ist empirisch kalibriert (§6: alle Items
`UNCALIBRATED_MVP_ITEM`, §35: die D-Stufen sind eine Heuristik). §127 gibt die Reihenfolge
vor: Pilotierung, Itemanalyse, Fehlermusteranalyse, Überprüfung der D-Stufen, der
Kompetenzrelationen, der Contrast-Items, der Routing-Heuristiken und der
Park-/Reaktivierungsregeln, dann psychometrische Kalibrierung und gegebenenfalls IRT/CAT.

Am dringendsten empirisch zu prüfen sind die Entscheidungen mit dem größten Hebel:
`mastery.consistency_threshold`, die Score-Gewichte aus D-06 und die
`NEAR_ROUND_NUMBER`-Regel aus D-19. Alle drei stehen in `system_config` oder in einer
einzigen Funktion und sind ohne Codeänderung austauschbar.
