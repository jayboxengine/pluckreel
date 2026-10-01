@echo off
rem Starts the server hidden every time you log in to Windows (per-user, no admin needed).
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Video Downloader Server.lnk"
powershell -NoProfile -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);" ^
  "$s.TargetPath = 'wscript.exe';" ^
  "$s.Arguments = '\"%~dp0start-server.vbs\"';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.Description = 'Video Downloader background server';" ^
  "$s.Save()"
wscript "%~dp0start-server.vbs"
echo Autostart enabled. The server is running now and will start at every login.
echo Open http://127.0.0.1:8000 (or double-click "Video Downloader.bat").
timeout /t 4 >nul
