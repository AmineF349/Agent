@echo off
rem ==========================================================================
rem  Wrapper sans strategie d'execution pour test.ps1
rem ==========================================================================
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0test.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
endlocal & exit /b %RC%
