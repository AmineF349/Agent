@echo off
REM Double-cliquez sur ce fichier pour lancer l'application (equivalent de .\start.ps1).
REM Contourne la politique d'execution PowerShell pour ce lancement uniquement.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
echo.
pause
