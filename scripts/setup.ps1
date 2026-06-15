$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher 'py' wurde nicht gefunden. Installieren Sie Python 3.12 oder 3.13."
}

$pythonSelector = $null
foreach ($candidate in @("-3.12", "-3.13")) {
    & py $candidate -c "import sys; print(sys.version)" *> $null
    if ($LASTEXITCODE -eq 0) {
        $pythonSelector = $candidate
        break
    }
}
if (-not $pythonSelector) {
    throw "Python 3.12 oder 3.13 wurde nicht gefunden."
}

& py $pythonSelector -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
& .\.venv\Scripts\python.exe -m pip install -e . --no-deps

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

Write-Host "Setup abgeschlossen. Start: .\scripts\run.ps1"
