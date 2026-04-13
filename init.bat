@echo off
setlocal

echo ==========================================
echo Initializing Project...
echo ==========================================

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment.
        exit /b %ERRORLEVEL%
    )
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo Failed to activate virtual environment.
    exit /b %ERRORLEVEL%
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install dependencies.
        exit /b %ERRORLEVEL%
    )
) else (
    echo Warning: requirements.txt not found. Skipping dependency installation.
)

REM Run Database Migrations
if exist "migrations" (
    echo Running database migrations...
    flask db upgrade
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to run migrations.
        exit /b %ERRORLEVEL%
    )
    echo Migrations applied successfully.
) else (
    echo Warning: migrations folder not found. Skipping migrations.
)

echo ==========================================
echo Project Initialization Complete!
echo ==========================================
pause
