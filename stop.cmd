@echo off
REM Double-cliquez sur ce fichier pour arreter l'application (equivalent de .\stop.ps1).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" %*
echo.
pause
