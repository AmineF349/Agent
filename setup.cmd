@echo off
REM Double-cliquez sur ce fichier pour installer (equivalent de .\setup.ps1).
REM Contourne la politique d'execution PowerShell pour ce lancement uniquement.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
echo.
pause
