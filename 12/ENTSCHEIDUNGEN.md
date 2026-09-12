# Entscheidungen des Implementierers

Dieses Dokument hält fest, was die Spezifikation offen lässt und wie es entschieden wurde.
Es ist das Gegenstück zu [OFFENE_FRAGEN.md](OFFENE_FRAGEN.md): dort steht, was noch offen
ist, hier steht, was entschieden wurde und warum.

**Der Rahmen.** §1 der Spezifikation verlangt, fachliche Lücken nicht eigenständig zu
füllen, sondern `UNDEFINED` zu setzen und zurückzufragen. Version 1.0 dieses Repos hat
das getan — 23 offene Punkte. Der Auftraggeber hat daraufhin entschieden, dass der
Implementierer sie selbst festlegt. Diese Anweisung hebt §1 nicht auf, sondern verschiebt
die Verantwortung: jede Festlegung unten ist als solche gekennzeichnet, trägt einen
Status, der sie von einer belegten Angabe unterscheidet, und ist umkehrbar.

**Drei Kennzeichnungen** ziehen die Grenze zwischen Spezifikation und Entscheidung durch
den ganzen Code:

| Kennzeichnung | Bedeutung |
|---|---|
| `source_type = SPEC_SEED_MVP` gegen `IMPLEMENTER_AUTHORED` | Items aus §42–57 gegen ergänzte |
| `options_status = SPEC_GIVEN` gegen `IMPLEMENTER_AUTHORED` | Distraktoren aus der Spezifikation gegen autorisierte |
| `evidence_status = C`/`D`, nie `A`/`B` | keine Relation behauptet empirische Absicherung (§114) |

Damit ist jede Abfrage in der Lage, die Spezifikation von ihrer Ergänzung zu trennen.

---

## Inhaltliche Entscheidungen

### D-01 / D-02 — ID-Kollision `ZO07-D3-S-A` (löst F-10, F-11)

**Problem.** §24 definiert `ZO07-D3-S-A` als `49 + 36 = ?` (Antwort 85), §51 dieselbe ID
als `Du weißt: 38 + 20 = 58. Wie hilft dir das bei 38 + 23?` (Antwort `58+3=61`). Für
`48 + 37` aus §52 gibt es überhaupt keine ID.

**Entscheidung.** §51 behält die ID, weil §51 der Aufgabenbank-Abschnitt ist und §24 nur
ein Metadatenbeispiel. Das §24-Item wird `ZO07-D3-S-E`, `48 + 37` wird `ZO07-D3-S-F`,
Antwort 85 (arithmetisch bestimmt). Beide folgen damit dem Muster
`{Kompetenz}-{Stufe}-{Darstellung}-{Variante}` aus §42–57; die zwischenzeitlich
verwendeten Namen `ZO07-CONTRAST-01-A/B` passten nicht in dieses Muster. Der
Familienname `ZO07-CONTRAST-01` aus §52 bleibt unverändert.

**Umkehrbar?** Ja, per Umbenennung in `content/tasks.json` und `content/task_routes.json`.

### D-03 — Doppelt geführte Items zusammengelegt (löst F-20)

**Problem.** Drei Aufgaben erscheinen zweimal, zwei davon mit unterschiedlicher
Schwierigkeit — dieselbe Aufgabe kann nicht gleichzeitig D3 und D4 sein.

**Entscheidung.**

| Aufgabe | bleibt | entfällt | Begründung |
|---|---|---|---|
| `17·6 = 10·6 + 7·6` | `ZO13-D3-S-A` (D3, ZO13) | `ZO09-D4-S-A` | Die Frage „welche Rechnung entspricht" zielt auf das Rechengesetz, nicht auf das Ausrechnen |
| `49+36 → 50+35` | `ZO12-D2-S-A` (D2, ZO12) | `ZO07-D3-S-B` | Route R008 aus §70 zielt auf dieses Item |
| `37 auf 50 ergänzen` | **beide** | — | Unterschiedliche Frageform (Gleichung gegen Anweisung) ist eine legitime Oberflächenvariation nach §25 |

Das bleibende Item erhält die Kompetenz des entfallenden als `secondary_competency`, damit
die Evidenz weiterhin dort ankommt — als `INDIRECT_*` nach §28, also schwächer gewichtet.
Zwei getrennte Items hätten die Evidenz doppelt gezählt.

### D-09 — Distraktoren für elf Auswahlaufgaben (löst F-17)

**Problem.** Elf Items sind als Auswahlaufgabe formuliert („Welche Rechnung passt?"), aber
§42–57 nennt nur die richtige Antwort. Sie waren nach §113 nicht auslieferbar — darunter
mit `ZO09-GV-D1-I-A` und `ZO09-REL-D3-I-A` zwei Knotenpunkte des Routings aus §70.

**Entscheidung.** Für jedes Item vier Optionen, jeder Distraktor mit einer benennbaren
Fehlvorstellung und einem Fehlercode aus §59 verknüpft. Ein Distraktor, der nur falsch
ist, wäre diagnostisch wertlos; einer, der aus zwei Gründen gewählt werden kann, wäre
nicht interpretierbar. Beispiel `6 Kugeln + 3 weitere`: `6+3` richtig, `6-3` und `6·3`
bilden `ERR_OPERATION_SELECTION` ab, `9` bildet ab, dass das Ergebnis statt der Rechnung
gewählt wurde.

Die Herkunft steht in `task_payload.options_status`: `SPEC_GIVEN` bei den sechs Items,
deren Optionen §46–48 selbst nennen, `IMPLEMENTER_AUTHORED` bei den elf autorisierten.

### D-10 — Akzeptierte Antworten für `ZO05-D4-S-A` (löst F-18)

§49 sagt zu „Welche Zerlegung von 64 hilft dir bei 64 + 28?": „Mehrere Antworten können
mathematisch sinnvoll sein. Scoring darf nicht unnötig nur eine Strategie akzeptieren."
Welche das sind, steht nicht dort. Entschieden wurde eine Liste akzeptierter Zerlegungen
mit `scoring_rule = ANY_OF_ACCEPTED` und dokumentierter Normalisierung; jede akzeptierte
Antwort nennt die Strategie, die sie bedient.

### D-11 — Ergänzte Items (löst F-21, F-22)

**Problem.** Zwei zentrale Wege der Spezifikation waren nicht durchspielbar.

§70 verlangt `6·8 falsch → Parallelitem → wieder falsch → ikonische Darstellung 6·8`. Ein
Parallelitem zu `6·8` gab es nicht, und das einzige ikonische `6·8`-Item lag auf D3 statt
D2 und fragte eine Zerlegung statt eines Ergebnisses — Darstellung, Schwierigkeit und
Frageform wechselten gleichzeitig. §116 verlangt das Gegenteil.

§69 wechselte von D2/symbolisch nach D1/ikonisch, also Darstellung **und** Schwierigkeit.
§92 und §93 nannten Förderschritte („ikonische Stellenwerttafel", „H/Z/E mit Symbolen",
„Transfer"), für die kein Item existierte. §69 verlangte „Bündelung prüfen", ohne dass
ein Bündelungsitem existierte.

**Entscheidung.** Dreizehn Items, alle mit `source_type = IMPLEMENTER_AUTHORED`:

| Item | Zweck |
|---|---|
| `ZO09-D2-S-B` (7·6) | das in §70 verlangte Parallelitem |
| `ZO09-D2-I-A` (6·8 ikonisch), `ZO09-D2-I-B` (7·6 ikonisch) | ikonische Gegenprobe auf **gleicher** Stufe, mit **gleichem** Antwortformat |
| `ZO06-D2-I-A`, `ZO06-D2-I-B` | dasselbe für §69: ikonisches Stellenwertitem auf D2 mit gleicher Frageform |
| `ZO06-1-D1-ACTION-A/B` | die von §69 verlangte Bündelungsprüfung |
| `ZO06-SUP-D1-I-A`, `ZO06-SUP-D2-MIXED-A`, `ZO06-SUP-D3-L-A` | die drei Förderschritte aus §92 |
| `ZO09-SUP-D3-L-A` | der Transferschritt aus §93 |
| `ZO07-D2-S-C` (39+24), `ZO07-D2-S-D` (47+35) | siehe D-19 |

Die Familie `FAM_ZO09_6X8_REPRESENTATION` ist damit eine 2×2-Anordnung aus Darstellung
und Zahlenpaar: alle vier Items D2, ENTER, `EXACT_NUMERIC`. Jeder Einzelvergleich ändert
genau eine Variable. `FAM_ZO07_D2_TWO_DIGIT` wurde von `PARALLEL_ITEM` auf
`CONTRAST_ITEM` umgestellt.

Eine Prüfregel sichert das Ergebnis: jede Route mit `reason = CHANGE_REPRESENTATION` muss
Stufe und Antwortformat konstant halten, sonst bricht `validate` mit `ERROR` ab.

### D-12 — Kantenliste des Kompetenzgraphen (löst F-05)

**Problem.** §10 listet 50 Knoten, §11 stellt fest, dass der Graph kein linearer Baum ist
— die Kanten folgen also nicht aus der Reihenfolge. Eine Kantenliste gibt die
Spezifikation nicht an. Version 1.0 hatte 12 Kanten, 14 von 50 Knoten hingen im Graphen,
und keine einzige `SUCCESSOR`-Relation existierte.

**Entscheidung.** 77 weitere Kanten. Nach der Prüfrunde sind vier davon wieder
entfernt (drei zwischen synonymen Knoten, eine doppelt abgedeckt) und vier auf
`D` herabgesetzt; es bleiben 85 Kanten, 49 von 50 Knoten verbunden:

| Typ | C | D |
|---|---|---|
| `STRONG_PREREQUISITE` | 46 | 8 |
| `SUPPORTING_RELATION` | 9 | 2 |
| `CROSS_DOMAIN_RELATION` | 7 | 3 |
| `REPRESENTATION_RELATION` | 4 | — |
| `SUCCESSOR` | 3 | — |
| `HARD_PREREQUISITE` | 3 | — |

Kein `A` oder `B`: für keine Kante liegt eine empirische Fundstelle vor, und §114 verbietet
den höheren Grad ohne Quelle. Die Unterscheidung C gegen D ist inhaltlich gemeint — C für
fachdidaktisch gut gestützte Kanten, D für Systemhypothesen. Jede Kante nennt in `notes`
ihre Begründung.

Achtzehn naheliegende Kanten wurden **abgelehnt**, dokumentiert in
`content/_fragments/relationen.json`. Der wichtigste Ablehnungsgrund: reine
Reihenfolgekanten aus §10 und Eltern-Kind-Kanten, deren Inhalt schon `parent_id` trägt.
§11 sagt ausdrücklich, dass die Reihenfolge in §10 keine Lernreihenfolge ist — eine Kante,
die nur diese Reihenfolge nachzeichnet, behauptet mehr als sie weiß.

Die Engine begrenzt den Schaden einer falschen Kante: eine Voraussetzungskante erzeugt bei
richtiger Antwort indirekt positive Evidenz mit kleinem Gewicht und bei falscher Antwort
**gar keine** (siehe D-05). Eine falsche Kante kann damit ein Item auswählen, aber keine
Aussage über die Schüler:in erzeugen — genau die Grenze, die §13 für C- und D-Beziehungen
zieht.

### D-13 — Kompetenzbeschreibungen (löst F-01)

41 Knoten hatten keine Beschreibung, weil §10 nur Stichworte listet. Jetzt haben alle 54
eine, bestehend aus drei Teilen: was die Kompetenz ist, wie sie sich von ihren
Geschwistern abgrenzt, woran sie beobachtbar ist. Keine Aussage über Schwierigkeit,
Reihenfolge oder Klassenstufe; keine psychologische Zuschreibung (§32, §87).

**Sechs Geschwisterpaare ließen sich nicht trennscharf beschreiben** und sind als
Modellierungsproblem des Kompetenzgraphen dokumentiert, nicht als Beschreibungsproblem —
darunter `ZO16 Kopfrechnen` gegen `ZO17 halbschriftliches Rechnen`, wo der Unterschied im
Lösungsweg liegt und nicht in der Aufgabe, und `ZO18 Rechnen in Kontexten` gegen
`ZO19 Transfer`. Siehe F-24.

### D-14 — Die vier undefinierten Fehlercodes (löst F-06)

§59 listet 16 Codes ohne Definition. Zwölf sind aus anderen Abschnitten belegbar, vier
waren offen:

| Code | Entscheidung |
|---|---|
| `ERR_SINGLE` | Auffangcode: genau dann, wenn die Antwort falsch ist und kein spezifischerer Code greift. Wird von `hypotheses.py` nicht ausgewertet, kann also keine Diagnose auslösen. |
| `ERR_OPERATION_CONCEPT` | Wechsel der **Operationsklasse** (additiv gegen multiplikativ). Abgrenzung zu `ERR_OPERATION_SELECTION`: gleiche Klasse mit vertauschter Richtung oder vertauschten Operanden ist eine Auswahlverwechslung. |
| `ERR_STRATEGY` | Nur bei Items, deren Antwort selbst ein Rechenweg ist. Bei einer Ergebniseingabe ist die Strategie nicht beobachtbar; eine Vergabe wäre eine Inferenz, für die §76 kein Verfahren vorsieht. |
| `ERR_REPRESENTATION` | Wird von `scoring.classify()` **nie** vergeben. §32 verbietet den Schluss vom Darstellungsunterschied auf eine Eigenschaft, und ein Unterschied ist an einem einzelnen Versuch ohnehin nicht ablesbar. Den Code setzt nur der Facettenvergleich. |

Zusätzlich wurde die Abgrenzung `ERR_ZERO_PLACEHOLDER` gegen `ERR_PLACE_VALUE` präzisiert:
der Nullstellenfehler greift nur bei **inneren** Nullen (508 als 58), eine fehlende Endnull
(60 als 6) ist eine Stellenwertverwechslung. Ohne diese Präzisierung wären die beiden
Codes aus §59 nicht trennscharf.

### D-15 — Skala für `language_demand` (löst F-03)

§81 führt das Feld, definiert aber keine Skala. Entschieden wurde eine operationale
Vierstufigkeit, an der Aufgabenformulierung ablesbar: `NONE` (keine Wörter außer Zahlen und
Rechenzeichen), `LOW` (kurze Standardanweisung ohne Kontext), `MEDIUM` (ein Satz mit
gegebenem Fakt oder Bedingung), `HIGH` (mehrere Teilsätze mit Sachkontext, aus dem die
relevante Information auszuwählen ist). Bei `HIGH` wird zusätzlich das
`additional_demand LANGUAGE_DEMAND` aus §15 gesetzt.

### D-16 — Darstellungsmodus der ZP05-Items (löst F-15)

§46 gibt für die drei ZP05-Items kein Darstellungskürzel an, anders als §42–45. Entschieden
nach Aufgabeninhalt: `ACTION` beim zweifachen Abzählen, `IMAGE` bei den beiden
Vorhersageitems. Die IDs bleiben unverändert, damit die Zitierbarkeit gegenüber §46
erhalten bleibt.

### D-17 — Anordnung bei vier Zählitems (löst F-14)

§9 verlangt ausdrücklich, die Anordnung als Aufgabenmerkmal zu speichern — „eine Menge
kann in einer Reihe korrekt gezählt werden, während dieselbe Anzahl kreisförmig
Schwierigkeiten verursacht". §44, §45 und §47 geben sie für vier Items nicht an.
Entschieden wurde `UNORDERED`, weil eine Reihe die Beobachtung mit ZP01 konfundieren würde.

### D-19 — Merkmalsregeln (löst F-12)

Drei operationale Regeln, damit die Merkmalsvergabe reproduzierbar wird statt kuratiert:

- `SMALL_FACTS` / `LARGE_FACTS`: Produkt ≤ 25 gegen > 25.
- `NEAR_ROUND_NUMBER`: bei Rechenaufgaben liegt der **erste** Operand höchstens 2 von
  einem Vielfachen von zehn entfernt (zweistellig) beziehungsweise ein Operand höchstens 2
  von einem Vielfachen von hundert (dreistellig); bei Vergleichs- und Ergänzungsaufgaben
  ist eine runde Zahl ausdrücklich Bezugs- oder Zielwert.
- `CROSSES_THOUSAND` als neuer Term, weil §20 nur Zehner und Hunderter kennt,
  `ZO04-D3-S-A` aber einen Tausender überschreitet.

**Die `NEAR_ROUND_NUMBER`-Regel hatte eine Folge.** Sie reproduziert §71 für die Contrast
Family — 49+36 und 48+37 tragen das Merkmal, 37+28 und 46+27 nicht — vergibt es aber
zusätzlich an `38+27`. Damit war das bisherige Paar `38+27` / `46+38` kein Parallelpaar
mehr. Statt die Regel zurechtzubiegen, wurden zwei Items ergänzt (D-11), die zwei saubere
Paare herstellen: `38+27` mit `39+24` (beide mit Merkmal), `46+38` mit `47+35` (beide
ohne). Auf D2 entsteht damit derselbe Kontrast, den §52 auf D3 aufbaut.

Das ist der Grundfall dieser ganzen Übung: eine Regel, die eine Inkonsistenz aufdeckt,
wird nicht abgeschwächt, sondern der Content wird korrigiert.

### D-21 — Klassenstufenreferenzen (löst F-04)

§79 führt `grade_reference_min/max`, §94 spricht nur von Aufgaben, keinem Knoten und
keinem Item ist eine Stufe zugeordnet. Entschieden wurde eine Ableitung aus Zahlenraum und
Operation, von „Zählprinzipien und Zahlen bis 20" (1) bis „mehrstellige Multiplikation mit
zweistelligem Faktor" (5). Kompetenzknoten erhalten Minimum und Maximum über ihre Items.

§94 bleibt gewahrt: `routing.allow_above_grade` ist `true`, das Routing kennt keine
Klassenstufenschranke. §2 ist der Grund — „eine Schüler:in soll nicht künstlich auf
Aufgaben der eigenen Klassenstufe begrenzt werden".

### D-22 — Quellenangaben (F-02 bleibt teilweise offen)

§111 nennt KMK, IQB, PIKAS/DZLM und Gelman & Gallistel, aber keine Fundstellen; §5 und
§112 berufen sich auf Forschung ohne Zitation. Ergänzt wurden nur belastbare Angaben
(Gelman & Gallistel 1978, KMK-Fassung 2022). **Es wurden keine Fundstellen erfunden.** Wo
keine vorliegt, bleibt `url_or_doi` leer und die Quelle behält
`source_type = THEORETICAL` mit dem Vermerk `UNDEFINED`.

Das ist die eine Stelle, an der die Anweisung „entscheide alles" nicht befolgt wurde: eine
erfundene Literaturangabe wäre schlechter als eine offene. §114 hängt daran — ohne
Fundstelle darf keine Relation `A` oder `B` tragen, und genau das hält der Graph ein.

---

## Entscheidungen der Engine

### D-05 — Evidenz- und Statusregeln (löst F-08)

§63 führt `direct_evidence_score`, `indirect_evidence_score` und `evidence_consistency`,
§65 führt `strength` — für keines gibt es eine Berechnungsvorschrift, und §117 verbietet
den naheliegenden Ersatz („73 % richtig → ZO07 = 73 % verliert Informationen").

**Evidenzstärke.** `Gewicht je Evidenzart × (support_discount, falls mit Hilfe gelöst)`.
Bewusst ohne Zeitfaktor: §62 verbietet, aus Bearbeitungszeit auf Kompetenz zu schließen.
Gewichte: direkt 1.0, indirekt 0.4, Unterstützung 0.5, leitideenübergreifend 0.3. Die
Abstufung setzt §31 um — „je weiter die Schlussfolgerung vom beobachteten Verhalten
entfernt ist, desto stärkere Evidenz muss erforderlich sein".

**Asymmetrie mit Absicht.** Ein richtiger Versuch erzeugt indirekt positive Evidenz auf den
Voraussetzungen (wer 6·8 löst, hat die Voraussetzungen wahrscheinlich). Ein falscher
Versuch erzeugt **keine** indirekt negative Evidenz auf den Voraussetzungen — das wäre der
Schluss „Aufgabe falsch, also Voraussetzung fehlt", den §29 und §121 verbieten. Stattdessen
löst der Fehler nach §30 ein Parallelitem aus und erst nach Replikation nach §31 eine
Voraussetzungsprüfung. Ein Test sichert diese Asymmetrie ab.

**Konsistenz.** `|positiv − negativ| / (positiv + negativ)`, also 1.0 bei einheitlicher
Richtung und 0.0 bei hälftigem Widerspruch. Schwelle 0.8.

**Kompetenzstatus nach Schwierigkeitsstufen getrennt**, nicht aggregiert — das ist die
direkte Anwendung von §117:

| Befund | Status | Begründung |
|---|---|---|
| reproduzierbarer Fehler auf einer Stufe | `SUPPORT_FOCUS` | Die Grenze ist lokalisiert, §91 setzt hier die Förderung an. §99 erwartet genau das. |
| reproduzierbarer Erfolg, nirgends Fehler | `SECURE` | §27: aktuell ausreichend konsistente Evidenz, nicht „dauerhaft" |
| Widerspruch **innerhalb** einer Stufe | `UNCERTAIN` | §71: nicht pauschal herabstufen, sondern Merkmale vergleichen. §101 erwartet genau das. |

Die Unterscheidung zwischen `SUPPORT_FOCUS` und `UNCERTAIN` ist der Kern: eine
stufenweise Grenze heißt Förderbedarf, merkmalsweise Streuung innerhalb einer Stufe heißt
offene Frage. Ein flacher Zähler hätte beides zu „unsicher" verschmolzen und damit genau
die Information verloren, die §117 erhalten will.

**Ergänzt nach der Prüfrunde (D-30):** eine Stufengrenze setzt voraus, dass die Fehler
nicht vollständig durch eine Bedingungsabhängigkeit erklärt sind. Scheitern auf einer Stufe
genau die Items ohne ein bestimmtes Merkmal und gelingen die mit, ist die Stufe nicht
unerreichbar — dann gilt `UNCERTAIN`. §71 wörtlich: „Nicht: ADDITION = UNSAFE. Sondern
Merkmale vergleichen."

**Parken** verlangt zusätzlich zwei **verschiedene** richtig gelöste Items. §38 sagt nur
„ausreichend konsistent"; zwei richtige Versuche an derselben Aufgabe sind das nicht, weil
§19 feststellt, dass Aufgaben derselben Kompetenz nicht austauschbar sind, und §26 dafür
den Marker `ITEM_SPECIFIC_SUCCESS` vorsieht.

### D-04 — Facetten statt Prozentwert (§117, §118)

§117 verlangt statt eines Prozentwerts eine Aufschlüsselung, und §118 zeigt sie:
„ZO09: concept = secure, symbolic = uncertain, iconic = secure, derived strategy =
uncertain". Diese Facetten sind keine Kompetenzknoten, sondern Aufgabenmerkmale.

Deshalb die Tabelle `student_competency_facets`: je Kompetenz und Merkmalswert ein eigener
Status, über acht Facettenklassen (Darstellung, Bedienform, Schwierigkeit, Aufgabenzweck
und die vier Merkmalslisten aus §20–23). `facet_kind` ist selbst ein Vokabularname, eine
neue Klasse braucht also keine Migration (§108).

Die Lehrkraftansicht zeigt daraufhin nirgends einen Prozentwert — ein Test prüft, dass das
Zeichen `%` im Bericht nicht vorkommt.

### D-06 — Unbezifferte Schwellen (löst F-07)

| §  | Mechanismus | Entscheidung |
|---|---|---|
| §73 | „STOP TESTING THIS NODE" | `testing.max_items_per_node = 6`. Eine reine Informationsschwelle wäre ohne empirische Kalibrierung nicht bestimmbar, eine Itemobergrenze ist es. |
| §72 | `TRANSFER_STABLE` über fünf Variationsdimensionen | drei von fünf. Zwei wären schon durch ein Parallelitem und einen Darstellungswechsel erreichbar und sagten nichts über Transfer. |
| §14 | „mehrere unabhängige Beobachtungen" | drei. Höher als die zwei für eine Darstellungshypothese, weil §31 Schritt 12 die kognitive Hypothese als die am weitesten vom Verhalten entfernte Schlussfolgerung einordnet. |
| §67 | „small candidate task pool" | 25. |
| §34 | Sprünge für D2 und D4 | Nachbarstufe, analog zu den in §34 genannten. |

Vier **zusätzliche Score-Summanden**, die §68 nicht nennt, aber die Priorisierung aus §67
im Score sichtbar machen statt sie im Code zu verstecken:

- `route` (Gewicht 10.0, skaliert mit der Routenpriorität): §67 stellt „1 Fehler
  replizieren, 2 Hypothese unterscheiden" der generischen Bewertung voran.
- `confirmation` (2.0): §41 macht die Bestätigung zur Bedingung für `SECURE`, also zur
  Anforderung und nicht zur Vorliebe. Greift nur, wenn die Bestätigungsstufe auch die
  Zielstufe ist — sonst würde sie den Sprung aus §34 verhindern, den §98 ausdrücklich
  erwartet.
- `family_completion` (1.2): die diagnostische Einheit ist nach §25 und §58 die Familie.
  Eine halb bearbeitete Contrast-Familie liefert keinen Vergleich.
- `facet_novelty` (0.6): §19 und §71 — ein Item mit unbeobachteter Merkmalskombination
  liefert mehr Information.

Die Redundanzstrafe zählt Items **derselben Familie nicht mit**: §116 verlangt für ein
Parallel- oder Contrast-Item ausdrücklich gleiche Stufe und gleiche Darstellung. Ohne diese
Ausnahme hätte die Strafe genau die Wiederholung bestraft, die §25 und §30 fordern.

### D-07 — Zeitgrenzen (löst F-09)

§39 fordert „Zeitgrenzen nicht hardcoden" und nennt `EVIDENCE_TOO_OLD` als
Reaktivierungsgrund. Entschieden: 90 Tage (etwa ein Schulhalbjahr) für
`park.evidence_too_old_days`, 30 Tage für `park.next_review_interval_days`. Beide stehen in
`system_config`, nirgends im Code, und auf `null` gesetzt schaltet sich der jeweilige
Mechanismus ab statt zu raten.

Dazu kam ein **Zirkel**, den §39 nicht adressiert: §38 entfernt eine geparkte Kompetenz aus
dem Aufgabenpool, also entsteht dort keine neue direkte Evidenz, die sie nach §39
zurückholen würde. Gelöst mit der Wiedervorlage — vor jeder Auswahl werden alle geparkten
Knoten auf alle drei Reaktivierungsgründe geprüft. Genau dafür führt §40 die Felder
`last_review` und `next_review`. Zusätzlich zählt wiederholte **indirekte** negative
Evidenz als widersprüchlich, weil §103 („später mehrere Stellenwertfehler") den Fall
beschreibt, dass die Fehler beim Rechnen an anderer Stelle auftreten.

### D-08 — Kontextbedingung für Routen (löst F-23)

§83 sieht für eine Route nur `condition` vor, also allein das Ergebnis der
Vorgängeraufgabe. Die Förderrouten aus §92 und §93 dürfen aber nur greifen, wenn
`SUPPORT_FOCUS` gesetzt ist — sonst lenkt eine richtig gelöste Screening-Aufgabe in eine
Förderkette. Das war in der ersten Simulation von Testfall A sofort sichtbar: Route R013
führte ein Kind mit hoher Kompetenz in die Multiplikations-Förderkette.

**Entscheidung.** Zwei Spalten `requires_status` und `requires_hypothesis` in
`task_routes`; acht Routen nutzen sie. Die Alternative wäre gewesen, die Bedingung im Code
zu prüfen — das verbietet §84.

Ergänzend: eine Route, deren Zielaufgabe bereits gestellt wurde, gilt als erledigt und
feuert nicht erneut. Zweck einer Route ist eine **neue** Beobachtung; §30 verlangt für die
Replikation ausdrücklich ein Parallelitem, nicht dieselbe Aufgabe. Ausnahme: `REACTIVATED`,
wo die Wiederholungsprüfung nach §39 genau der Zweck ist.

### D-24 — Vergleichsbedingung für Abhängigkeitshypothesen

§116 verlangt den Grundsatz der minimalen Veränderung, §32 verbietet die
Überinterpretation eines Darstellungsunterschieds. Eine Hypothese „symbolisch schlechter
als ikonisch" wird deshalb nur eröffnet, wenn die verglichenen Beobachtungen **dieselbe
Schwierigkeitsstufe und dasselbe Antwortformat** haben. Zwei symbolische Fehler auf D3
gegen zwei ikonische Erfolge auf D1 lassen den Unterschied nicht der Darstellung
zuordnen — er könnte an der Stufe liegen.

Das ist die strengste Einzelentscheidung dieses Systems, und sie hat den Content
verändert: solange die Aufgabenbank kein gleichstufiges Paar hatte, eröffnete die Engine
keine Hypothese und machte damit F-21 sichtbar, statt es in einer zu frühen Hypothese zu
verstecken. Erst die Items aus D-11 haben die Voraussetzung geschaffen. Abschaltbar über
`hypothesis.require_same_difficulty_for_dependency`.

**Zweitens:** mehrwertige Merkmale werden nach **Anwesenheit gegen Abwesenheit**
verglichen, nicht Wert gegen Wert. §71 beschreibt genau das — 49+36 gelingt mit
`NEAR_ROUND_NUMBER`, 37+28 ohne. Ein Wert-gegen-Wert-Vergleich findet das nicht, weil
49+36 sowohl `COMPENSATION` als auch `DECOMPOSITION` nahelegt. Für die einwertige
Darstellung bleibt der Wert-gegen-Wert-Vergleich richtig. Dieselbe Unterscheidung gilt für
die Profilmarker aus §26 — ein Marker und eine Hypothese beschreiben denselben Befund,
also muss die Erkennungsregel dieselbe sein.

### D-25 — Widerlegbarkeit technisch erzwungen

§115 verlangt, dass eine Hypothese durch eine Aufgabe widerlegt werden kann. Umgesetzt
als Bedingung: existiert kein widerlegendes Item, wird die Hypothese **nicht** eröffnet,
und das wird als `BLOCKED_NOT_FALSIFIABLE` gemeldet. Das ist dann ein Befund über die
Aufgabenbank, keine Ausnahme — und war der Weg, über den F-22 in der Simulation sichtbar
wurde: die Voraussetzungshypothese zu ZO06 blieb blockiert, solange kein Bündelungsitem
existierte.

### D-26 — Was der Simulation die Lehrkraft vorgibt

Zwei Eingriffe, die §3 ausdrücklich erlaubt („Die Lehrkraft kann Aufgaben auswählen,
Aufgaben sperren, Förderpfade verändern, Systementscheidungen übersteuern"), damit die
Testfälle reproduzierbar sind:

- **Einstiegsaufgabe.** §98–§103 beginnen jeweils an einem benannten Item. Ab der zweiten
  Aufgabe entscheidet ausschließlich die Engine.
- **Fokus** auf einen Kompetenzknoten. Strikt, ohne automatische Erweiterung auf
  Voraussetzungen — bei einem dichten Graphen (§11) wäre sonst das halbe Netz drin und die
  Einschränkung wirkungslos. Eine Voraussetzung erreicht den Pool weiterhin über eine
  Route mit `reason = CHECK_PREREQUISITE`, also genau dann, wenn eine fachliche Regel sie
  verlangt — nicht schon, weil sie existiert.

---

## Die Prüfrunde

Der autorisierte Inhalt wurde anschließend geprüft — technisch (Vokabulare, Verweise,
Arithmetik, Zyklen) und fachdidaktisch (§116, §32, Distraktorqualität, Trennschärfe der
Beschreibungen). Ergebnis: **43 Befunde, davon acht gravierend.** Alle inhaltlichen
Befunde sind abgearbeitet, die verbleibenden Fragen stehen als F-25 bis F-27 in
[OFFENE_FRAGEN.md](OFFENE_FRAGEN.md).

Drei Befunde machten das jeweilige Item diagnostisch wertlos. Sie sind lehrreich, weil sie
alle dieselbe Form haben: das Item war auf einem Weg lösbar, den die Zielkompetenz nicht
braucht.

**Das Bündelungsitem war durch Ziffernablesen lösbar.** „Hier liegen 13 Einerwürfel.
Bündle so viele Zehner, wie du kannst. Wie viele Zehner und wie viele Einer bleiben
übrig?" — die richtige Antwort (1 Zehner, 3 Einer) sind die beiden Ziffern von 13. Das
Item konnte `ZO06_1_BUNDLING` nicht messen, und die Rückwärtsschritte aus §69 hingen daran.
Korrektur: Fünferbündel. 13 zu Fünfern ergibt 2 Bündel und 3 übrig — die Antwort steht
nicht in den Ziffern. Das Zehneritem bleibt als Kontrastpartner, wodurch genau eine
Variable variiert (§116): die Bündelungsgröße. Gelingt nur das Zehneritem, spricht das für
Ablesen statt Bündeln — aus dem Fehler ist ein diagnostisches Paar geworden.

**Das ikonische Multiplikationsitem war durch Abzählen lösbar.** Ein offenes
6×8-Punktfeld mit freier Ergebniseingabe lässt sich auszählen, der symbolische Partner
`6 · 8` nicht. Der Vergleich hielt damit nicht die Darstellung als einzige Variable
konstant, sondern variierte auch die Menge der zulässigen Lösungswege — und genau die trug
den Befund. Korrektur: Malwinkel mit verdecktem Inneren. Zeilen- und Spaltenzahl bleiben
sichtbar, das Ergebnis muss multiplikativ bestimmt werden. §62 verbietet, das über eine
Zeitgrenze zu lösen.

**Drei Items enthielten als Distraktor den Zahlenwert der richtigen Rechnung.** Bei „6
Kugeln und 3 weitere — welche Rechnung passt?" stand `9` zur Auswahl. Wer sie wählt, hat
die Situation richtig modelliert und ausgerechnet, also genau die Grundvorstellung
gezeigt, die das Item prüfen soll — und wurde als falsch gewertet und nach §70 in die
Förderkette „Grundvorstellung prüfen" geleitet. Korrektur: die Distraktoren prüfen nur noch
die Operationsklasse. Ein Rollentausch ist als Distraktor übrigens unbrauchbar, weil er bei
kommutativen Operationen denselben Wert ergibt und vom Scoring als richtig gilt.

### D-29 — Die Frageform als dritte Variable (§116)

Der schärfste Befund betraf die Reparatur selbst. Nach D-11 hielt der
Darstellungsvergleich aus §69 Schwierigkeit und Antwortformat konstant — aber nicht die
**Frageform**: symbolisch wird eine ZIFFER genannt und ihre Stelle muss lokalisiert werden
(„Welchen Wert hat die Ziffer 6 in 364?"), ikonisch wird die STELLE genannt („Welchen Wert
haben die Zehnerstangen zusammen?"). F-21 war damit nur teilweise gelöst.

Ohne ein Feld dafür wäre das eine Fußnote geblieben. Also gibt es jetzt eines:
`tasks.question_form` mit 27 Termen, für alle 97 Items belegt. Der Vergleichsschlüssel für
Abhängigkeitshypothesen umfasst Stufe, Antwortformat **und** Frageform; die Prüfregel für
Routen ebenso.

Beim Einschalten fand die Regel sofort drei konfundierte Routen — darunter die, die im
selben Schritt zur Reparatur ergänzt worden war. Das ist das beste Argument für das Feld.

Die Kette nach §69 ist daraufhin in zwei Schritte getrennt, und §31 gibt die Reihenfolge
selbst vor:

| Schritt | §31 | Was variiert |
|---|---|---|
| `ZO06-D2-S-A` → `-S-B` | §30 | nichts (Parallelitem) |
| `-S-B` → `-S-C` | Schritt 7, Aufgabentyp | nur die Frageform, bleibt symbolisch |
| `-S-C` → `-S-D` | §30 | nichts (Parallelitem) |
| `-S-D` → `ZO06-D2-I-A` | Schritt 8, Darstellung | nur die Darstellung |
| `-I-A` → `-I-B` | §30 | nichts (Parallelitem) |

Jeder Einzelschritt ist nach §116 interpretierbar. Dafür brauchte es zwei weitere
symbolische Items und einen neuen `ROUTE_REASON` (`CHECK_TASK_TYPE`, §31 Schritt 7). Die
Seed-Items bleiben unberührt (§1).

Bei der Multiplikation ist die Frageform **nicht** trennbar: eine Multiplikation ikonisch
zu stellen heißt notwendig, die Faktoren als Struktur zu zeigen. Die Frageform beider
Seiten ist deshalb `COMPUTE_RESULT` — verlangt wird das Produkt, nur die Darbietung der
Faktoren unterscheidet sich. Das ist die Darstellungsdifferenz selbst und keine zweite
Variable.

### D-30 — Eine Stufengrenze verlangt variierte Bedingungen

Testfall D endete zunächst auf `SUPPORT_FOCUS`, obwohl §101 „nicht pauschal herabstufen"
verlangt. Ursache: die beiden Fehler auf D2 teilten dasselbe fehlende Merkmal — die Engine
hatte aus einer merkmalshomogenen Stichprobe eine Stufengrenze geschlossen.

Korrektur: ein reproduzierbarer Fehler auf einer Stufe ist nur dann eine Grenze, wenn er
**nicht** vollständig durch eine Bedingungsabhängigkeit erklärt ist. Scheitern genau die
Items ohne `COMPENSATION` und gelingen die mit, dann ist die Stufe nicht unerreichbar —
die Aufgabenmerkmale entscheiden. Das ist der Unterschied zwischen Testfall B (auch
ikonisch falsch, also Grenze) und Testfall D (nur ohne das Merkmal falsch, also
Abhängigkeit), und es ist §71 wörtlich: „Nicht: ADDITION = UNSAFE. Sondern Merkmale
vergleichen."

### Weitere abgearbeitete Befunde

- Drei Voraussetzungskanten zwischen Knoten, die dasselbe bezeichnen, sind entfernt
  (`REL_019`, `REL_021`, `REL_038`). Eine Kante zwischen Synonymen ist nach §115 nicht
  widerlegbar und erzeugt in der Rückwärtssuche nach §36 garantiert redundante
  Kontrollaufgaben — genau das, was §73 verbietet. Die Knotenpaare stehen jetzt unter F-24.
- `ZO06_4` wurde von zwei Autorierungslinien verschieden definiert. Verbindlich ist die
  Definition aus den Kompetenzbeschreibungen; `REL_051` ist daraufhin entfallen, weil
  `REL_048` die Beziehung dort abdeckt.
- Vier Kanten, deren Begründung sich auf die Reihenfolge in §10 stützte, sind auf
  `evidence_status = D` herabgesetzt. Dass ein Item die andere Operation als bekannt
  vorgibt, ist eine Aufgabendesign-Entscheidung, kein Entwicklungsvorrang (§11).
- `FAM_ZO06_D3_ZERO` konnte den Nullstellenfehler replizieren, aber nicht kontrastieren —
  beide Mitglieder trugen eine Null an der Zehnerstelle. Ein nullfreies Kontrollitem (538)
  auf derselben Stufe trennt jetzt ZO06.5 von ZO06.6.
- `SMALL_FACTS` und `LARGE_FACTS` galten auch für mehrstellige Multiplikationen. „Fakt" im
  Sinne von §20 ist ein abrufbares Einsmaleins-Ergebnis; die Regel gilt jetzt nur für
  einstellige Faktoren.
- Zwei Routen hatten denselben Schlüssel aus `source_task` und `condition`; ohne
  Prioritätsunterschied hätte die Sortierung nach `route_id` entschieden.
- Das Parallelitem zu `6·8` war `7·6` und änderte beide Faktoren samt ihren Rollen. Jetzt
  `6·7`: die Gruppenanzahl bleibt konstant, nur die Gruppengröße variiert (§25).
- Zwei Distraktoren waren aus je zwei Gründen wählbar und damit nicht diskriminierend;
  einer von drei separat richtig gerechneten Distraktoren blieb, die übrigen entfielen.
- Bei identischen Zahlen müssen die Zahlmerkmale identisch sein — `403−198` trug in zwei
  Items verschiedene.

### Was die Prüfrunde über das Verfahren zeigt

Kein Befund betraf die Architektur, alle betrafen den Inhalt — und die schwersten waren
Items, die auf einem Umweg lösbar waren, den die Zielkompetenz nicht braucht. Das ist
genau die Fehlerklasse, die §116 adressiert und die man einem Item nicht ansieht, solange
man nur prüft, ob die Antwort richtig ist.

Zwei Korrekturen haben den Inhalt verbessert, statt ihn nur zu reparieren: aus dem kaputten
Bündelungsitem ist ein diagnostisches Kontrastpaar geworden, und aus der konfundierten
§69-Kette eine Sequenz, die §31s eigene Prüfreihenfolge abbildet.

---

## Was nicht entschieden wurde

Drei Punkte bleiben offen, obwohl „entscheide alles" auch sie umfasst. In allen drei Fällen
wäre eine Festlegung schlechter als eine offene Frage:

**F-02, Literaturangaben.** Eine erfundene Fundstelle würde §114 aushebeln: die Prüfregel
erlaubt `evidence_status = A` nur mit amtlicher oder empirischer Quelle. Mit einer
erfundenen Quelle wäre jede Relation formal abgesichert und die Unterscheidung zwischen
belegt und plausibel wertlos.

**F-16, Zuordnung der Items zu Unterknoten.** §42–57 ordnet die Items über die
Kapitelüberschrift der Gruppenebene zu (`ZO06`), nicht den neun Unterknoten aus §10.
33 der 50 MVP-Knoten haben deshalb kein eigenes Item. Eine eigenständige Zuordnung wäre
eine fachdidaktische Entscheidung mit direkter Folge für jede Statusaussage — und sie ist
nicht nötig, weil die Facettenaufschlüsselung aus D-04 dasselbe leistet: §118 arbeitet
ohnehin mit Facetten („concept", „symbolic", „iconic"), nicht mit Unterknoten.

**F-24, sechs nicht trennscharfe Geschwisterpaare.** Wenn `ZO16 Kopfrechnen` und
`ZO17 halbschriftliches Rechnen` sich nur im Lösungsweg unterscheiden, den das MVP nicht
beobachtet (§76), dann ist keine Beschreibung möglich, die ein Item eindeutig zuordnet.
Das ist ein Modellierungsproblem des Kompetenzgraphen aus §10, kein Textproblem — es zu
überschreiben würde es verdecken.
