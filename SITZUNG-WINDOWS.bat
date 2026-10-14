@echo off
rem ====================================================================
rem  Mit einem Kind arbeiten - Windows.
rem
rem  Doppelklicken. Fragt nach der Kennung des Kindes und startet den
rem  Aufgabendurchlauf im Fenster.
rem
rem  Wie START-WINDOWS.bat nur eine Huelle: die Abfrage der Kennung
rem  steht in tools\sitzung.py und nicht hier. "set /p" in cmd fuehrt
rem  aus, was jemand eintippt, laesst bei leerer Eingabe den vorigen
rem  Wert stehen - das waere das vorige Kind - und zeigt nicht
rem  verlaesslich an, was tatsaechlich ankommt. Bei einer pseudonymen
rem  Kennung (Paragraf 86) ist das nicht hinnehmbar.
rem
rem  Reines ASCII, auch in den Kommentaren: das Paragrafenzeichen gaebe
rem  es in der Codepage 850 zwar, aber eine Datei, die zu 99 Prozent
rem  ASCII ist, laedt zu genau einer Ausnahme ein - und die naechste
rem  waere dann ein Umlaut in einer echo-Zeile.
rem ====================================================================

cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 goto :kein_python

py -3 -u "%~dp0tools\sitzung.py"
if errorlevel 9009 goto :kein_python
if errorlevel 1 pause
exit /b

:kein_python
echo.
echo   Auf diesem PC fehlt Python.
echo.
echo   Bitte zuerst START-WINDOWS.bat doppelklicken - dort steht, wie
echo   Python auf diesen PC kommt.
echo.
pause
exit /b 1
