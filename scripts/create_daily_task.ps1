param(
    [string]$Time = "06:00"
)

$ErrorActionPreference = "Stop"

$Runner = Join-Path `
    $PSScriptRoot `
    "run_etl.ps1"

$TaskName = "Online Retail ETL"

if (-not (Test-Path $Runner)) {
    throw "Scheduler runner not found: $Runner"
}

$At = [datetime]::ParseExact(
    $Time,
    "HH:mm",
    $null
)

$Action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$Runner`""

$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $At

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily Online Retail ETL pipeline" `
    -Force |
    Out-Null

Write-Host "Created scheduled task '$TaskName' for $Time."
Write-Host "Runner: $Runner"
Write-Host "Overlapping runs are ignored."
Write-Host "Failed runs retry up to three times."
