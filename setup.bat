@echo off
rem ==========================================================================
rem  Wrapper sans strategie d'execution : lance setup.ps1 meme si la GPO
rem  Windows bloque les scripts PowerShell (ExecutionPolicy Restricted).
rem  Usage : double-clic, ou  setup.bat  [arguments passes a setup.ps1]
rem ==========================================================================
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo setup.ps1 a retourne le code %RC%.
  pause
)
pause
endlocal & exit /b %RC%
