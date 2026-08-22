@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo   SPACE EXPERIMENT AI - STARTING EDGE SERVER
echo ================================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
  echo ERROR: Python virtual environment was not found.
  echo Expected: backend\.venv\Scripts\python.exe
  echo.
  echo If this is a new laptop, run the setup steps first.
  pause
  exit /b 1
)

echo Starting FastAPI + YOLO backend...
start "Space Experiment AI - Backend" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe main.py"

echo Waiting for the backend to start...
timeout /t 6 /nobreak >nul

echo Opening the local dashboard...
start "" "http://localhost:8000/"

echo.
echo The AI backend is running in a separate window.
echo Keep that window open while using the dashboard.
echo.
exit /b 0
