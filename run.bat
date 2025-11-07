@echo off
REM Script to run the MongoDB RAG System on Windows

echo ================================
echo MongoDB RAG System Startup
echo ================================
echo.

REM Check if virtual environment exists
if not exist "rag_env" (
    echo Creating virtual environment...
    python -m venv rag_env
)

REM Activate virtual environment
echo Activating virtual environment...
call rag_env\Scripts\activate.bat

REM Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check environment variables
if not exist ".env" (
    echo Warning: .env file not found. Please create one from .env.example
    exit /b 1
)

REM Start backend
echo.
echo Starting Flask backend on port 5000...
start "Flask Backend" cmd /k "cd backend && python app.py"

REM Wait for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend
echo.
echo Starting React frontend on port 5173...
start "React Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ================================
echo System Started Successfully!
echo ================================
echo Backend API: http://localhost:5000/api
echo Frontend UI: http://localhost:5173
echo.
echo Close the terminal windows to stop services
echo.
pause

