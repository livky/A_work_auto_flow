@echo off
setlocal
rem Resolve every entry from this file, including paths with spaces or Chinese.
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
if not exist "%~dp0services\qdrant\runtime\python.exe" (
  echo Missing bundled runtime. Copy the COMPLETE workspace including services.
  exit /b 2
)
if "%~1"=="" goto interactive
"%~dp0services\qdrant\runtime\python.exe" "%~dp0automation\scripts\portable.py" %*
exit /b %errorlevel%
:interactive
"%~dp0services\qdrant\runtime\python.exe" "%~dp0automation\scripts\portable.py" check
set "CHECK_RESULT=%errorlevel%"
pause
exit /b %CHECK_RESULT%
