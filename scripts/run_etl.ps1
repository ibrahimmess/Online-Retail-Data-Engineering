$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $ProjectRoot

$Python = Join-Path `
    $ProjectRoot `
    ".venv\Scripts\python.exe"

$LogFile = Join-Path `
    $ProjectRoot `
    "logs\task_scheduler.log"

if (-not (Test-Path $Python)) {
    throw "Python not found: $Python"
}
$LogDirectory = Join-Path $ProjectRoot "logs"

New-Item `
    -ItemType Directory `
    -Path $LogDirectory `
    -Force | Out-Null
& $Python -m src.run_etl *>> $LogFile

if ($LASTEXITCODE -ne 0) {
    throw "ETL failed. Read $LogFile"
}
