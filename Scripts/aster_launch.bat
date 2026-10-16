@echo off
rem Copyright (C) 2026 trednuK
rem This Source Code Form is subject to the terms of the Mozilla Public
rem License, v. 2.0. If a copy of the MPL was not distributed with this
rem file, You can obtain one at https://mozilla.org/MPL/2.0/.
rem aster_launch.bat
rem Started by bridge_run_aster._launch_command in the Code-Aster window:
rem runs run_aster.bat and then writes its exit code to an end marker
rem file, so that the bridge knows reliably that the run has ended.
rem A batch file instead of an echo of ERRORLEVEL on the cmd line itself:
rem the output goes through a pipe to tee, cmd expands such a line before
rem run_aster runs, and the exit code of a pipe is that of tee.
rem Arguments: 1 = run_aster.bat, 2 = .export, 3 = end marker file.
call "%~1" "%~2"
set "BRIDGE_RC=%ERRORLEVEL%"
rem Write to a temporary name first, so the bridge never reads half a file.
> "%~3.tmp" echo %BRIDGE_RC%
move /y "%~3.tmp" "%~3" > nul
exit /b %BRIDGE_RC%
