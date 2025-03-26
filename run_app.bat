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

REM Run the main application
call venv\Scripts\activate.bat
python finance_assistant/main.py
