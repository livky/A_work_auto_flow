@echo off
setlocal
rem Dispatch from the installed workspace, regardless of the caller's directory.
pushd "%~dp0"
if "%~1"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0automation\python.ps1" "%~dp0automation\scripts\workspace_cli.py" workbench
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0automation\python.ps1" "%~dp0automation\scripts\workspace_cli.py" %*
)
set "WORKBENCH_EXIT=%errorlevel%"
popd
exit /b %WORKBENCH_EXIT%
