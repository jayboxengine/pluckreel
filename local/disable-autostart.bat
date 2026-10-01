@echo off
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Video Downloader Server.lnk" 2>nul
echo Autostart disabled. (The server keeps running until you log out or run stop-server.bat.)
timeout /t 4 >nul
