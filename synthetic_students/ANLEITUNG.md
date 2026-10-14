# Sichtbarer Test in deinem Programm

Nach Installation liegt im Ordner `12` die Datei **TEST-SUS-MAC.command**.

1. Doppelklicke diese Datei. Sie öffnet die Testansicht im Browser.
2. Wähle einen Test-SuS, zum Beispiel SUS_05.
3. Klicke **Test starten**.
4. Beobachte Aufgabe, Antwort und Bewertung. **Pause** hält den Ablauf an; **Einzelschritt** zeigt abwechselnd Antwort und nächste Aufgabe.
5. Unten findest du die bestehende **Kompetenzkarte**, **Fehleranalyse**, **Hypothesen**, **Evidenz** und den **Aufgabenverlauf**. Mit **Auswertung groß öffnen** öffnest du diese Ansicht in einem eigenen Tab.
6. Später kannst du unter **Gespeicherte Ergebnisse** einen abgeschlossenen Lauf auswählen und **Ergebnis anzeigen** anklicken.

Das Terminalfenster offen lassen, solange du die Browseransicht verwendest. Nach dem Schließen erneut `TEST-SUS-MAC.command` starten. Die Browseradresse wird automatisch gewählt, damit ein bereits laufendes Programm nicht gestört wird.

Die Erweiterung verwendet die echte Test-Engine und die unveränderte Auswertungsoberfläche aus `12/ui`. Sie ergänzt eine Entwickleransicht für synthetische Testpersonen. Eine neue direkte Bedienung durch echte Schüler:innen oder die vollständige Animation von Drag-and-drop ist nicht enthalten. Noch nicht grafisch umgesetzte Aufgabenmaterialien werden mit den gelieferten Stimulusdaten dargestellt. Unbekannte Anordnungen werden als unbekannt angezeigt, nicht fachlich ergänzt.

Alle Testdaten und Berichte werden separat unter `12/synthetic_students/visible_results` gespeichert. Die produktive `mathkomp.sqlite3` wird nicht verändert. Die Auswertung verwendet die neutrale Kennung `SIMULATED_LEARNER`; das zugehörige SUS-Profil steht in der Testansicht und im Bericht. Das Sollprofil wird nicht an die Fachlogik weitergegeben. Die gespeicherten Ergebnisdateien enthalten die tatsächlichen MVP-Ergebnisse und getrennt davon den technischen Soll-/Ist-Vergleich. REVIEW umfasst auch nicht automatisch prüfbare Erwartungen.

Pro Durchlauf ist ein Profil aktiv. Die Auswahl und Auswertung gelten für alle Browserfenster dieses Testservers gemeinsam. Bei 100 Aufgaben stoppt die Erweiterung mit `MAX_TASKS`. Die Simulation verwendet die Aufgaben und Konfiguration aus `content/`.

## Technische Prüfung

Alle 14 Profile mit Seed 42: 752 Antworten ohne Abweichung zwischen erzeugter Richtigkeit und dem MVP-Scoring. Doppelte Abgabe derselben Aufgabenansicht wird abgefangen. Pause, Einzelschritt und Aktualisierung der eingebetteten Kompetenzkarte wurden im Browser geprüft.
