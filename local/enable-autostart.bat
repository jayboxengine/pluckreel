@echo off
rem Keeps the server running: starts it at login and restarts it within 5 minutes if it stops.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-autostart.ps1"
echo Open http://127.0.0.1:8000 (or double-click "PluckReel.bat").
timeout /t 4 >nul
