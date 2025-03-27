@echo off
setlocal enabledelayedexpansion

REM Get current timestamp for log filename
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (set DATE=%%c%%b%%a)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set TIME=%%a%%b)
set TIMESTAMP=%DATE%_%TIME%

echo === Fund Management Dashboard - Schema Validation Tool ===
echo.
echo This script will validate the relationship schema against the CSV tables:
echo - Checks that all tables referenced in the schema exist
echo - Verifies that all columns referenced in relationships exist in their tables
echo - Identifies potential column name discrepancies
echo - Generates warning and error reports
echo.

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Log file
set LOG_FILE=logs\schema_validate_%TIMESTAMP%.log
echo Starting schema validation process at %date% %time% > %LOG_FILE%

REM Check if Python is installed
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH >> %LOG_FILE%
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher before running this script
    goto end
)

REM Get Python version for logging
python --version >> %LOG_FILE% 2>&1

REM Check for required Python packages
echo Checking required packages...
echo Checking required packages... >> %LOG_FILE%

python -c "import pandas" > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing pandas... >> %LOG_FILE%
    echo Installing pandas...
    pip install pandas >> %LOG_FILE% 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Error installing pandas >> %LOG_FILE%
        echo Error installing pandas. Please run: pip install pandas
        goto end
    )
)

python -c "import json" > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing json... >> %LOG_FILE%
    echo Installing json...
    pip install json >> %LOG_FILE% 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Error installing json >> %LOG_FILE%
        echo Error installing json. Please run: pip install json
        goto end
    )
)

REM Parse command line arguments
set AUTO_FIX=
set USERNAME=%USERNAME%

if "%~1"=="--auto-fix" (
    set AUTO_FIX=--auto-fix
    echo Running with auto-fix option
    echo Running with auto-fix option >> %LOG_FILE%
)

if "%~1"=="-f" (
    set AUTO_FIX=--auto-fix
    echo Running with auto-fix option
    echo Running with auto-fix option >> %LOG_FILE%
)

if not "%~2"=="" (
    set USERNAME=%~2
)

echo Using username: %USERNAME% >> %LOG_FILE%

REM Set paths
set TABLES_DIR=Tables
set SCHEMA_PATH=relationship_schema.json

echo.
echo Running schema validation tool...
echo Running schema validation tool... >> %LOG_FILE%
echo Tables directory: %TABLES_DIR%
echo Schema file: %SCHEMA_PATH%
echo.

REM Run the Python script with appropriate parameters
python validate_schema.py --tables-dir=%TABLES_DIR% --schema-path=%SCHEMA_PATH% %AUTO_FIX% --username="%USERNAME%" >> %LOG_FILE% 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Warning: Schema validation detected issues with exit code %ERRORLEVEL%.
    echo Warning: Schema validation detected issues with exit code %ERRORLEVEL%. >> %LOG_FILE%
    echo Check the console output above or review the log file for details.
) else (
    echo.
    echo Schema validation completed successfully.
    echo Schema validation completed successfully. >> %LOG_FILE%
)

:end
echo Process completed at %date% %time% >> %LOG_FILE%
echo.
echo Log file: %LOG_FILE%
pause
