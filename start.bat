@echo off
title GeoPulse System Launcher
echo ========================================================
echo   🛰️ Starting GeoPulse SAR Intelligence System
echo ========================================================

echo [1/3] Launching FastAPI Backend Server on port 8000...
start "GeoPulse Backend API (Port 8000)" cmd /k "cd /d "%~dp0backend" && python scripts\run_server.py --port 8000"

echo [2/3] Launching Frontend Web Suite on port 3000...
start "GeoPulse Frontend Suite (Port 3000)" cmd /k "cd /d "%~dp0Frontend" && python serve.py 3000"

echo [3/3] Launching React Parallax Dev Server on port 5173...
start "GeoPulse React Parallax (Port 5173)" cmd /k "cd /d "%~dp0Frontend\react-parallax" && npm run dev"

echo Waiting for servers to initialize...
timeout /t 3 /nobreak >nul

echo Opening browser...
start http://localhost:3000/explorer

echo.
echo ========================================================
echo   ✅ All services are running!
echo   - Backend:  http://localhost:8000 (Docs: /docs)
echo   - Frontend: http://localhost:3000
echo   - React:    http://localhost:5173
echo ========================================================
