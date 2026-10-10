' Starts the PluckReel server hidden (no console window).
' Safe to run repeatedly: run_local.py exits at once if the server is already up.
Set fso = CreateObject("Scripting.FileSystemObject")
serverDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName)) & "\server"

Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = serverDir
shell.Run """" & serverDir & "\.venv\Scripts\pythonw.exe"" """ & serverDir & "\run_local.py""", 0, False
