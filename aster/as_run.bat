@echo off
echo AS_RUN_WRAPPER_V5
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0as_run_convert.ps1" %*
exit /b %errorlevel%
