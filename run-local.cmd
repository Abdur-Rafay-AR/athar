@echo off
echo Setting up local environment for Agent Tracer...

REM Check if venv exists, if not create it
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install the package in editable mode
echo Installing package and dependencies...
pip install -e .

REM Start the application
echo Starting Agent Tracer...
agent-tracer

pause
