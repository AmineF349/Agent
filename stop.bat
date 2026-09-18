@echo off
rem ==========================================================================
rem  Wrapper sans strategie d'execution pour stop.ps1
rem ==========================================================================
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
endlocal & exit /b %RC%
