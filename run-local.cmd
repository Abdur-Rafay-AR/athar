@echo off
echo =======================================================
echo   ATHAR (أثر) · Local-First Multi-Agent Debugger
echo =======================================================

REM Check if venv exists, if not create it
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install the package in editable mode
echo Installing Athar in editable mode...
pip install -e .

REM Start the application
echo Starting Athar UI server on http://localhost:4173 ...
athar

pause
