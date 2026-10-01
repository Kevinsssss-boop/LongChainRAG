@echo off
title RAG Knowledge QA System

echo ========================================
echo   RAG Knowledge QA System - Starting...
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

:: Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo [1/4] Installing backend dependencies...
cd backend
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Backend dependency install failed
    pause
    exit /b 1
)
echo       Backend dependencies OK

echo [2/4] Starting backend server (port 8000)...
start "RAG-Backend" cmd /k "cd /d %~dp0backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo       Backend server started

echo [3/4] Installing frontend dependencies...
cd /d %~dp0frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Frontend dependency install failed
    pause
    exit /b 1
)
echo       Frontend dependencies OK

echo [4/4] Starting frontend server (port 5173)...
start "RAG-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo       Frontend server started

echo.
echo ========================================
echo   Startup Complete!
echo   Frontend : http://localhost:5173
echo   API Docs : http://localhost:8000/docs
echo ========================================
echo.
echo   [NOTE] Admin password
echo   No default password any more. On first run the backend
echo   prints a randomly generated one in its console window
echo   (the "RAG-Backend" window) -- copy it from there.
echo   To set a fixed password, put ADMIN_PASSWORD=... in
echo   backend\.env and restart the backend.
echo.
echo   [NOTE] First run also needs a real LLM API key in
echo   backend\.env -- see backend\.env.example
echo.
echo Press any key to open browser...
pause >nul
start http://localhost:5173
