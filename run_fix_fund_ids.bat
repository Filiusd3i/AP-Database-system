@echo off
setlocal enabledelayedexpansion

REM Get current timestamp for log filename
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (set DATE=%%c%%b%%a)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set TIME=%%a%%b)
set TIMESTAMP=%DATE%_%TIME%

echo === Fund Management Dashboard - Fund ID Fix Tool ===
echo.
echo This script will fix missing fund_id values in invoices and vendor allocations:
echo - Identifies records with missing or invalid fund_id values
echo - Provides suggestions based on vendor relationships and other attributes
echo - Updates CSV files with the corrected values
echo.

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Log file
set LOG_FILE=logs\fund_fix_%TIMESTAMP%.log
echo Starting fund ID fix process at %date% %time% > %LOG_FILE%

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

python -c "import numpy" > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing numpy... >> %LOG_FILE%
    echo Installing numpy...
    pip install numpy >> %LOG_FILE% 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Error installing numpy >> %LOG_FILE%
        echo Error installing numpy. Please run: pip install numpy
        goto end
    )
)

REM Parse command line arguments
set AUTO_MODE=
set USERNAME=%USERNAME%

if "%~1"=="--auto" (
    set AUTO_MODE=--auto
    echo Running in automatic mode
    echo Running in automatic mode >> %LOG_FILE%
)

if "%~1"=="-a" (
    set AUTO_MODE=--auto
    echo Running in automatic mode
    echo Running in automatic mode >> %LOG_FILE%
)

if not "%~2"=="" (
    set USERNAME=%~2
)

echo Using username: %USERNAME% >> %LOG_FILE%

echo.
echo Running fund ID fix tool...
echo Running fund ID fix tool... >> %LOG_FILE%

REM Run the Python script with appropriate parameters
python fix_missing_fund_ids.py %AUTO_MODE% "%USERNAME%" >> %LOG_FILE% 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Fund ID fix process failed with exit code %ERRORLEVEL%.
    echo Error: Fund ID fix process failed with exit code %ERRORLEVEL%. >> %LOG_FILE%
    echo Please check the logs for more information: %LOG_FILE%
) else (
    echo.
    echo Fund ID fix completed successfully.
    echo Fund ID fix completed successfully. >> %LOG_FILE%
)

:end
echo Process completed at %date% %time% >> %LOG_FILE%
echo.
echo Log file: %LOG_FILE%
pause
