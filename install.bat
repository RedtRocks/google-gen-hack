@echo off
echo ========================================
echo Legal Document Demystifier - Installation
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    echo.
) else (
    echo Virtual environment already exists.
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo.

REM Install/upgrade Python dependencies
echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt
echo.

REM Install npm dependencies
echo Installing npm dependencies...
call npm install --legacy-peer-deps
echo.

REM Build frontend
echo Building frontend...
call npm run client:build
echo.

REM Check for .env file
if not exist ".env" (
    echo.
    echo ========================================
    echo IMPORTANT: Environment Setup
    echo ========================================
    echo .env file not found. Creating from example...
    if exist ".env.example" (
        copy .env.example .env
        echo .env file created. Please edit it and add your GEMINI_API_KEY
    ) else (
        echo GEMINI_API_KEY=your-api-key-here> .env
        echo PORT=8080>> .env
        echo .env file created. Please edit it and add your GEMINI_API_KEY
    )
    echo.
    echo Get your API key from: https://aistudio.google.com/app/apikey
    echo.
)

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file and add your GEMINI_API_KEY
echo 2. Run 'start.bat' to start the application
echo.
pause
