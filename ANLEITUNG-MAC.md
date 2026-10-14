# Kompetenzanalyse auf dem Mac — Anleitung

Diese Seite ist für die Person gedacht, die das Programm benutzen soll.

Es sind drei Schritte. Der dritte sieht am unheimlichsten aus: der Mac fragt
dort einmal nach, ob er dieses Programm wirklich starten darf. Das ist normal
und unten genau beschrieben.

> **Wenn etwas nicht klappt:** `<Name>`, `<Mailadresse>`, `<Telefon>`.
> Lieber einmal zu früh fragen — kaputtmachen kann man hier nichts.

---

## Schritt 1 — Python installieren (einmalig, etwa 3 Minuten)

Das Programm braucht eine Grundlage namens **Python**. Ein Mac bringt zwar
eine mit, aber eine zu alte.

1. <https://www.python.org/downloads/> im Browser öffnen
2. Die große gelbe Schaltfläche anklicken — **Download Python 3.x.x**
3. Die geladene Datei (Endung `.pkg`) im Ordner *Downloads* doppelklicken
4. Im Installationsfenster jeweils auf **Fortfahren** und **Installieren** klicken
5. Der Mac fragt einmal nach dem Anmeldekennwort. Das ist normal und richtig.

Danach ist Python da. Man sieht davon nichts — es ist kein Programm, das man
öffnet, sondern etwas, das andere Programme benutzen.

> **Falls das Fenster nach einem anderen Benutzernamen fragt:** dann verwaltet
> jemand anderes diesen Mac. Diese Person muss Schritt 1 übernehmen.

> **Woran man merkt, dass dieser Schritt noch fehlt:** Schritt 3 bricht ab und
> zeigt genau diese Anleitung noch einmal an.

---

## Schritt 2 — Das Programm auspacken

1. Die erhaltene ZIP-Datei doppelklicken.
   Daneben entsteht ein Ordner gleichen Namens. Kommt die Datei von
   GitHub, endet sein Name meist auf **`-main`**. Der Name darf so
   bleiben.
2. Diesen Ordner in den **Benutzerordner** ziehen.
   Im Finder: Menü **Gehe zu** → **Benutzerordner**.

Der Ordner darf nicht in der ZIP-Datei bleiben — von dort aus kann das
Programm nicht arbeiten.

> **Warum nicht auf den Schreibtisch?** Der Schreibtisch wird auf vielen Macs
> automatisch mit der iCloud abgeglichen. Dann lägen die Daten der Kinder auf
> fremden Servern. Im Benutzerordner passiert das nicht. Außerdem fragt der
> Mac beim Schreibtisch noch einmal nach Zugriffsrechten — eine Rückfrage
> weniger ist eine Rückfrage weniger.

Der Ordner soll dort auch liegen bleiben. Verschieben oder Umbenennen ist
nicht schlimm, kostet aber beim nächsten Start noch einmal ein bis zwei
Minuten und eine Internetverbindung.

---

## Schritt 3 — Starten

Ganz oben im entpackten Ordner liegen diese zwei Startsymbole:

| Symbol | wofür |
|---|---|
| **`START-MAC.command`** | die Auswertung ansehen |
| **`SITZUNG-MAC.command`** | mit einem Kind arbeiten |

Kam der Ordner über GitHub, liegen daneben noch `START-WINDOWS.bat` und
`SITZUNG-WINDOWS.bat`. Die sind für einen Windows-PC und tun auf dem Mac
nichts. Sie dürfen liegen bleiben.

Beim allerersten Mal geht der Doppelklick **nicht** sofort. macOS legt auf
alles, was aus dem Internet kommt, zwei Sperren — und bei Startdateien dieser
Art meldet es das nicht, sondern tut einfach nichts. Kein Fenster, keine
Meldung. Wer darauf wartet, wartet vergeblich.

Beide Sperren werden **einmalig** gelöst, mit zweimal demselben Handgriff.
Abzutippen ist dabei nichts außer ein paar Buchstaben.

1. **cmd + Leertaste** drücken, `Terminal` tippen, **Enter**.
   Es geht ein Fenster mit Text auf. Das ist richtig so.
2. Das Fenster an den rechten Rand schieben, so dass links der Finder mit dem
   entpackten Ordner sichtbar bleibt.
3. Ins Terminalfenster klicken und tippen — **mit Leerzeichen am Ende**:
   `chmod +x `
4. Jetzt die beiden Dateien `START-MAC.command` und `SITZUNG-MAC.command` im
   Finder markieren (die zweite mit gedrückter **cmd**-Taste anklicken) und
   zusammen **ins Terminalfenster ziehen**. Ihre Orte setzen sich von selbst
   ein. **Enter** drücken.
5. Dasselbe noch einmal, diesmal mit diesem Anfang — wieder mit Leerzeichen
   am Ende: `xattr -dr com.apple.quarantine `
6. Und diesmal den **ganzen entpackten Ordner** ins Fenster ziehen. **Enter**.

Kommt nach dem Enter keine Antwort, hat es geklappt — hier ist Schweigen das
Erfolgszeichen.

> **Was die beiden Zeilen tun.** Die erste erlaubt, dass die Startdateien
> überhaupt startbar sind; das Recht dazu geht auf dem Transportweg oft
> verloren. Die zweite nimmt den Dateien die Markierung *aus dem Internet
> geladen*. Beides betrifft nur diesen einen Ordner. An den Einstellungen des
> Macs ändert sich nichts.

**Ab dann:** einfach doppelklicken. Für immer.

> **Falls das Terminal bei Schritt 4 oder 6 meckert** — etwa *No such file or
> directory*: dann ist beim Ziehen etwas danebengegangen. Fenster schließen,
> neu anfangen. Kaputt geht dabei nichts.

### Wenn es heute laufen muss und die Schritte oben nicht klappen

Es gibt einen Weg, der beide Sperren umgeht, ohne etwas zu reparieren: das
Programm nicht doppelklicken, sondern aus dem Terminal heraus starten.

Terminal öffnen wie oben, dann `bash ` tippen — **mit Leerzeichen** —, die
Datei `START-MAC.command` hineinziehen, **Enter**. Danach läuft alles wie
beschrieben.

Das repariert nichts, es startet nur. Beim nächsten Mal ist der Handgriff
wieder nötig — bis die Schritte 1 bis 6 einmal gemacht wurden.

---

## Was dann passiert

Ein Terminalfenster öffnet sich und schreibt mit, was es tut.

Beim **ersten Start** richtet es sich ein. Das dauert ein bis zwei Minuten und
braucht einmalig Internet. Beim Schritt *„Programm installieren"* laufen
Zeilen durch — das sieht technisch aus und ist genau richtig so. Bitte nicht
abbrechen und **nicht noch einmal doppelklicken**.

Danach baut es die Daten auf und spielt sieben Beispielprofile durch, damit
gleich etwas zu sehen ist. Dann öffnet sich der Browser.

**Es hat geklappt, wenn** im Browser oben **Kompetenzanalyse** steht und
rechts daneben ein Auswahlfeld **Schüler:in** mit Einträgen wie `SIM-A`
gefüllt ist. Steht dort dauerhaft nur *„Daten werden geladen …"*, ist etwas
schiefgegangen — dann bitte melden.

**Das Terminalfenster muss offen bleiben.** Es *ist* das laufende Programm,
auch wenn der Browser sich gleich davorschiebt.

Jeder weitere Start dauert nur noch wenige Sekunden.

### Beenden

Im Terminalfenster **ctrl** und **C** zusammen drücken.

Oder das Fenster schließen. Der Mac fragt dann einmal nach, ob die laufenden
Programme beendet werden sollen — mit **Beenden** bestätigen.

Danach zeigt der Browser noch die zuletzt geladenen Zahlen, holt aber keine
neuen mehr. Beim nächsten Neuladen steht dort *„nicht erreichbar"*. Das ist
kein Fehler.

---

## Mit einem Kind arbeiten

Dafür **`SITZUNG-MAC.command`** doppelklicken. Es fragt nach zwei Dingen:

**Die Kennung.** Ein Kürzel, kein Name — zum Beispiel `KIND-01` oder `A3`.
Eine bekannte Kennung setzt die Arbeit fort, eine neue beginnt neu.

> Der echte Name des Kindes darf hier nicht stehen. Das Programm kann das
> nicht prüfen — es sieht nur, was eingetippt wurde. Die Zuordnung von Kürzel
> zu Kind gehört auf ein Blatt Papier, nicht in dieses Programm.

**Die Klassenstufe.** Nur ein Bezugsrahmen, keine Erwartung. Leer lassen ist
erlaubt.

Danach laufen die Aufgaben im Fenster. Mit **ctrl** und **C** lässt sich
jederzeit aufhören; alles bis dahin bleibt gespeichert.

Was dabei herausgekommen ist, zeigt anschließend `START-MAC.command` — dort
oben die Kennung auswählen.

---

## Wenn etwas nicht stimmt

Die linke Spalte ist das, was im Fenster steht.

| Was zu sehen ist | Was zu tun ist |
|---|---|
| „Auf diesem Mac fehlt ein ausreichend neues Python" | Schritt 1 nachholen, dann erneut doppelklicken |
| „Das SQLite dieses Python ist zu alt" | Schritt 1 mit einer neueren Python-Version wiederholen |
| „Diese Startdatei liegt nicht mehr in ihrem Ordner" | Das Startsymbol zurück in den entpackten Ordner legen, ganz nach oben. Es funktioniert nur dort. |
| „Der Ordner dieses Startsymbols laesst sich nicht oeffnen" | Dasselbe — das Startsymbol liegt an einer Stelle, von der aus es seinen Ordner nicht findet. |
| „Die Arbeitsumgebung liess sich nicht anlegen" | Den entpackten Ordner in den Benutzerordner ziehen (Schritt 2), dann erneut starten |
| „Die Installation ist fehlgeschlagen" | Internetverbindung prüfen. Nur dieser eine Schritt braucht sie. |
| „Das Programm wird gerade in einem anderen Fenster gestartet" | Es läuft schon. Dieses Fenster schließen, das andere benutzen. |
| „Das Programm laeuft bereits in einem anderen Fenster" | Kein Fehler. Die Oberfläche wurde erneut geöffnet. |
| „Die Datenbank in diesem Ordner ist unvollstaendig" | Einmal den Mac neu starten und es noch einmal versuchen. Hilft das nicht: **nichts löschen**, bitte melden — die erhobenen Daten sind noch da |
| „Die Datenbank liess sich nicht aufbauen" | Melden, und die Datei `einrichtung.log` aus dem Ordner mitschicken |
| „Das Programm ist auf diesem Mac noch nicht eingerichtet" | Einmal `START-MAC.command` doppelklicken und warten, bis der Browser aufgeht. Danach geht es hier weiter. |
| „Die Datenbank fehlt noch" | Dasselbe: einmal `START-MAC.command` doppelklicken. Es baut sie auf. |
| Das Startsymbol öffnet sich als Text, oder der Mac meldet fehlende Zugriffsrechte | Schritt 3 noch nicht gemacht — oder die Datei kam beschädigt an. Bitte melden. |
| Der Browser zeigt „nicht erreichbar" | Ist das Terminalfenster noch offen? Adresse: `http://127.0.0.1:8765/` |
| **Eine Meldung, die hier nicht steht** | Ein Bild vom ganzen Fenster machen und mitschicken |

---

## Was das Programm mit dem Rechner macht

Es legt seine Arbeitsumgebung in seinem eigenen Ordner an und ändert keine
Einstellungen des Macs. Aus dem Internet lädt es nur beim ersten Start, und
nur die Bausteine, die es zum Laufen braucht.

Das Programm läuft **nur auf diesem Mac**. Die Adresse `127.0.0.1` steht für
den eigenen Rechner — niemand im selben Netz kann die Oberfläche sehen.

Die Auswertungsansicht kann die Daten nur **lesen**, nicht verändern.
Hinsehen ändert also nichts an dem, was über ein Kind festgehalten wurde.

Gespeichert werden die Aufgaben, die Antworten und die daraus abgeleiteten
Einschätzungen — aber **kein Name**. Nur das Kürzel, das beim Start
eingetippt wurde.
