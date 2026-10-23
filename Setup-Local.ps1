$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
 $base=$null
 foreach ($v in @('3.12','3.11')) {
  if (Get-Command py -ErrorAction SilentlyContinue) {
   try { $candidate=& py "-$v" -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $candidate) { $base=($candidate | Select-Object -Last 1);break }
   } catch {}
  }
 }
 if (-not $base) { throw 'Install Python 3.11 or 3.12 from python.org, reopen PowerShell, and retry.' }
 & $base -m venv .venv
 if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
$valid=& $python -c "import sys; print(sys.version_info[:2] in ((3,11),(3,12)))"
if ($LASTEXITCODE -ne 0 -or $valid -ne 'True') { throw 'Virtual environment requires Python 3.11/3.12.' }
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not (Test-Path 'data\navigator_local.db')) {
 & $python tools/import_workspace.py
 if ($LASTEXITCODE -ne 0) { throw 'Database copy failed.' }
}

Write-Host 'Setup complete. Open Start-Local.cmd.'
