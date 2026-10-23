$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Run Start-Local.ps1 first.' }
& $python -m pip install -r requirements-semantic.txt
if ($LASTEXITCODE -ne 0) { throw 'Semantic dependency installation failed.' }
Write-Host 'Restart the app. Model download/loading requires explicit consent.'
