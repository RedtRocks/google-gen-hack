@echo off
echo ========================================
echo Legal Document Demystifier - Startup
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo.

REM Install/upgrade Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt
echo.

REM Check if frontend is built
if not exist "client\dist\index.html" (
    echo Frontend not built. Building now...
    echo Installing npm dependencies...
    call npm install --legacy-peer-deps
    echo.
    echo Building frontend...
    call npm run client:build
    echo.
)

REM Check for .env file
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Please create a .env file with your GEMINI_API_KEY
    echo Example:
    echo GEMINI_API_KEY=your-api-key-here
    echo PORT=8080
    echo.
    pause
    exit /b 1
)

echo ========================================
echo Starting application...
echo ========================================
echo Server will be available at: http://localhost:8080
echo Press Ctrl+C to stop the server
echo.

python main.py
