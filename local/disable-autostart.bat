@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-autostart.ps1" -Remove
timeout /t 4 >nul
