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

1. Die erhaltene Datei **`mathkomp-fuer-mac.zip`** doppelklicken.
   Daneben entsteht ein Ordner **`mathkomp`**.
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

Im Ordner `mathkomp` liegen zwei Startsymbole:

| Symbol | wofür |
|---|---|
| **`START-MAC.command`** | die Auswertung ansehen |
| **`SITZUNG-MAC.command`** | mit einem Kind arbeiten |

Beim allerersten Mal: **`START-MAC.command`** doppelklicken.

macOS lässt das beim ersten Mal nicht zu, weil die Datei aus dem Internet
kommt. Der Weg dahin:

1. Doppelklicken. Es erscheint eine Meldung, dass die Datei nicht geöffnet
   werden kann. Diese Meldung schließen.
2. **Apfelmenü** → **Systemeinstellungen** → **Datenschutz & Sicherheit**
3. Dort ganz nach unten scrollen. Es steht eine Zeile über die gerade
   blockierte Datei, daneben **Dennoch öffnen**. Darauf klicken.
4. Der Mac fragt noch einmal nach — **Öffnen** bestätigen.

> Auf älteren Macs geht es kürzer: mit der rechten Maustaste auf die Datei
> klicken (oder mit zwei Fingern auf dem Trackpad), im Menü **Öffnen** wählen,
> und im Fenster noch einmal **Öffnen**.

Diese Frage kommt **einmal pro Ordner**. Geht beim ersten Versuch etwas
schief, die ZIP-Datei bitte *nicht* noch einmal auspacken — dann entsteht ein
zweiter Ordner, und die Frage kommt wieder. Einfach den vorhandenen Ordner
weiterbenutzen.

**Ab dann:** einfach doppelklicken.

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
| „Diese Startdatei liegt nicht mehr in ihrem Ordner" | Das Startsymbol zurück in den Ordner `mathkomp` legen. Es funktioniert nur dort. |
| „Die Arbeitsumgebung liess sich nicht anlegen" | Den Ordner `mathkomp` in den Benutzerordner ziehen (Schritt 2), dann erneut starten |
| „Die Installation ist fehlgeschlagen" | Internetverbindung prüfen. Nur dieser eine Schritt braucht sie. |
| „Das Programm wird gerade in einem anderen Fenster gestartet" | Es läuft schon. Dieses Fenster schließen, das andere benutzen. |
| „Das Programm laeuft bereits in einem anderen Fenster" | Kein Fehler. Die Oberfläche wurde erneut geöffnet. |
| „Die Datenbank in diesem Ordner ist beschaedigt" | Nichts löschen, bitte melden |
| „Die Datenbank liess sich nicht aufbauen" | Melden, und die Datei `einrichtung.log` aus dem Ordner mitschicken |
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
