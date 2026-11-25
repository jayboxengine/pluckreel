# Keeps the PluckReel server running: a scheduled task starts it at login and re-checks every
# 5 minutes, restarting it if it stopped (shutdown, crash, sleep issues). start-server.vbs does
# nothing if the server is already up, so the repeat is harmless. Runs as you, no admin needed.
param([switch]$Remove)

$TaskName = 'PluckReel Server'
$Vbs = Join-Path $PSScriptRoot 'start-server.vbs'
$Startup = [Environment]::GetFolderPath('Startup')

# The older Startup-folder shortcut is replaced by the task (and could be switched off by Windows'
# Startup Apps or cleanup tools without notice).
Remove-Item "$Startup\PluckReel Server.lnk", "$Startup\Video Downloader Server.lnk" -ErrorAction SilentlyContinue

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host 'Autostart removed. (The server keeps running until you log out or run stop-server.bat.)'
    return
}

$user = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "`"$Vbs`"" -WorkingDirectory $PSScriptRoot

$atLogon = New-ScheduledTaskTrigger -AtLogOn -User $user
$every5 = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $atLogon, $every5 `
    -Settings $settings -Principal $principal -Force `
    -Description 'Keeps the PluckReel server (http://127.0.0.1:8000) running.' | Out-Null

Start-ScheduledTask -TaskName $TaskName
Write-Host 'Autostart enabled: PluckReel starts at login and is restarted within 5 minutes if it stops.'
