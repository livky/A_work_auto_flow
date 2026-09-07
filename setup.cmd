@echo off
setlocal
rem Bypass applies to this child process only; no permanent execution policy changes.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0automation\setup.ps1" %*
exit /b %errorlevel%
