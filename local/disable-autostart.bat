@echo off
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
del "%STARTUP%\PluckReel Server.lnk" 2>nul
del "%STARTUP%\Video Downloader Server.lnk" 2>nul
echo Autostart disabled. (The server keeps running until you log out or run stop-server.bat.)
timeout /t 4 >nul
