# HireSense AI — Start both servers with one command
# Usage: powershell -ExecutionPolicy Bypass -File start.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "  HireSense AI — Starting servers..." -ForegroundColor Cyan
Write-Host ""

# ── Backend ──────────────────────────────────────────────────────────────────
$backendDir = Join-Path $root "backend"
$uvicorn    = Join-Path $backendDir ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $uvicorn)) {
    Write-Host "  [ERROR] .venv not found. Run:" -ForegroundColor Red
    Write-Host "    cd backend" -ForegroundColor Yellow
    Write-Host "    python -m venv .venv" -ForegroundColor Yellow
    Write-Host "    .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendDir'; Write-Host '  [Backend] Starting on http://127.0.0.1:8000' -ForegroundColor Green; .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000"
) -WindowStyle Normal

# ── Frontend ─────────────────────────────────────────────────────────────────
$frontendDir = Join-Path $root "frontend"

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; Write-Host '  [Frontend] Starting on http://127.0.0.1:3000' -ForegroundColor Green; npm run dev"
) -WindowStyle Normal

Write-Host "  Backend  → http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  Frontend → http://127.0.0.1:3000" -ForegroundColor Green
Write-Host ""
Write-Host "  Both servers are starting in separate windows." -ForegroundColor Cyan
Write-Host "  Open http://127.0.0.1:3000 in your browser once both are ready." -ForegroundColor Cyan
Write-Host ""
