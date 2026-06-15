$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .\.venv\Scripts\maf-lab.exe)) {
    throw "Virtuelle Umgebung fehlt. Zuerst .\scripts\setup.ps1 ausführen."
}

& .\.venv\Scripts\maf-lab.exe
