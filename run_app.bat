@echo off
setlocal

REM Check if "fix" argument is provided
if "%1"=="fix" (
    echo Running database column fix...
    call venv\Scripts\activate.bat
    python -m finance_assistant.db_schema_fix --all --fix-amounts
    if errorlevel 1 (
        echo Error fixing database columns!
        pause
        exit /b 1
    )
    echo Database columns fixed successfully!
    echo Schema changes recorded in CHANGELOG.md
    echo.
)

REM Initialize the database schema for private equity support
echo Initializing Private Equity Dashboard Schema...
call venv\Scripts\activate.bat
python -c "from finance_assistant.database.manager import DatabaseManager; db = DatabaseManager(); db.connect_to_database(db_name='finance_db', host='localhost', port=5432, user='postgres', password=None); db.ensure_private_equity_schema()"
if errorlevel 1 (
    echo Warning: Private Equity schema initialization might have failed!
    echo You may need to manually configure your database settings.
    echo Continuing with application launch...
    echo.
)

REM Run the Finance Assistant application with the Private Equity Dashboard
echo Launching Finance Assistant with Private Equity Dashboard...
call venv\Scripts\activate.bat
python finance_assistant/main.py

echo.
echo Application closed.
pause
