@echo off
rem Stops the background server (whatever is listening on 127.0.0.1:8000).
set found=
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:"127.0.0.1:8000 .*LISTENING"') do (
  taskkill /F /T /PID %%p >nul 2>&1
  set found=1
)
if defined found (echo PluckReel server stopped.) else (echo Server was not running.)
timeout /t 2 >nul
