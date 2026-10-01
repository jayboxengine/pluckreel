@echo off
rem Opens the app, starting the background server first if it isn't running.
wscript "%~dp0start-server.vbs"

rem Wait up to ~15s for the server to answer before opening the browser.
for /l %%i in (1,1,30) do (
  curl -s -o nul http://127.0.0.1:8000/ && goto open
  ping -n 1 -w 500 127.0.0.1 >nul
)
:open
start "" http://127.0.0.1:8000/
