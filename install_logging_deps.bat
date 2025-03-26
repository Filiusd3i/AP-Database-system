@echo off
setlocal

echo Installing logging dependencies for AP Database System...

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Install required packages
pip install python-logstash-async

echo.
echo Installation complete. You can now run the application with enhanced logging capabilities.
echo.

pause
