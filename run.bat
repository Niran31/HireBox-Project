@echo off
setlocal

echo ==========================================
echo Starting Application...
echo ==========================================

REM Check if venv exists
if not exist "venv" (
    echo Error: Virtual environment not found. Please run init.bat first.
    pause
    exit /b 1
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b %ERRORLEVEL%
)

REM Run the application
echo Running Flask application...
venv\Scripts\python.exe run.py

if %ERRORLEVEL% NEQ 0 (
    echo Application exited with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

echo Application stopped.
pause
