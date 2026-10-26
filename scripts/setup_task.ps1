# Register a Windows Scheduled Task for the daily Naukri assistant.
# Run once in PowerShell (preferably as your user, not SYSTEM):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#   .\scripts\setup_task.ps1
#
# Default: daily at 09:00 local time, wakes PC if allowed by power settings.
# Task runs run_daily.bat which defaults to dry-run (no --apply).

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Bat = Join-Path $RepoRoot "scripts\run_daily.bat"
$TaskName = "NaukriApplyDaily"

if (-not (Test-Path $Bat)) {
    Write-Error "Missing $Bat"
}

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$Bat`"" -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At 9:00am
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun

# Current user interactive session so the browser can show OTP prompts
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

Write-Host "Registered scheduled task '$TaskName' (daily 09:00)."
Write-Host "Repo: $RepoRoot"
Write-Host "Edit scripts\run_daily.bat to switch from dry-run to --apply when ready."
Write-Host "Verify: Get-ScheduledTask -TaskName $TaskName"
Write-Host "Remove:  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
