# PowerShell Script to run the AstroAgent backend
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "            STARTING ASTROAGENT BACKEND" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$ActivatePath = Join-Path $ScriptDir "backend\venv\Scripts\Activate.ps1"

if (-not (Test-Path $ActivatePath)) {
    Write-Host "[ERROR] Virtual environment not found at: backend\venv\Scripts\Activate.ps1" -ForegroundColor Red
    Write-Host "Please ensure the venv is created in the backend folder." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Gray
& $ActivatePath

Write-Host "[INFO] Starting FastAPI server via Uvicorn..." -ForegroundColor Gray
python -m uvicorn backend.app.main:app --reload --port 8001
