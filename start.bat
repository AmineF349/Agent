@echo off
rem ==========================================================================
rem  Wrapper sans strategie d'execution pour start.ps1
rem  Usage : double-clic, ou  start.bat  [arguments passes a start.ps1]
rem ==========================================================================
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo start.ps1 a retourne le code %RC%.
  pause
)
endlocal & exit /b %RC%
