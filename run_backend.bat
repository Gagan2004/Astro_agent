@echo off
echo ====================================================
echo             STARTING ASTROAGENT BACKEND
echo ====================================================
cd /d "%~dp0"
if not exist "backend\venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at backend\venv\Scripts\activate.bat
    echo Please make sure the venv is created in the backend folder.
    pause
    exit /b 1
)

echo [INFO] Activating virtual environment...
call backend\venv\Scripts\activate.bat

echo [INFO] Starting FastAPI server via Uvicorn...
python -m uvicorn backend.app.main:app --reload --port 8001

pause
