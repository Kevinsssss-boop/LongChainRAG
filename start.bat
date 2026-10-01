@echo off
setlocal
title RAG Knowledge QA System

set "ROOT=%~dp0"
set "VENV=%ROOT%backend\.venv"
set "PY=%VENV%\Scripts\python.exe"

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

:: ---------------------------------------------------------------------------
:: 后端的依赖装进项目自带的 venv，不装进全局 Python。
:: 之前是 `pip install -r requirements.txt` 直接装到系统环境里 —— 会污染全局，
:: 而且 requirements.txt 写的是版本区间，换台机器装出来的东西可能不一样。
:: 现在：没有 venv 就建一个，然后按 requirements.lock 装精确版本。
:: ---------------------------------------------------------------------------
echo [1/4] Preparing backend virtual environment...

if not exist "%PY%" (
    echo       No venv found, creating backend\.venv ...
    python -m venv "%VENV%"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo         Python 3.11 or newer is required.
        pause
        exit /b 1
    )
)

echo       Installing backend dependencies from requirements.lock ...
"%PY%" -m pip install --disable-pip-version-check -q -r "%ROOT%backend\requirements.lock"
if %errorlevel% neq 0 (
    echo [ERROR] Backend dependency install failed
    pause
    exit /b 1
)
echo       Backend dependencies OK

echo [2/4] Starting backend server (port 8000)...
start "RAG-Backend" cmd /k "cd /d "%ROOT%backend" && "%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo       Backend server started

echo [3/4] Installing frontend dependencies...
:: 用 npm ci 而不是 npm install：前者严格按 package-lock.json 装，
:: lock 和 package.json 对不上会直接报错，而不是悄悄装一个别的版本
pushd "%ROOT%frontend"
call npm ci
if %errorlevel% neq 0 (
    echo [ERROR] Frontend dependency install failed
    popd
    pause
    exit /b 1
)
echo       Frontend dependencies OK

echo [4/4] Starting frontend server (port 5173)...
start "RAG-Frontend" cmd /k "cd /d "%ROOT%frontend" && npm run dev"
popd
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
