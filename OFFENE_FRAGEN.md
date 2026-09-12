# Offene fachliche Fragen

Nach §1 der Spezifikation:

> Fachliche Beziehungen, diagnostische Interpretationen, Schwierigkeitsgrade oder
> psychologische Schlussfolgerungen sollen nicht eigenständig ergänzt werden.
> Wenn eine fachliche Information fehlt: `UNDEFINED` setzen und fachliche Rückfrage stellen.

Version 1.0 dieses Repos hat 23 Punkte so behandelt. Der Auftraggeber hat entschieden, dass
der Implementierer sie selbst festlegt. **Zwanzig sind entschieden** und in
[ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md) begründet.

Eine anschließende Prüfung des autorisierten Inhalts hat 43 Befunde geliefert, davon acht
gravierend — ein Bündelungsitem, das durch Ziffernablesen lösbar war, ein ikonisches
Multiplikationsitem, das durch Abzählen lösbar war, und drei Items, deren Distraktor der
Zahlenwert der richtigen Rechnung war. Alle inhaltlichen Befunde sind abgearbeitet; drei
neue offene Punkte (F-25 bis F-27) sind daraus entstanden.

**Sieben Punkte bleiben offen**, weil eine Festlegung dort schlechter wäre als eine offene
Frage.

`python -m mathkomp validate` meldet die offenen Punkte weiterhin als `NOTICE` — nichts
davon ist im Content verdeckt.

---

## Offen

### F-02 — Literaturangaben für §5, §111 und §112

§111 nennt KMK, IQB, PIKAS/DZLM und Gelman & Gallistel als primäre Referenzen, aber ohne
Fundstellen — kein Jahr, keine URL, keine Seitenzahl. §5 nennt „Forschung zu
mathematischen Strategien und Aufgabenvariation" und „Forschung zu adaptivem Testen", §112
beruft sich auf Forschung zur Strategieauswahl und leitet daraus die Verbindlichkeit der
vier Merkmalsfelder ab — jeweils ohne Publikationsangabe.

Ergänzt wurden nur belastbare Angaben (Gelman & Gallistel 1978, KMK-Fassung 2022). Es
wurden **keine Fundstellen erfunden**; wo keine vorliegt, bleibt `url_or_doi` leer.

**Warum nicht entschieden.** §114 erlaubt `evidence_status = A` nur mit amtlicher oder
empirischer Quelle, und eine Prüfregel setzt das durch. Mit einer erfundenen Quelle wäre
jede Relation formal absicherbar und die Unterscheidung zwischen belegt und plausibel
wertlos. Solange F-02 offen ist, trägt keine der 85 Kanten mehr als `C`.

**Benötigt.** Fundstellen für die vier primären Referenzen und eine Publikationsangabe für
§112.

### F-16 — Zuordnung der Items zu den Unterknoten aus §10

§42–57 ordnet die Items über die Kapitelüberschrift der Gruppenebene zu („50. Stellenwert
– ZO06"), nicht den neun Unterknoten `ZO06.1` bis `ZO06.9`. Deshalb haben **33 der 50
MVP-Knoten kein eigenes Item**, darunter alle Unterknoten von ZO02, ZO04, ZO05 und ZO06.

**Warum nicht entschieden.** Eine eigenständige Zuordnung wäre eine fachdidaktische
Entscheidung mit direkter Folge für jede Statusaussage — sie würde festlegen, welche
Kompetenz ein Item belegt. Und sie ist nicht nötig: das Zielbild in §118 arbeitet mit
Facetten („concept", „symbolic", „iconic", „derived strategy"), nicht mit Unterknoten, und
genau diese Facetten liefert `student_competency_facets` (Entscheidung D-04).

**Benötigt.** Entweder eine Zuordnung der Items zu Unterknoten, oder die Bestätigung, dass
die Unterknoten Strukturknoten ohne eigene Evidenz bleiben.

### F-24 — Neun Knotenpaare sind nicht trennscharf beschreibbar

Beim Verfassen der Kompetenzbeschreibungen (D-13) und bei der anschließenden Prüfung
ließen sich neun Fälle aus §10 nicht so beschreiben, dass ein Item eindeutig einem Knoten
zuzuordnen wäre:

| Paar | Problem |
|---|---|
| `ZO16 Kopfrechnen` / `ZO17 halbschriftliches Rechnen` | Der Unterschied liegt im Lösungsweg und dessen Notation, nicht in der Aufgabe. §76 sieht für das MVP kein Verfahren vor, den Lösungsweg zu beobachten. |
| `ZO18 Rechnen in Kontexten` / `ZO19 Transfer / Problemlösen` | Das unterscheidende Merkmal — dass der Lösungsweg nicht unmittelbar aus dem Kontext folgt — ist am Item nicht ablesbar. |
| `ZO02.1 kardinales Zahlverständnis` / `ZO02.4 Menge → Zahl` | §10 führt beide, nennt aber kein Merkmal, das sie trennt. |
| `ZO04.1 größer / kleiner` / `ZO04.5 Zahlen vergleichen` | Beide Bezeichnungen benennen dieselbe Leistung. |
| `ZO05.1 Zahlzerlegung` / `ZO05.3 Ergänzen` | Die Items `8 = 5 + __` und `37 + __ = 50` haben dieselbe Form. |
| `ZP02 stabile Reihenfolge` / `ZO02.5 Zahlwortreihe` | Kein Geschwisterpaar, aber derselbe Fall: die Items aus §43 belegen beide gleichermaßen. |
| `ZP03 Kardinalprinzip` / `ZO02.1 kardinales Zahlverständnis` | Derselbe Fall. Die zunächst gesetzte Voraussetzungskante REL_021 wurde entfernt: eine Kante zwischen zwei Namen für denselben Gegenstand ist nach §115 nicht widerlegbar. |
| `ZO12 Aufgabenbeziehungen` / `ZO13 Rechengesetze` / `ZO15 flexible Strategiewahl` | `49+36 → 50+35` erfüllt alle drei Definitionen wörtlich, `17·6 → 10·6+7·6` mindestens zwei. Ein beobachtbares trennendes Merkmal fehlt. |
| `ZO06.9 größere Zahlenräume` | Der Knoten nennt keine Grenze. Entweder gehört jedes dreistellige Stellenwertitem hierher — dann ist er gegen ZO06.3 bis ZO06.6 nicht abgrenzbar — oder er beginnt erst bei vier Stellen und hat in V1 kein Item. |

**Warum nicht entschieden.** Das ist ein Modellierungsproblem des Kompetenzgraphen aus §10,
kein Beschreibungsproblem. Eine Beschreibung, die eine Trennung behauptet, die am Item
nicht ablesbar ist, würde das Problem verdecken — und sie würde die Statusberechnung
beschädigen, sobald ein Item einem der beiden Knoten zugeordnet wird.

**Benötigt.** Entweder ein trennendes Merkmal je Paar, oder die Zusammenlegung der Knoten.

### F-25 — §71 widerspricht der operandensymmetrischen Regel

§71 führt vier Additionsitems vor: 49+36 und 48+37 gelingen, 37+28 und 46+27 nicht. Die
erfolgreiche Seite etikettiert §71 mit `NEAR_ROUND_NUMBER` und `COMPENSATION_AVAILABLE`,
die erfolglose mit `NO_NEAR_ROUND_ANCHOR`.

Arithmetisch ist das für 37+28 nicht haltbar: 28 liegt 2 von 30 entfernt, es gibt also
einen runden Anker. Jede operandensymmetrische Definition von `NEAR_ROUND_NUMBER` vergibt
das Merkmal an 37+28.

Die erste Fassung dieses Repos hatte die Regel so gebaut, dass §71 herauskommt — nur der
**erste** Operand zählte bei zweistelligen Aufgaben. Die Kritik hat das zu Recht als
Regeldesign statt Fachlichkeit beanstandet: für die Asymmetrie gab es keinen Grund außer
dem gewünschten Ergebnis. Die Regel ist jetzt symmetrisch (D-19), 37+28 trägt das Merkmal,
und der Kontrast der Contrast Families läuft über `COMPENSATION` — das Merkmal, das §71
für die erfolgreiche Seite ebenfalls nennt und das die vier Items so trennt, wie §71 sie
gruppiert.

**Warum nicht entschieden.** Ob §71 das Merkmal `NEAR_ROUND_NUMBER` in einem engeren Sinn
meint als „irgendein Operand liegt nahe an einer runden Zahl", ist eine fachliche Frage.
Sie zu entscheiden hieße, entweder §71 zu widersprechen oder eine unbegründete
Regelasymmetrie festzuschreiben.

**Benötigt.** Entweder die Bestätigung, dass 37+28 das Merkmal trägt und §71 an dieser
Stelle unpräzise ist, oder eine engere Definition — etwa: nur der Operand, der beim
Ausgleich aufgerundet wird, darf den Anker liefern.

### F-26 — Darbietungsreihenfolge ist mit der Darstellung konfundiert

In beiden reparierten Ketten (§69, §70) wird ausnahmslos zuerst symbolisch, dann ikonisch
vorgelegt. Ein ikonischer Vorteil ist damit nicht von einem Zweitkontakteffekt zu trennen:
das Kind hat die Zahlen bereits gesehen.

Die Reihenfolge steht in den Versuchsdaten und ist auswertbar, aber die Engine
berücksichtigt sie nicht. `hypothesis.require_same_difficulty_for_dependency` hält Stufe,
Antwortformat und Frageform konstant — die Reihenfolge nicht.

**Warum nicht entschieden.** Eine Umkehrung erfordert ein drittes Zahlenpaar je Familie
und damit weitere Items; und ob der Zweitkontakteffekt bei diesen Aufgaben groß genug ist,
um das zu rechtfertigen, ist eine empirische Frage (§127).

**Benötigt.** Entweder ein drittes Zahlenpaar je Darstellungsfamilie mit umgekehrter
Reihenfolge, oder die Entscheidung, den Effekt in V1 in Kauf zu nehmen und in der
Lehrkraftansicht zu benennen.

### F-27 — Erfolg innerhalb einer Förderkette zählt wie Erfolg ohne Hilfe

Die Förderketten aus §92 und §93 führen zum Schluss auf das ursprüngliche Item zurück
(§91 „ORIGINAL REQUIREMENT"). Ein Erfolg dort wird derzeit wie jeder andere Erfolg
verbucht, obwohl er unmittelbar auf eine gestützte Sequenz folgt.

§33 gibt das Werkzeug vor: eine Leistung unter Unterstützung ist eine andere Beobachtung.
Die Engine hat es auch — `support_used` erzeugt `SUPPORT_EVIDENCE` und ein reduziertes
Gewicht. Es wird für Förderketten nur nicht automatisch gesetzt; die Oberfläche müsste es
mitgeben.

**Benötigt.** Entweder die Festlegung, dass ein über `reason = SUPPORT_ROUTE` erreichtes
Item automatisch als gestützt gilt, oder eine eigene Kennzeichnung für den
Förderkontext.

---

## Entschieden

Alle Begründungen in [ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md).

| Punkt | Was fehlte | Entscheidung |
|---|---|---|
| F-01 | Kompetenzbeschreibungen (41 Knoten) | D-13 — alle 54 beschrieben, mit Abgrenzung und Beobachtbarkeit |
| F-03 | Skala für `language_demand` | D-15 — vierstufig, an der Formulierung ablesbar |
| F-04 | Klassenstufenreferenzen | D-21 — aus Zahlenraum und Operation abgeleitet |
| F-05 | Kantenliste des Kompetenzgraphen | D-12 — 77 Kanten ergänzt, 18 begründet abgelehnt |
| F-06 | Vier undefinierte Fehlercodes | D-14 — definiert, `ERR_REPRESENTATION` nur per Facettenvergleich |
| F-07 | Vier unbezifferte Schwellen | D-06 — beziffert, plus vier Score-Summanden |
| F-08 | Berechnungsvorschriften für Evidenz | D-05 — Formeln, Asymmetrie, stufenweiser Status |
| F-09 | Zeitgrenzen | D-07 — 90/30 Tage, plus Wiedervorlage gegen den Parkzirkel |
| F-10 | ID-Kollision `ZO07-D3-S-A` | D-01 — §51 behält die ID, §24-Item wird `ZO07-D3-S-E` |
| F-11 | `48+37` ohne ID und Metadaten | D-02 — `ZO07-D3-S-F` |
| F-12 | Merkmalsregeln | D-19 — drei operationale Regeln, `CROSSES_THOUSAND` ergänzt |
| F-13 | Familien- und Parallelitem-Zuordnung | D-11 — vier Familien repariert, zwei ergänzt |
| F-14 | Anordnung bei vier Zählitems | D-17 — `UNORDERED` |
| F-15 | Darstellungsmodus der ZP05-Items | D-16 — nach Aufgabeninhalt |
| F-17 | 13 Auswahlaufgaben ohne Distraktoren | D-09 — autorisiert, jeder mit Fehlvorstellung |
| F-18 | Antwortmenge für `ZO05-D4-S-A` | D-10 — Liste akzeptierter Zerlegungen |
| F-19 | Prozesskompetenzen nicht zugeordnet | D-19 — regelbasiert vergeben |
| F-20 | Dieselbe Aufgabe mit zwei Stufen | D-03 — zusammengelegt, Sekundärkompetenz eingetreten |
| F-21 | Darstellungsvergleiche konfundiert | D-11 — gleichstufige Paare ergänzt, Regel erzwingt es |
| F-22 | Förderitems aus §92/§93 fehlten | D-11 — fünf Items ergänzt |
| F-23 | `task_routes` ohne Kontextfeld | D-08 — `requires_status`, `requires_hypothesis` |

### Wie die Entscheidungen abgesichert sind

Keine ist nur dokumentiert. Für jede gibt es einen Mechanismus, der ihre Verletzung
bemerkt:

- **19 Prüfregeln** in `validate.py`, jede mit Abschnittsverweis. Zwei ehemalige Hinweise
  sind zu harten Regeln erhoben, seit die zugehörige Lücke geschlossen ist: ein Item ohne
  Distraktoren und eine Route, die neben der Darstellung auch Stufe, Antwortformat oder
  Frageform wechselt, brechen jetzt mit `ERROR` ab. Die Frageform-Prüfung hat beim
  Einschalten drei Konfundierungen gefunden, darunter eine gerade erst ergänzte Route —
  die Regel arbeitet also.
- **156 Tests**, darunter die sechs Testfälle aus §98–§103, alle 20 Kriterien der
  Definition of Done aus §123 und die Architekturregeln der Analyseoberfläche: dass genau
  eine Datei Daten lädt, dass kein Kompetenzstatus und kein Schwellenwert im Frontend
  ausgewertet wird und dass kein Zustand allein an der Farbe zu erkennen ist.
- **Jeder Schwellwert in `system_config`**, keiner im Code. Ein Test scannt die Quellen
  nach Literalen.
- **Jede Festlegung als `CONFIGURABLE` markiert**, nicht als gesichert. §41 verlangt genau
  diese Unterscheidung.

### F-28 — §14 zweite Hälfte: wann aktivieren mehrere Beobachtungen eine Hypothese?

§14 verbietet nicht nur den Kurzschluss („ein Fehler bedeutet nicht: räumliches
Vorstellungsvermögen schwach"), sondern stellt auch etwas in Aussicht:

> Erst mehrere unabhängige Beobachtungen können eine entsprechende Hypothese aktivieren.

Die erste Hälfte ist erfüllt: `CROSS_DOMAIN_EVIDENCE` steht nicht in den gewerteten
Evidenztypen, verändert also keinen Status, und es existiert kein leitideenübergreifender
Hypothesendetektor. Die zweite Hälfte ist **nicht umgesetzt**. Der Schlüssel
`hypothesis.cross_domain_min_observations` steht in der Konfiguration und hat keinen
Leser.

**Warum nicht entschieden.** Die fehlende Zahl ist das kleinere Problem. Zu entscheiden
wäre, *was* die Hypothese behauptet und *woran* sie scheitern kann. „Räumliche
Verarbeitung ist beeinträchtigt" ist nach §32 und §87 keine zulässige Aussage, und §115
verlangt für jede Hypothese eine Aufgabe, die sie widerlegt — für einen
leitideenübergreifenden Befund im MVP gibt es keine, weil L2 bis L5 nach §7 keine
inhaltlichen Knoten und damit keine Items haben. Eine erfundene Formulierung wäre genau
die psychologische Schlussfolgerung, die §1 dem Implementierer verbietet.

**Benötigt.** Eine zulässige Formulierung der leitideenübergreifenden Hypothese, die
Bedingungen beschreibt statt Eigenschaften, und eine Angabe, welche Beobachtung sie
widerlegen würde. Ohne beides bleibt der Schlüssel ohne Leser — sichtbar, statt still
umgesetzt zu sein.

## Beim Bau der Oberfläche sichtbar geworden

Die Analyseoberfläche zeigt an, was das Backend liefert. Beim Anschließen ist aufgefallen,
wo etwas geliefert wird, das keine Entsprechung hat — und wo etwas fehlt, das der
Implementierungsauftrag zur Oberfläche verlangt. Keiner dieser Punkte ist im Zuge der
Oberfläche entschieden worden: es sind fachliche Festlegungen, und §1 verbietet, sie
nebenbei zu treffen.

### F-29 — Die Begründung nach §88 wird gebaut und weggeworfen

`routing._explain()` setzt zu jeder Entscheidung eine ausformulierte Begründung im Format
von §88 zusammen — gewählte Aufgabe, Regel oder Routenbegründung, geprüfte Hypothese,
Abstand zum Zweitplatzierten, die stärksten Summanden. `_log()` schreibt sie nicht: die
Tabelle `routing_decisions` hat keine Spalte `explanation`. Dasselbe gilt für `margin`,
den Abstand zwischen Erst- und Zweitplatziertem, aus dem die Konfidenz entsteht — berechnet,
verwendet, nicht gespeichert.

Die Oberfläche zeigt deshalb die Summanden einzeln und den daraus entstandenen
Konfidenzwert, aber nicht den Satz, der beides zusammenfasst, und nicht den Abstand, auf
den sich der Konfidenzwert stützt.

**Zu entscheiden.** Ob §89 die formulierte Begründung als Teil des Protokolls verlangt oder
ob sie eine Anzeigeform ist, die bei Bedarf neu erzeugt wird. Das ist keine technische
Frage: eine gespeicherte Begründung ist ein Dokument über eine getroffene Entscheidung und
bleibt auch dann gültig, wenn sich die Regeln später ändern. Eine nachträglich erzeugte
beschreibt die heutige Regel, nicht die damalige. Wird die Spalte ergänzt, sind `margin`
und `explanation` zusammen zu ergänzen.

### F-30 — Was `evidence_used` bedeuten soll

`routing._evidence_used()` liefert die fünf jüngsten Evidenzzeilen des gewählten Knotens.
Weder die Fünf noch die Beschränkung auf einen Knoten steht in der Fachspezifikation;
beides ist beim Implementieren entstanden.

Das hat Folgen für die Debug-Ansicht, weil der Auftrag dort verlangt, sichtbar zu machen,
„welche Daten aktuell nicht relevant waren". Aus dem Protokoll ist das nicht zu erkennen:
die Menge der nicht aufgeführten Einträge entsteht aus einer Abfragegrenze und nicht aus
einer Relevanzprüfung. Die Oberfläche benennt deshalb nur, welche Einträge eingegangen
sind, und behauptet über die übrigen nichts (Entscheidung D-41).

**Zu entscheiden.** Ob `evidence_used` die *tatsächlich gelesenen* Zeilen bezeichnen soll —
dann gehören die Statusberechnungen aller betrachteten Kandidatenknoten dazu und die Liste
wird deutlich länger — oder die *ausschlaggebenden*. Im zweiten Fall braucht es eine Regel,
was ausschlaggebend heißt, und das ist eine fachliche Festlegung.

### F-31 — Zwei Angaben aus dem UI-Auftrag haben kein Feld

Der Implementierungsauftrag verlangt in der Detailansicht eines Kompetenzknotens den
**Anforderungsbereich** und in der Fehleranalyse die **Fehlerfamilie**. Beides existiert im
Datenmodell nicht.

- *Anforderungsbereich* (AB I–III der Bildungsstandards) ist in der Fachspezifikation nicht
  vergeben. Die Oberfläche zeigt stattdessen `INTERNAL_DIFFICULTY` (D1–D4) und benennt das
  als solches. Die beiden sind nicht dasselbe: D1–D4 beschreibt die Aufgabe, AB I–III die
  verlangte geistige Tätigkeit.
- *Fehlerfamilie* wird derzeit aus dem Präfix des Fehlercodes abgelesen — `ERR_PLACE_VALUE`
  und `ERR_PLACE_VALUE_SWAP` gehören erkennbar zusammen. Das ist eine Zeichenkettenregel,
  keine Taxonomie, und die Oberfläche schreibt das auch so hin.

**Zu entscheiden.** Ob AB I–III je Knoten zu vergeben ist — dann als Spalte in
`competencies`, nicht als Ableitung — und ob die Fehlercodes eine erklärte Gruppierung
erhalten. Eine im Frontend erfundene Taxonomie wäre nach dem Auftrag ausdrücklich verboten.

### F-32 — Die Testdaten kennen keine Widerlegung

§115 verlangt, dass jede Hypothese widerlegbar ist, und die Oberfläche zeigt für jede
Hypothese Belege dafür und dagegen nebeneinander. In der Datenbank stehen dreizehn
Hypothesen; **keine einzige** hat widersprechende Evidenz, keine hat den Status `REJECTED`
oder `WEAKENED` (neun `SUPPORTED`, vier `OPEN`). Alle dreizehn tragen eine
`falsifying_task`, aber keine ist je an ihr gescheitert.

Ebenso: alle sechzehn Fehlercodes sind `is_observation_only`, `current_floor` und
`current_ceiling` sind in nur acht von 28 Kompetenzzuständen gesetzt, und bei sieben von
acht Kindern endet der Durchlauf mit einem Abbruch ohne nächste Aufgabe. Die geforderten
Angaben „widersprechende Beobachtungen", „Anforderungsbereich" und „welche diagnostische
Frage ist gerade aktiv" sind damit nicht *falsch* dargestellt, sondern **nicht
überprüfbar**: niemand kann sehen, ob die Anzeige stimmt.

Das ist keine Eigenschaft der Engine, sondern der sechs Testfälle aus §98–§103: sie bilden
Verläufe ab, in denen sich die jeweilige Vermutung bestätigt. Die Gegenrichtung ist damit
im laufenden System nie durchlaufen worden — die Anzeige „0 dagegen" ist überall korrekt und
nirgends geprüft.

**Benötigt.** Ein Testfall, in dem eine aktivierte Hypothese an ihrer eigenen
Kontrollaufgabe scheitert, und eine Angabe, welcher Status daraus folgt (`WEAKENED` ab
wann, `REJECTED` ab wann). Die Schwellenwerte dafür sind, wie alle anderen, in
`system_config` zu hinterlegen und nicht im Code.

### Beiläufig behoben, nicht offen

Bis zur dritten Prüfrunde hat `interactive.run()` je Zug zwei Entscheidungszeilen
geschrieben — eine beim Ausliefern der Aufgabe, eine beim Auswerten. Der Fehler ist
behoben (Entscheidung D-35); die bereits erzeugten Profile tragen die Doppelungen
weiterhin, weil `simulate` sie nicht rückwirkend bereinigt. Wer ein sauberes Protokoll
braucht, erzeugt die Daten neu.
