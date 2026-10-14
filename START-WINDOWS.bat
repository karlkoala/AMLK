@echo off
rem ====================================================================
rem  Kompetenzanalyse starten - Windows.
rem
rem  Doppelklicken. Beim ersten Mal richtet sich das Programm ein - das
rem  dauert etwa eine halbe Minute und braucht einmalig Internet.
rem  Danach startet es nur noch. Es ist derselbe Klick, immer.
rem
rem  WARUM DIESE DATEI SO KURZ IST
rem  Alles, was eine Bedingung, eine Schleife, eine Eingabe oder ein
rem  Sonderzeichen braucht, steht in tools\start.py. cmd.exe scheitert
rem  bei solchen Dingen naemlich nicht, sondern fuehrt lautlos etwas
rem  anderes aus: "call :abbruch" bricht nicht ab, "^&" wird in einem
rem  Klammerblock zu Text, "set /p" fuehrt Eingetipptes aus - und das
rem  Gegenmittel dagegen loescht jedes Ausrufezeichen aus den Pfaden.
rem  Die Begruendung im Einzelnen steht im Kopf von tools\start.py.
rem
rem  Reines ASCII und CRLF sind hier Pflicht: eine Konsole liest eine
rem  .bat in der Codepage 850, nicht in UTF-8. Umlaute wuerden schon
rem  beim Einlesen zerfallen. Festgehalten in tests\test_windows_start.py.
rem ====================================================================

cd /d "%~dp0"

rem  Nicht fragen, ob es "py" gibt, sondern ob etwas Brauchbares startet:
rem  auch py.exe liegt auf manchen Rechnern als Platzhalter des Microsoft
rem  Store herum und meldet sich mit 9009, statt Python zu starten.
where py >nul 2>nul
if errorlevel 1 goto :kein_python

py -3 -u "%~dp0tools\start.py"
if errorlevel 9009 goto :kein_python

rem  Nur im Fehlerfall anhalten. Bei einem geordneten Ende hat start.py
rem  schon selbst auf die Eingabetaste gewartet; hier faengt "pause" nur
rem  noch den Absturz ab, dessen Meldung sonst mit dem Fenster verschwaende.
if errorlevel 1 pause
exit /b

:kein_python
echo.
echo   Auf diesem PC fehlt Python.
echo.
echo   Das Programm braucht eine Grundlage namens Python. Windows
echo   bringt keine mit.
echo.
echo   So geht es:
echo     1. https://www.python.org/downloads/ im Browser oeffnen
echo     2. die grosse gelbe Schaltflaeche anklicken
echo     3. die geladene Datei doppelklicken und dem
echo        Installationsfenster folgen
echo     4. danach diese Startdatei hier erneut doppelklicken
echo.
echo   Die Haken im Installationsfenster koennen bleiben, wie sie sind.
echo   Das Fenster fragt einmal nach dem Kennwort des PCs. Das ist
echo   normal und richtig.
echo.
pause
exit /b 1
