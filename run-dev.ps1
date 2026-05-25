<#
run-dev.ps1 — start backend (uvicorn) and frontend (npm) on Windows (PowerShell)
Usage: Open PowerShell in the `oxbow` folder and run `.
un-dev.ps1`
#>

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

Write-Host "Starting backend..."
Set-Location (Join-Path $scriptDir 'backend')

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found in PATH. Install Python and ensure 'python' is available."
    exit 1
}

# Start uvicorn as a process
$backendProc = Start-Process -FilePath python -ArgumentList '-m', 'uvicorn', 'backend.app:app', '--reload', '--port', '8000' -PassThru
Write-Host "Backend started (pid: $($backendProc.Id))"

Set-Location (Join-Path $scriptDir 'frontend')
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm not found in PATH. Install Node.js and npm."
    Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "Starting frontend..."
$frontendProc = Start-Process -FilePath npm -ArgumentList 'run', 'dev' -PassThru
Write-Host "Frontend started (pid: $($frontendProc.Id))"

Write-Host "Both processes are running. Press Ctrl+C to stop."

try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Write-Host "Stopping processes..."
    if ($frontendProc -and -not $frontendProc.HasExited) { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue }
    if ($backendProc -and -not $backendProc.HasExited) { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue }
}
