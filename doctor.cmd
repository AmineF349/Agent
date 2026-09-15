@echo off
REM Double-cliquez sur ce fichier pour diagnostiquer l'installation (equivalent de .\doctor.ps1).
REM Contourne la politique d'execution PowerShell pour ce lancement uniquement.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0doctor.ps1" %*
echo.
pause
