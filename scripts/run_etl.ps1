$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path `
    $ProjectRoot `
    ".venv\Scripts\python.exe"

$LogDirectory = Join-Path `
    $ProjectRoot `
    "logs"

$LogFile = Join-Path `
    $LogDirectory `
    "task_scheduler.log"

if (-not (Test-Path $Python)) {
    throw "Python not found: $Python"
}

New-Item `
    -ItemType Directory `
    -Path $LogDirectory `
    -Force | Out-Null

"$(Get-Date -Format o) | Scheduled ETL started" |
    Out-File `
        -FilePath $LogFile `
        -Append `
        -Encoding utf8

$PreviousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"

& $Python -m src.run_etl *>> $LogFile

$PythonExitCode = $LASTEXITCODE
$ErrorActionPreference = $PreviousErrorActionPreference

if ($PythonExitCode -ne 0) {
    "$(Get-Date -Format o) | Scheduled ETL failed with exit code $PythonExitCode" |
        Out-File `
            -FilePath $LogFile `
            -Append `
            -Encoding utf8

    throw "ETL failed with exit code $PythonExitCode. Read $LogFile"
}

"$(Get-Date -Format o) | Scheduled ETL completed" |
    Out-File `
        -FilePath $LogFile `
        -Append `
        -Encoding utf8
