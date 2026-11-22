@echo off
title HireMate
echo.
echo ============================================
echo   HireMate - Your AI Job Search Assistant
echo ============================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.9+ first.
    pause
    exit /b 1
)

:: Check if venv exists, create if not
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install dependencies
echo [*] Installing dependencies...
python -m pip install -r requirements.txt --quiet

:: Run the app
echo.
echo [*] Starting HireMate...
echo [*] Open http://localhost:5000 in your browser
echo [*] Go to Settings to configure your free AI provider
echo.
python app.py
