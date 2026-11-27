@echo off
setlocal
title Guiwu - Campus Lost and Found

set "APP=%~dp0"
set "PY="

rem ---- 1) py launcher ----
for /f "delims=" %%I in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do call :probe "%%I"

rem ---- 2) common install locations ----
call :probe "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
call :probe "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
call :probe "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
call :probe "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
call :probe "C:\Python313\python.exe"
call :probe "C:\Python312\python.exe"
call :probe "C:\Python311\python.exe"
call :probe "C:\ProgramData\Anaconda3\python.exe"
call :probe "%USERPROFILE%\anaconda3\python.exe"
call :probe "%USERPROFILE%\miniconda3\python.exe"

rem ---- 3) fallback: the interpreter shipped with DSH ----
if not defined PY call :probe "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"

if not defined PY goto :nopython

echo.
echo   Guiwu - Campus Lost and Found (prototype)
echo   Python: %PY%
echo.
echo   Student  http://127.0.0.1:8000/
echo   Admin    http://127.0.0.1:8000/admin
echo.
"%PY%" -u "%APP%server.py"
echo.
echo   Server stopped.
pause
exit /b 0

:nopython
echo.
echo   [x] No Python 3 found on this machine.
echo.
echo   Install it (about 2 minutes):
echo       winget install -e --id Python.Python.3.12
echo   Then reopen the terminal and run this file again.
echo.
echo   Note: if Windows says "Python was not found; run without arguments to
echo   install from the Microsoft Store", the python command is only a Store
echo   alias and no real interpreter is installed.
echo.
pause
exit /b 1

:probe
if defined PY goto :eof
if not exist "%~1" goto :eof
"%~1" -c "import sys" >nul 2>nul
if not errorlevel 1 set "PY=%~1"
goto :eof
