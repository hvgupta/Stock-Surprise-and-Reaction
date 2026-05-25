<#
run-dev.ps1 — start backend (uvicorn) and frontend (npm) on Windows (PowerShell)
Usage: Open PowerShell in the `oxbow` folder and run `.
run-dev.ps1`
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

# Prefer 'uv' CLI per README
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Found 'uv' CLI — using it to run backend"
    $backendProc = Start-Process -FilePath uv -ArgumentList 'run', 'fastapi', 'run', 'app.py' -PassThru
    Write-Host "Backend started via uv (pid: $($backendProc.Id))"
} else {
    # ensure venv exists
    $venvDir = Join-Path $scriptDir 'backend' | Split-Path -Parent
    if (-not (Test-Path -Path (Join-Path (Join-Path $scriptDir 'backend') '.venv'))) {
        Write-Host "Creating virtualenv at backend\.venv"
        python -m venv .venv
    }

    $pythonExe = Join-Path (Join-Path $scriptDir 'backend') '.venv\Scripts\python.exe'
    if (-not (Test-Path $pythonExe)) { $pythonExe = 'python' }

    # ensure uvicorn installed in venv
    try {
        & $pythonExe -c "import uvicorn" 2>$null
    } catch {
        Write-Host "Installing uvicorn into virtualenv..."
        & $pythonExe -m pip install --upgrade pip
        & $pythonExe -m pip install 'uvicorn[standard]'
    }

    $backendProc = Start-Process -FilePath $pythonExe -ArgumentList '-m', 'uvicorn', 'backend.app:app', '--reload', '--port', '8000' -PassThru
    Write-Host "Backend started (pid: $($backendProc.Id))"
}

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
