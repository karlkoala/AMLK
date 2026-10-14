# Kompetenzanalyse auf Windows — Anleitung

Diese Seite ist für die Person gedacht, die das Programm benutzen soll.

Es sind drei Schritte. Der erste enthält einen Handgriff, den man leicht
übersieht und der sich hinterher nur mühsam nachholen lässt — deshalb steht er
ganz vorn.

> **Wenn etwas nicht klappt:** `<Name>`, `<Mailadresse>`, `<Telefon>`.
> Lieber einmal zu früh fragen — kaputtmachen kann man hier nichts.

---

## Schritt 1 — Auspacken (der Handgriff vor dem Doppelklick)

Windows merkt sich bei jeder heruntergeladenen Datei, dass sie aus dem
Internet stammt, und behandelt sie danach misstrauisch. Diese Markierung
überträgt sich beim Auspacken auf **jede einzelne Datei** im Ordner. Sie
lässt sich aber **vorher an der ZIP-Datei in einem Zug** entfernen.

1. Die heruntergeladene ZIP-Datei im Ordner *Downloads* suchen
   (**nicht** doppelklicken).
2. Mit der **rechten Maustaste** anklicken → **Eigenschaften**.
3. Ganz unten im Fenster steht *Sicherheit: Die Datei stammt von einem
   anderen Computer …* Daneben ein Kästchen **Zulassen** — dieses ankreuzen.
4. **OK** klicken.
5. Jetzt die ZIP-Datei mit der rechten Maustaste anklicken → **Alle
   extrahieren…** → **Extrahieren**.

> **Wenn dort unten nichts von *Sicherheit* steht:** dann ist die Markierung
> gar nicht gesetzt. Alles gut, direkt zu Punkt 5.

Es entsteht ein Ordner, dessen Name meist auf **`-main`** endet. In ihm liegt
alles, was das Programm braucht. Der Name darf so bleiben.

### Wohin der Ordner gehört

Diesen Ordner in den **Benutzerordner** ziehen:

* **Windows-Taste + R** drücken, `%userprofile%` eintippen, **Enter**.
  Es öffnet sich der richtige Ordner. Den Programmordner dort hineinziehen.

> **Warum nicht auf den Desktop oder in *Dokumente*?** Beide werden auf vielen
> Windows-11-PCs automatisch mit **OneDrive** abgeglichen. Dann lägen die
> Daten der Kinder auf fremden Servern. Außerdem legt das Programm bei der
> Einrichtung mehrere tausend kleine Dateien an — OneDrive kommt damit
> schlecht zurecht und macht daraus gelegentlich leere Platzhalter, worauf das
> Programm nicht mehr startet.

> **Und nicht in `C:\Programme`.** Dort darf das Programm nichts anlegen.

Der Ordner soll dort auch liegen bleiben. Verschieben oder Umbenennen ist
nicht schlimm, kostet aber beim nächsten Start noch einmal eine halbe Minute
und eine Internetverbindung.

### Falls schon ausgepackt wurde

Dann ist nichts verloren. Es müssen nur zwei Dateien freigegeben werden — die
beiden Startsymbole, alles andere wird nie doppelgeklickt:

Rechtsklick auf **`START-WINDOWS`** → **Eigenschaften** → unten **Zulassen**
ankreuzen → **OK**. Dasselbe für **`SITZUNG-WINDOWS`**.

---

## Schritt 2 — Python installieren (einmalig, etwa 3 Minuten)

Das Programm braucht eine Grundlage namens **Python**. Windows bringt keine
mit.

1. <https://www.python.org/downloads/> im Browser öffnen
2. Die große gelbe Schaltfläche anklicken — **Download Python 3.x.x**
3. Die geladene Datei (Endung `.exe`) im Ordner *Downloads* doppelklicken
4. Im Installationsfenster auf **Install Now** klicken. Die vorhandenen Haken
   können bleiben, wie sie sind.
5. Windows fragt einmal nach, ob die Änderung zugelassen wird — mit **Ja**
   bestätigen.
6. Am Ende **Close** klicken.

Danach ist Python da. Man sieht davon nichts — es ist kein Programm, das man
öffnet, sondern etwas, das andere Programme benutzen.

> **Nicht aus dem Microsoft Store nehmen.** Die Fassung von dort trägt
> denselben Namen, darf aber vieles nicht, was hier gebraucht wird.

> **Falls das Fenster nach einem anderen Benutzernamen und Kennwort fragt:**
> dann verwaltet jemand anderes diesen PC. Diese Person muss Schritt 2
> übernehmen.

> **Woran man merkt, dass dieser Schritt noch fehlt:** Schritt 3 bricht ab und
> zeigt genau diese Anleitung noch einmal im Fenster an.

---

## Schritt 3 — Starten

Im Programmordner liegen vier Startsymbole. Zwei davon gehören hierher:

| Symbol | wofür |
|---|---|
| **`START-WINDOWS`** | die Auswertung ansehen |
| **`SITZUNG-WINDOWS`** | mit einem Kind arbeiten |

Windows blendet die Endung `.bat` meist aus; zu sehen ist dann nur der Name
mit einem Zahnrad davor.

Die beiden anderen heißen `START-MAC.command` und `SITZUNG-MAC.command`.
Sie sind für einen Mac und tun auf diesem PC nichts — ein Doppelklick
öffnet sie höchstens im Editor. Sie dürfen liegen bleiben.

**Doppelklicken.** Das ist alles.

> **Falls doch ein Fenster *„Datei öffnen – Sicherheitswarnung"* erscheint:**
> auf **Ausführen** klicken. Dann war der Handgriff aus Schritt 1 noch nicht
> gemacht — er lässt sich nachholen (siehe *Falls schon ausgepackt wurde*),
> sonst kommt diese Frage jedes Mal wieder.

---

## Was dann passiert

Ein schwarzes Fenster öffnet sich und schreibt mit, was es tut.

Beim **ersten Start** richtet es sich ein. Das dauert meist eine halbe Minute
und braucht einmalig Internet — bei langsamer Verbindung auch einige Minuten.
Beim Schritt *„Programm installieren"* laufen
Zeilen durch — das sieht technisch aus und ist genau richtig so. Bitte nicht
abbrechen und **nicht noch einmal doppelklicken**.

Danach baut es die Daten auf und spielt sieben Beispielprofile durch, damit
gleich etwas zu sehen ist. Dann öffnet sich der Browser.

**Es hat geklappt, wenn** im Browser oben **Kompetenzanalyse** steht und
rechts daneben ein Auswahlfeld **Schüler:in** mit Einträgen wie `SIM-A`
gefüllt ist. Steht dort dauerhaft nur *„Daten werden geladen …"*, ist etwas
schiefgegangen — dann bitte melden.

**Das schwarze Fenster muss offen bleiben.** Es *ist* das laufende Programm,
auch wenn der Browser sich gleich davorschiebt.

Jeder weitere Start dauert nur noch wenige Sekunden.

> **Warum im Fenster keine Umlaute stehen.** Dort steht *„laesst"* statt
> *„lässt"*. Das ist Absicht: die Schriftzeichen dieses Fensters sind älter
> als Umlaute im Computer, und *ä* käme dort als Zeichensalat an.

### Beenden

Im schwarzen Fenster **strg** und **C** zusammen drücken.

Danach wird zweimal nachgefragt. Beides bestätigen:

1. *„Zum Schliessen die Eingabetaste druecken"* → **Enter**
2. *„Batchvorgang abbrechen (J/N)?"* → **J** eintippen, **Enter**

Das Fenster schließt sich. Die zweite Frage stellt Windows selbst; sie klingt
schärfer, als sie ist.

Oder einfach oben rechts auf das **×** klicken. Das tut dasselbe, ohne zu
fragen.

Danach zeigt der Browser noch die zuletzt geladenen Zahlen, holt aber keine
neuen mehr. Beim nächsten Neuladen steht dort *„nicht erreichbar"*. Das ist
kein Fehler.

---

## Mit einem Kind arbeiten

Dafür **`SITZUNG-WINDOWS`** doppelklicken. Es fragt nach zwei Dingen:

**Die Kennung.** Ein Kürzel, kein Name — zum Beispiel `KIND-01` oder `A3`.
Eine bekannte Kennung setzt die Arbeit fort, eine neue beginnt neu.

Das Fenster zeigt anschließend noch einmal an, was es sich gemerkt hat
(*„Gespeichert wird unter der Kennung: …"*). Dort bitte kurz hinsehen: was
dort steht, steht später auch in den Daten.

> Der echte Name des Kindes darf hier nicht stehen. Das Programm kann das
> nicht prüfen — es sieht nur, was eingetippt wurde. Die Zuordnung von Kürzel
> zu Kind gehört auf ein Blatt Papier, nicht in dieses Programm.

**Die Klassenstufe.** Nur ein Bezugsrahmen, keine Erwartung. Leer lassen ist
erlaubt.

Danach laufen die Aufgaben im Fenster. Mit **strg** und **C** lässt sich
jederzeit aufhören; alles bis dahin bleibt gespeichert.

Was dabei herausgekommen ist, zeigt anschließend `START-WINDOWS` — dort oben
die Kennung auswählen.

> **Beides gleichzeitig ist erlaubt.** Die Auswertungsansicht darf offen
> bleiben, während nebenan mit einem Kind gearbeitet wird. Sie zeigt aber
> nicht von selbst, was gerade dazukommt — dafür im Browser die Seite neu
> laden (**F5**).

---

## Wenn etwas nicht stimmt

Die linke Spalte ist das, was im Fenster oder auf dem Bildschirm steht.

| Was zu sehen ist | Was zu tun ist |
|---|---|
| „Auf diesem PC fehlt Python" | Schritt 2 nachholen, dann erneut doppelklicken |
| „Das Python auf diesem PC ist zu alt" | Schritt 2 wiederholen; die Seite python.org bietet von selbst die neueste Fassung an |
| „Das SQLite dieses Python ist zu alt" | Dasselbe: Python von python.org neu installieren |
| „Dieses Startsymbol liegt nicht mehr in seinem Ordner" | Das Startsymbol zurück in den Programmordner legen. Es funktioniert nur dort. |
| „Der Ordner des Programms laesst sich nicht oeffnen" | Liegt der Ordner auf einem Netzlaufwerk oder einem USB-Stick? Dann in den Benutzerordner kopieren (Schritt 1). |
| „Die Arbeitsumgebung liess sich nicht anlegen" | Den Programmordner in den Benutzerordner ziehen (Schritt 1), dann erneut starten |
| „Die Installation ist fehlgeschlagen" | Internetverbindung prüfen. Nur dieser eine Schritt braucht sie. Im Schulnetz kann eine Sperre der Grund sein — dann bitte melden. |
| „Das Programm wird gerade in einem anderen Fenster gestartet" | Es läuft schon. Dieses Fenster schließen, das andere benutzen. |
| „Das Programm laeuft bereits in einem anderen Fenster" | Kein Fehler. Die Oberfläche wurde erneut geöffnet. |
| „Die Datenbank in diesem Ordner ist unvollstaendig" | Einmal den PC neu starten und es noch einmal versuchen. Hilft das nicht: **nichts löschen**, bitte melden — die erhobenen Daten sind noch da |
| „Die Datenbank liess sich nicht aufbauen" | Melden, und die Datei `einrichtung.log` aus dem Programmordner mitschicken |
| „Das Programm ist auf diesem PC noch nicht eingerichtet" | Einmal `START-WINDOWS` doppelklicken und warten, bis der Browser aufgeht. Danach geht es hier weiter. |
| „Die Datenbank fehlt noch" | Dasselbe: einmal `START-WINDOWS` doppelklicken. Es baut sie auf. |
| Ein Fenster „Datei öffnen – Sicherheitswarnung" | Auf **Ausführen** klicken. Dauerhaft loswerden: *Falls schon ausgepackt wurde* in Schritt 1. |
| Das Startsymbol öffnet sich als Text im Editor | Auf diesem PC ist die Zuordnung für solche Dateien verstellt. Bitte melden. |
| **Gar nichts passiert — kein Fenster, keine Meldung** | Steckt der Ordner noch in der ZIP-Datei? Von dort aus kann das Programm nicht arbeiten. Sonst: Schritt 1 ganz durchgehen. |
| Das Fenster geht auf und sofort wieder zu | Bitte melden — das soll nicht vorkommen; das Fenster wartet sonst immer auf die Eingabetaste. |
| Der Browser zeigt „nicht erreichbar" | Ist das schwarze Fenster noch offen? Adresse: `http://127.0.0.1:8765/` |
| **Eine Meldung, die hier nicht steht** | Ein Bild vom ganzen Fenster machen und mitschicken |

---

## Was das Programm mit dem PC macht

Es legt seine Arbeitsumgebung in seinem eigenen Ordner an und ändert keine
Einstellungen von Windows. Aus dem Internet lädt es nur beim ersten Start,
und nur die Bausteine, die es zum Laufen braucht.

Das Programm läuft **nur auf diesem PC**. Die Adresse `127.0.0.1` steht für
den eigenen Rechner — niemand im selben Netz kann die Oberfläche sehen.

Die Auswertungsansicht kann die Daten nur **lesen**, nicht verändern.
Hinsehen ändert also nichts an dem, was über ein Kind festgehalten wurde.

Gespeichert werden die Aufgaben, die Antworten und die daraus abgeleiteten
Einschätzungen — aber **kein Name**. Nur das Kürzel, das beim Start
eingetippt wurde.
