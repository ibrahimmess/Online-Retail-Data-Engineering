param(
    [string]$Time = "06:00"
)

$ErrorActionPreference = "Stop"

$Runner = Join-Path `
    $PSScriptRoot `
    "run_etl.ps1"

$TaskName = "Online Retail ETL"

$At = [datetime]::ParseExact(
    $Time,
    "HH:mm",
    $null
)

$Action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`""

$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $At

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (
        New-TimeSpan -Hours 2
    )

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily Online Retail ETL" `
    -Force | Out-Null

Write-Host ("Created scheduled task '$TaskName' for $Time.")