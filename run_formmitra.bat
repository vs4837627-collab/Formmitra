@echo off
title FormMitra - AI Document & Form Assistant
echo ===================================================================
echo                     Starting FormMitra Backend
echo                 Open: http://localhost:8000
echo ===================================================================
echo.
cd /d "%~dp0\backend"
..\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
