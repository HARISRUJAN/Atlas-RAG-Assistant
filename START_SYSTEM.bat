@echo off
echo ========================================
echo Starting MongoDB RAG System
echo ========================================
echo.

REM Start Backend
echo [1/2] Starting Backend...
start "Backend Server" cmd /k "cd /d %~dp0 && call rag_env\Scripts\activate.bat && python -m backend.app"
timeout /t 5 /nobreak >nul

REM Start Frontend  
echo [2/2] Starting Frontend...
start "Frontend Server" cmd /k "cd /d %~dp0\frontend && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo System Started!
echo ========================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5173
echo.
echo Press any key to exit (servers will keep running)...
pause >nul

