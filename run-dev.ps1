<#
run-dev.ps1 - start backend and frontend on Windows (PowerShell)
#>

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendDir = Join-Path $scriptDir 'backend'
$frontendDir = Join-Path $scriptDir 'frontend'

Set-Location $scriptDir

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found in PATH. Install Python and ensure 'python' is available."
    exit 1
}

Write-Host "Starting backend..."
Set-Location $backendDir

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Found 'uv' CLI - using it to run backend"
    $backendCommand = { uv run fastapi run backend\app.py }
} else {
    $venvDir = Join-Path $backendDir '.venv'
    $pythonExe = Join-Path $venvDir 'Scripts\python.exe'

    if (-not (Test-Path $pythonExe)) {
        Write-Host "Creating virtualenv at backend\.venv"
        & python -m venv $venvDir
    }

    if (-not (Test-Path $pythonExe)) {
        $pythonExe = 'python'
    }

    # If we created (or already have) a backend virtualenv, install project dependencies into it
    if (Test-Path $venvDir) {
        Write-Host "Installing project dependencies into backend virtualenv..."
        & $pythonExe -m pip install --upgrade pip
        & $pythonExe -m pip install -e $scriptDir
    }

    try {
        & $pythonExe -c 'import uvicorn' 2>$null
    } catch {
        Write-Host "Installing uvicorn into virtualenv..."
        & $pythonExe -m pip install --upgrade pip
        & $pythonExe -m pip install 'uvicorn[standard]'
    }

    try {
        & $pythonExe -c 'import fastapi' 2>$null
    } catch {
        Write-Host "Installing fastapi into virtualenv..."
        & $pythonExe -m pip install 'fastapi[standard]'
    }

    $backendCommand = { & $pythonExe -m uvicorn backend.app:app --reload --port 8000 }
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm not found in PATH. Install Node.js and npm."
    exit 1
}

Set-Location $frontendDir

Write-Host "Starting frontend..."
$npmExe = (Get-Command npm.cmd).Source
$frontendProc = Start-Process -FilePath $npmExe -ArgumentList @('run', 'dev') -WorkingDirectory $frontendDir -PassThru
Write-Host "Frontend started (pid: $($frontendProc.Id))"

try {
    Write-Host "Starting backend in the foreground. Press Ctrl+C to stop."
    # Ensure the backend is started from the repository root so the `backend` package is importable
    Set-Location $scriptDir
    & $backendCommand
} finally {
    Write-Host "Stopping processes..."
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
}
