@echo off
echo Running Database Schema Check...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if psycopg2 is installed
python -c "import psycopg2" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required dependencies...
    pip install psycopg2-binary python-dotenv
    if %errorlevel% neq 0 (
        echo Error installing dependencies. Please run manually:
        echo pip install psycopg2-binary python-dotenv
        pause
        exit /b 1
    )
)

REM Run the database check
echo.
echo DETAILED DATABASE SCHEMA DIAGNOSTIC
echo ==================================
echo.
echo This will perform a comprehensive check of your database schema and identify any issues
echo with vendor column naming, data types, and other potential problems.
echo.
echo Options:
echo 1. Basic check (default)
echo 2. Detailed check with sample data
echo 3. Export report to JSON file

set /p choice="Enter your choice (1-3) or press Enter for default: "

if "%choice%"=="2" (
    python check_db.py --verbose
) else if "%choice%"=="3" (
    set /p filename="Enter filename for report (default: db_report.json): "
    if "%filename%"=="" set filename=db_report.json
    python check_db.py --export %filename%
    echo Report saved to %filename%
) else (
    python check_db.py
)

echo.
echo Check completed. See results above for any issues detected.
echo.

REM Ask if user wants to fix vendor column issue automatically
echo Would you like to run the vendor column fix tool now?
echo This will attempt to fix any vendor/vendor_name column issues detected.
echo.
set /p fix_choice="Run fix tool? (y/n): "

if /i "%fix_choice%"=="y" (
    echo.
    echo Running vendor column fix tool...
    echo.
    python run_fix.py
    if %errorlevel% neq 0 (
        echo.
        echo Fix operation failed with errors. Check the log above for details.
    ) else (
        echo.
        echo Fix operation completed successfully.
    )
    echo.
    echo Please restart your application to apply changes.
)

pause
