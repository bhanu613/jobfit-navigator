$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python) -or -not (Test-Path 'data\navigator_local.db')) {
 & (Join-Path $PSScriptRoot 'Setup-Local.ps1')
 if (-not $?) { throw 'Setup failed.' }
}
$env:JOBFIT_MODE='local'
$env:JOBFIT_DB=Join-Path $PSScriptRoot 'data\navigator_local.db'
& $python launch.py
if ($LASTEXITCODE -ne 0) { throw 'Application exited with an error.' }
