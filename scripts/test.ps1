$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    throw "Virtuelle Umgebung fehlt. Zuerst .\scripts\setup.ps1 ausführen."
}

& .\.venv\Scripts\python.exe -m pytest --cov=maf_lab --cov-report=term-missing
