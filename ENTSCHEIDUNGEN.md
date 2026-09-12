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

## Zweite Prüfrunde — die Oberfläche und die Replikation

Mit dem interaktiven Durchlauf (§105) kam ein Pfad hinzu, den vorher nur die Simulation
ging. Eine Prüfung über fünf Regelklassen lieferte 16 Befunde, davon **3 bestätigt und 13
widerlegt**. Die Widerlegungsquote ist selbst ein Ergebnis: die meisten Verdachtsfälle
scheiterten daran, dass weiter unten im Pfad eine Absicherung greift, die der erste Blick
nicht sieht.

### D-31 — Fehlerreplikation als eigener Score-Summand (§29, §30, §31, §67)

§29 ist die Grundregel des ganzen Systems: „TASK A WRONG führt **nicht** zu
`COMPETENCY = NOT_MASTERED`, sondern zunächst zu `OBSERVATION = ERROR`. Dann:
Parallelitem." §67 nennt „replicate error" als **erste** Priorität, §31 das Parallelitem
als Rang 2 von 12 — noch vor Voraussetzung, Strategie und Darstellung.

`tasks.parallel_item_id` trug diese Beziehung bisher nur als Datenfeld. Das Routing las es
nirgends. Fünf Items hatten eine ausdrückliche `REPLICATE_ERROR`-Route; die übrigen
dreizehn trafen ihr Parallelitem nur dann, wenn der **ergebnisblinde** Familienbonus
zufällig reichte — er zahlt nach einer richtigen Antwort genauso wie nach einer falschen.
Bei `ZO07-D2-S-A`, `ZO07-D2-S-B` und `ZO13-D3-S-A` reichte er nicht: dort stand das
Parallelitem auf Rang 25 von 96.

Verschärfend kam hinzu, dass ein Fehler den betroffenen Knoten **abwertet**:
`information_need` fällt von 1.0 (`UNKNOWN`) auf 0.7 (`ACTIVE`), `facet_novelty` auf 0.0.
Der Score bewegte sich nach einem Fehler also vom Fehler weg. Und ohne Replikation löst
`_is_repeated_pattern` nie aus — §30 verlangt aber ein reproduzierbares Muster, bevor eine
Hypothese entstehen darf. Für diese Items lief die Diagnostik leer.

Entscheidung: ein eigener Summand `score.weight_replication`, in derselben Größenordnung
wie eine Route mit `priority = 100`. Das ist kein neues Gewicht, sondern dieselbe
Priorität — einmal aus dem Inhalt, einmal aus der Regel. Er greift nicht, wenn eine Route
das Item ohnehin trägt: wo der Inhalt eine Route gesetzt hat, gilt der Inhalt.

Die erste Fassung hatte keine Schranke und replizierte nach **jedem** Fehler. Testfall B
wuchs dadurch von vier auf sieben Aufgaben, ohne eine einzige zusätzliche Beobachtung —
genau das Übertesten, das §73 verbietet. Die Schranke ist jetzt
`mastery.failure_replication_required` und zählt **je Kompetenz, nicht je Familie**:
repliziert wird der Fehler, nicht das Item. Zwei Fehler mit demselben Code auf ZO06 sind
ein Muster, auch wenn sie in verschiedenen Familien liegen. Steht das Muster fest, ist die
Replikation erledigt und §31 geht zu Rang 3 weiter, der Voraussetzung.

Ergebnis: **18 von 18** Items mit deklariertem Parallelitem treffen es nach einem Fehler,
vorher 12 — und die 12 trafen es aus Punktzufall, nicht aus Regel.

### D-32 — Bearbeitungszeit wird gespeichert (§60, §62) — Korrektur einer Fehlentscheidung

Der interaktive Durchlauf übergab zunächst `time_seconds = None`, mit Verweis auf §62.
Das war falsch gelesen. §62 sagt zweierlei, und beides gilt:

> Zeit speichern. **Aber:** „langsam = schwache Kompetenz" ist nicht zulässig.
> Bearbeitungszeit wird zunächst nur als Kontextinformation gespeichert.

§60 führt `time_seconds` ausdrücklich unter den zu speichernden Rohdaten. Gespeichert wird
also, ausgewertet nicht. Die zweite Hälfte hängt ohnehin nicht an der Oberfläche, sondern
am Sperrschlüssel `evidence.time_seconds_used_for_inference = false`, den eine Prüfregel
hält. Nur zu speichern wäre zu wenig gewesen, nur zu messen zu viel.

### D-33 — Übersteuern gehört ins Entscheidungsprotokoll (§88, §89)

`next_task()` schreibt seine Protokollzeile, bevor die Lehrkraft den Vorschlag übergehen
kann. Wurde nur das Objekt im Speicher geändert, nannte `routing_decisions` eine Aufgabe,
die nie gestellt wurde — und §88 fragt ausdrücklich: „Warum hat das System diesen Pfad
gewählt?" Eine Antwort, die die tatsächlich gestellte Aufgabe verschweigt, ist keine.

Korrigiert wird jetzt die bestehende Zeile, nicht eine zweite geschrieben: es war eine
Entscheidung, nur nicht die des Systems. `rule_triggered` wird `TEACHER_OVERRIDE`, die
Konfidenz sinkt auf `LOW`, weil die Begründung nicht mehr vom Score stammt.

### D-34 — `students.notes` entfernt (§86)

Ein Freitextfeld auf der einzigen Tabelle, die eine Person identifiziert — von keiner
Zeile Code je geschrieben oder gelesen. §86 verlangt „nur Daten, die für die Funktion
notwendig sind"; ein unbeschriftetes Textfeld neben einer Personen-ID ist die
wahrscheinlichste Stelle, an der ein Klarname oder eine medizinische Bemerkung landet.

Der zugehörige Test war eine **Sperrliste** verbotener Spaltennamen (`name`, `diagnose`,
…) und hätte `notes` nie gefangen. Er ist jetzt eine **Positivliste**: jede Spalte braucht
einen Abschnittsverweis, der ihre Notwendigkeit belegt. §86 formuliert die Regel ohnehin
positiv — notwendig oder gar nicht.

### Widerlegt: der Cross-Domain-Verdacht

Beim Testen fiel auf, dass eine falsche Antwort auf die Zahlenstrahlaufgabe negative
Evidenz auf `L2_MEASUREMENT`, `L3_PATTERN_FUNCTION` und `L4_SPACE_SHAPE` schreibt — und
§14 sagt zu genau diesem Item, ein Fehler bedeute *nicht* „räumliches Vorstellungsvermögen
schwach". Der Verdacht hielt der Gegenprüfung nicht stand, und die Begründung ist
lehrreich:

§66 ist das spezifikationseigene Musterbeispiel. Dort erzeugt **ein einzelner** falscher
Versuch (`508` als `58`) die Kette Rohbeobachtung → Fehlercode → `DIRECT_NEGATIVE ZO06`,
und erst nach Replikation eine Hypothese. Die Spezifikation schreibt also selbst aus einem
einzelnen Fehler eine negativ gerichtete Evidenzzeile. §14 verbietet die **Hypothese**,
nicht die Evidenzzeile — und eine Hypothese entsteht hier nachweislich nie: es gibt keinen
leitideenübergreifenden Detektor. Der Verdacht las eine Ebene-2-Zeile als Ebene-3-Aussage,
also genau die Vermischung, vor der §66 warnt.

## Dritte Prüfrunde — die Analyseoberfläche

Der Implementierungsauftrag für die UI ist fachlich verbindlich und beginnt mit dem Satz,
der alles Weitere bestimmt: „Treffe **keine eigenen pädagogischen, diagnostischen oder
psychometrischen Entscheidungen**." Er verbietet ausdrücklich `if correct: level += 1` und
`if error == TEN_TRANSITION: competency = PLACE_VALUE_DEFICIT` im Frontend.

Die Frage war deshalb nicht, wie die Oberfläche aussieht, sondern wo die Grenze verläuft.
Sie verläuft an der Datenkante: alles, was eine fachliche Regel braucht, entsteht im
Backend und wird als fertiger Wert geliefert. Die vier Entscheidungen darunter sind die
Stellen, an denen das nicht von selbst so war.

### D-35 — Eine Entscheidung je Zug, nicht zwei (§89, §120)

Die Debug-Ansicht zeigt `routing_decisions` — und machte damit sofort sichtbar, was drei
Testrunden nicht gefunden hatten: jeder Zug stand **doppelt** im Protokoll. `interactive.run()`
rief am Schleifenanfang `render_next()` auf, obwohl `submit()` die nächste Auswahl nach
§120 Schritt 7 bereits getroffen und protokolliert hatte. Ein Durchlauf mit 3 Aufgaben
erzeugte 6 Entscheidungen.

Das ist kein kosmetischer Fehler. §89 verlangt ein Protokoll, das beantwortet, „warum das
System diesen Pfad gewählt hat"; ein Protokoll, das zwei Entscheidungen behauptet, wo eine
getroffen wurde, beantwortet diese Frage falsch — und §36 misst Informationsgewinn pro
Entscheidung. Die Auswahl wird jetzt in `vorgemerkt` weitergereicht. Nur `:uebergehen`
verlangt eine neue Auswahl und schreibt deshalb eine neue Zeile: Übergehen ist selbst eine
Entscheidung, `:hilfe` und `:loesung` sind keine.

Der Befund ist zugleich das Argument für die Debug-Ansicht. Was der Auftrag unter
„Dateneffizienz" verlangt — sichtbar zu machen, welche Daten für eine Entscheidung benutzt
wurden und welche nicht — ist nicht nur eine Anforderung an die Anzeige. Es ist der
einzige Weg, auf dem dieser Fehler auffallen konnte.

### D-36 — Der konfigurierte Wert gewinnt gegen das Literal (§38)

`_resource_class_map()` ordnet jeden Kompetenzstatus einer der drei Gruppen des Auftrags
zu (Ressource / offener Bereich / noch nicht geprüft). Welcher Status als gezeigtes Können
gilt, sagt `park.enter_status` (§38) — geparkt wird aus gezeigtem Können heraus, nicht aus
Unwissen.

Im Dict-Literal stand der konfigurierte Schlüssel *vor* den festen Einträgen und wurde von
ihnen überschrieben. Solange `park.enter_status` auf `SECURE` zeigt, fällt das nicht auf;
zeigte es auf einen der genannten Werte, wäre die Konfiguration wirkungslos gewesen — und
die Oberfläche hätte eine Gruppierung angezeigt, die von der Engine abweicht. Die Zuweisung
steht jetzt zuletzt. Der Test setzt den Schlüssel absichtlich auf einen kollidierenden Wert.

### D-37 — Die Oberfläche liest schreibgeschützt (§89)

Naheliegend wäre gewesen, die „nächste diagnostisch sinnvolle Aufgabe" beim Seitenaufruf
über `routing.next_task()` zu berechnen. Das wäre falsch: jeder Aufruf schriebe eine Zeile
nach §89, und das Protokoll behauptete Diagnostik, die nie stattgefunden hat — ein
Ansehen ist keine Entscheidung.

Die Oberfläche liest stattdessen die zuletzt protokollierte Entscheidung und markiert sie
als `is_pending`, solange ihre Aufgabe unbearbeitet ist. Die Verbindung wird zusätzlich
mit `mode=ro` geöffnet. Das ist keine Vorsichtsmaßnahme gegen Angriffe, sondern gegen die
eigene Bequemlichkeit: es macht den Fehler unmöglich statt unwahrscheinlich.

### D-38 — Kein Entwicklungsmodus, keine Mock-Daten

Der Auftrag sieht Mock-Daten vor, „falls noch keine echten Endpunkte existieren", und
schränkt sofort ein: „Erfinde keine fachlichen Backend-Regeln für die Mock-Daten." Die
Endpunkte existieren. Erfundene Daten hätten also nichts abgesichert und alles gefährdet:
jeder Mock-Wert ist eine Behauptung darüber, was das Backend liefern *würde*, und genau
diese Behauptungen sind fachliche Festlegungen.

Die Datenzugriffsschicht (`ui/data.js`) bleibt trotzdem die einzige Stelle mit `fetch()` —
ein Test hält das fest. Der Nutzen liegt nicht im Austausch gegen Mocks, sondern darin,
dass beim Anschluss an eine andere Quelle genau eine Datei zu ändern ist.

**Wo die Grenze im Einzelnen verläuft.** Die Oberfläche zeigt nichts an, wofür sie eine
Regel bräuchte. Sechs Werte, die das Frontend naheliegenderweise selbst gebildet hätte,
liefert deshalb `api.py` — jeder aus einer bestehenden Backend-Regel, keiner neu erfunden:

| Wert | Woher er stammt | Was das Frontend sonst entscheiden müsste |
|---|---|---|
| `resource_class` | `park.enter_status` (§38) | welcher Status gezeigtes Können ist |
| `reproduced` | `mastery.failure_replication_required` (§30) | ab wann ein Fehler ein Muster ist |
| `is_scored` | `SCORED_EVIDENCE_TYPES` (§28) | welche Evidenz den Status bewegt |
| `hypothesis_test.state` | `falsifying_task` (§115) | ob eine Hypothese prüfbar ist |
| `missing_evidence` | `falsifying_task` + Versuchsliste | was einer Hypothese fehlt |
| `next_question` | Protokoll und Hypothesen, **getrennt** | welche Quelle vorgeht — also Routing |

Die letzte Zeile ist die wichtigste: beide Quellen stehen nebeneinander und werden nicht
zu einer Empfehlung verrechnet. Eine Rangfolge zu bilden wäre Routinglogik, und die gehört
weder ins Frontend noch in den Vertrag zur Oberfläche.

Alle deutschen Beschriftungen kommen aus `vocabularies` und `vocabulary_terms`. Die
Oberfläche bringt keine Übersetzungstabelle für Fachbegriffe mit — eine eigene Übersetzung
wäre eine fachliche Festlegung außerhalb des Contents (§108). `tests/test_api.py` liest die
zu prüfenden Spalten aus den Fremdschlüsseln des Schemas und kontrolliert jeden Wert, der
in der Datenbank steht, gegen den ausgelieferten Katalog.

### Was die Oberfläche bewusst nicht zeigt

Kein Gesamtwert, keine Prozentwerte, keine Klassenstufenäquivalente (§117) — ein Test
durchsucht das ausgelieferte Profil nach Feldern, die danach aussehen. Farbe ist nirgends
die einzige Information: jeder Status trägt zusätzlich ein Zeichen und den ausgeschriebenen
Begriff, und ein Test prüft gegen die Vokabulare, dass kein Status ohne Zeichen bleibt.
`UNKNOWN` steht als eigene Gruppe neben den anderen und nicht als Rest — es ist ein
gültiger Zustand und kein Defizit.

## Vierte Prüfrunde — was die Oberfläche verschwiegen hat

Die dritte Runde hat geprüft, ob die Oberfläche etwas Falsches *behauptet*. Diese Runde
prüft das Gegenstück: ob sie etwas Richtiges *verschweigt*. Beides verletzt dieselbe
Grundregel — eine Ansicht, die die Rohbeobachtung nicht zeigt, zwingt zum Vertrauen in die
Verdichtung, und Vertrauen ist das, was die sechs Ebenen gerade vermeiden sollen.

### D-39 — Die konkrete Abweichung wird immer gezeigt

`ErrorObservation.detail` enthält das Paar, um das es geht: `{"rule": "EXACT_NUMERIC",
"expected": {"value": 60}, "given": 6}`. Die Oberfläche hat es hinter einer Bedingung
versteckt — sichtbar nur, wenn `is_observation_only` falsch war. In der Datenbank ist
`is_observation_only` bei **allen sechzehn Fehlercodes** gesetzt, und **alle dreißig**
Fehlerbeobachtungen tragen ein `detail`. Die Bedingung war also nicht selten wahr, sondern
nie: die tatsächliche Antwort des Kindes erschien an keiner Stelle der Oberfläche.

Der Zusammenhang ist der eigentliche Fehler. `is_observation_only` sagt, ob ein Code in die
**Wertung** eingeht; `detail` sagt, was **beobachtet** wurde. Das eine an das andere zu
koppeln hieß: weil dieser Fehler den Status nicht bewegt, darf auch niemand sehen, was das
Kind geschrieben hat. Gerade bei ungewerteten Codes ist die Rohbeobachtung das Einzige, was
bleibt.

Abweichung und Wertungsvermerk stehen jetzt in zwei Spalten. Beide Zustände von
`is_observation_only` sind beschriftet („nur Beobachtung, keine Wertung" /  „geht in die
Wertung ein") — vorher war das Fehlen des Vermerks die Information, und ein Fehlen ist für
niemanden lesbar.

Ein Fehlercode allein ist nach §66 nicht interpretierbar: `ERR_PLACE_VALUE` benennt das
Was, nicht das Warum. Wer nur den Code sieht, ergänzt die Ursache selbst — und die
Abkürzung leistet dann genau die Deutung, die der Auftrag verbietet. „erwartet 60,
gegeben 6" leistet sie nicht.

### D-40 — Der Rückweg von der Verdichtung zur Beobachtung

Ein Fehlermuster ist eine Zusammenfassung. `api.py` liefert zu jedem Muster die Liste der
Versuche, aus denen es entstanden ist (`muster.attempts`) — die Oberfläche hat sie nicht
benutzt. Es gab einen Weg vom Muster zu den *Aufgaben* und einen zu den *Hypothesen*, aber
keinen zurück zu den sechs Zeilen, die das Muster behaupten.

Jedes Muster trägt jetzt einen Knopf „*n* Einzelbeobachtungen unten zeigen", der Fehlercode
und Knoten als Filter setzt; die Aufgabenkennung jeder Beobachtung führt in den
Aufgabenverlauf. Damit ist die Forderung „Fehler müssen filter- und anklickbar sein" in
beide Richtungen erfüllt und nicht nur nach unten.

### D-41 — Die Debug-Ansicht deutet ihre eigene Zahl nicht

Unter „Nicht herangezogen" stand der Satz: *„Eine Entscheidung, die alles benutzt, erklärt
nichts."* Er war die einzige Stelle, an der die Oberfläche eine eigene fachliche Behauptung
aufstellte — und er überdehnte die Zahl, auf die er sich stützte.

`routing._evidence_used()` liefert die fünf jüngsten Evidenzzeilen des gewählten Knotens.
Die Menge „nicht herangezogen" ist damit konstruktionsbedingt fast alles; sie entsteht aus
einer Abfragegrenze, nicht aus einer Relevanzprüfung. Ob ein Eintrag *nicht relevant* oder
bloß *nicht nachgeschlagen* war, ist aus dem Protokoll nicht zu erkennen.

Der Auftrag verlangt, sichtbar zu machen, dass nicht alle vorhandenen Daten in jede
Entscheidung eingehen. Das tut die Ansicht weiterhin — „5 von 26" steht da, und dazu die
aus den Daten ablesbare Tatsache, zu welchem Knoten die fünf gehören. Sie sagt jetzt nur
noch, was das Protokoll hergibt: *welche* Einträge eingegangen sind, nicht *warum* die
übrigen fehlen. Die Bewertung dieser Zahl ist eine fachliche Aussage und steht dem
Frontend nicht zu.

## Fünfte Prüfrunde — die Restliste

Nach den vier blockierenden Punkten blieb eine Liste kleinerer Befunde. Sie sind hier
zusammengefasst, weil sie ein gemeinsames Muster haben: an jeder dieser Stellen hat die
Oberfläche etwas selbst gemacht, was ihr geliefert wurde, oder etwas behauptet, was sie
nicht wusste.

### D-42 — Ein Filterwert, den es nicht gibt, wird benannt

Die zweite Hälfte des Befundes zum Schülerwechsel: das Adressfragment kann eine Kennung
tragen, die im Profil des angezeigten Kindes nicht vorkommt — ein Lesezeichen, ein
geteilter Verweis. Ohne passende Option wählt der Browser die erste, also „alle". Das
Bedienelement behauptet dann, es sei nicht gefiltert, während die Ansicht darunter leer
bleibt.

`dom.js` liefert dafür `optionen()`: ein fremder Wert bekommt eine eigene Option mit dem
Zusatz „für dieses Kind nicht vorhanden". Alle fünf Filterfelder benutzen sie; die
Leitidee-Auswahl der Kompetenzkarte hat dieselbe Vorsorge.

### D-43 — Das gelieferte Objekt statt der eigenen Herleitung

`RepresentationEvidence` wurde vom Backend geliefert und in der Oberfläche genau einmal
gelesen: als Zahl neben dem Navigationspunkt. Die Tabelle „Darstellungsevidenz (EIS)"
baute sich stattdessen aus `competency_states[].facets` zusammen — inhaltlich dasselbe,
aber aus einer zweiten Quelle. Die Zahl zählte also ein anderes Objekt, als die Ansicht
zeigte.

Dass die EIS-Sicht genau die Facetten der Art `REPRESENTATION_MODE` sind, ist eine
fachliche Festlegung. Sie steht jetzt einmal in `api.py`; die Ansicht liest das Ergebnis.
`representation_evidence()` trägt dafür `status_label` und `resource_class` mit, aus
derselben Quelle wie `competency_states`.

### D-44 — Eine Bedingung, dreimal nachgebaut und zweimal falsch

Ob eine Hypothese *gerade geprüft wird*, hängt an zwei Dingen: die Kontrollaufgabe ist
offen **und** der Status ist noch einer der aktiven. Eine verworfene Hypothese kann eine
unbearbeitete Aufgabe stehen lassen.

`api.py` kannte beide Hälften. Die Oberfläche prüfte an drei Stellen nur die erste. Die
Bedingung steht jetzt als `hypothesis_test.is_active` im Vertrag, `_attach_next_question()`
benutzt dieselbe Zeile, und zwei Tests halten fest, dass beide Wege dieselbe Menge
ergeben. Ein Vergleich auf `"PLANNED"` im Frontend lässt die Testreihe jetzt scheitern.

### D-45 — Zahlen ohne Skala, Ränge ohne Bedeutung

`Konsistenz 0.3333` und `Stärke 0.4` standen als nackte Zahlen in der Ansicht. Einheitenlos
und ohne Bereich liest sich das wie ein Anteil — genau die Lesart, die §117 verbietet.
Beide Werte bleiben stehen, weil die Engine sie liefert, tragen jetzt aber ihren
Wertebereich und den Namen der Formel, unter dem sie in der Debug-Ansicht nachzulesen sind.

„Priorität im Routing" hieß eine Zahl, die ein Rang in der Warteschlange der Prüfungen ist
und nichts darüber sagt, wie wahrscheinlich eine Hypothese zutrifft. Sie heißt jetzt
„Rang in der Prüfwarteschlange".

### D-46 — Die Legende beschreibt den Graphen, nicht den Katalog

Die Kantenlegende zählte sechs Relationsarten fest auf, darunter
`CROSS_DOMAIN_RELATION`. In der Voreinstellung ist davon keine einzige gezeichnet: alle
zehn verbinden L1-Knoten mit den Wurzeln von L2 bis L5, und der Graph behält nur Kanten
mit zwei sichtbaren Enden. Eine Legende, die Striche erklärt, die es nicht gibt, behauptet
Struktur. Sie führt jetzt die gezeichneten Arten und benennt die ausgeblendeten als
ausgeblendet.

Im selben Zug: die fünf beidseitigen Relationen waren als einseitige Pfeile gezeichnet —
eine falsche Richtungsbehauptung —, und `notes` stand in allen 85 Relationen, ohne je
angezeigt zu werden. Beides ist behoben.

### D-47 — Was sonst noch stillschweigend entschieden wurde

- Die **Variationsdimensionen aus §72** standen als englische Rohschlüssel in der
  Detailansicht, und nur die belegten. Gezeigt werden jetzt alle fünf mit Zeichen und
  Wort: welche Bedingung *nicht* variiert wurde, ist die interessantere Angabe — sie sagt,
  worüber die bisherige Evidenz nichts aussagt.
- Der **Seitenkopf** trug „Leitidee 1 · Zahl und Operation" fest verdrahtet — derselbe
  Katalogwert, den die Oberfläche sonst nirgends selbst behauptet. Er kommt jetzt aus dem
  Katalog.
- Die **kompakte Übersicht** im Aufgabenverlauf ignorierte den Filter darüber: oben „6 von
  8 Versuchen", darunter kommentarlos acht Zeilen. Sie folgt jetzt derselben Auswahl.
- **Hypothese und Evidenz** sind im Backend nicht direkt verbunden: `supporting_evidence`
  führt Versuchskennungen. Die Hypothesenansicht sagt das jetzt und führt über den
  Fremdschlüssel `source_attempt` zu den Evidenzzeilen derselben Beobachtung — mit dem
  ausdrücklichen Hinweis, dass daraus nicht folgt, dass sie die Hypothese stützen.
- Auf **Papier** blieben die Statusfarben weg (Browser drucken Hintergründe nicht) und die
  Ebenenlegende eingeklappt. Ein weitergereichter Ausdruck trug damit K, E, H, B, F und P
  unerklärt. Beides ist im Druckbereich geregelt.

### D-48 — Das Protokoll darf nicht mehr versprechen, als darin steht

Zwei Sätze in der Debug-Ansicht haben für etwas gebürgt, das die Daten nicht hergeben.

**„Jede Zeile ist eine tatsächlich getroffene Entscheidung."** In sieben von acht Profilen
ist das falsch: bis zur Korrektur aus D-35 hat ein Zug zwei Zeilen geschrieben, und die
bereits erzeugten Profile tragen sie weiterhin. Die Ansicht vergleicht jetzt jede Zeile mit
ihrer Vorgängerin über alle gelieferten Felder, kennzeichnet feldgleiche als solche und
nennt ihre Zahl. Der Vergleich ist ein Feldvergleich, keine Deutung — behauptet wird nur,
dass zwei Zeilen gleich aussehen.

**Die gerundeten Scores.** `toFixed(1)` machte aus 2.9375 und 2.8750 zweimal „2.9". In
dreizehn protokollierten Entscheidungen stand der Höchstwert danach mehrfach da — in
ausgerechnet der Ansicht, die erklären soll, warum eine Aufgabe gewählt wurde. Gerundet
wird jetzt erst bei vier Stellen, und ein Test lässt jede gröbere Rundung in einer Ansicht
scheitern.

Bleibt der Fall, in dem die Kandidaten wirklich gleichauf liegen: bei DEMO-LAUFEND stehen
fünf Aufgaben mit identischem Score nebeneinander. Warum eine davon gewann, ist aus dem
Protokoll nicht zu beantworten — `margin` wird berechnet und nicht gespeichert (offene
Frage F-29). Die Ansicht schreibt diesen Satz jetzt hin, statt die Frage offenzulassen.
