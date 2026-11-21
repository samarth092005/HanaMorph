Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Starting HanaMorph BW Migration Studio (Local)   " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$port = 4004
Write-Host "Starting Studio server on http://localhost:$port..." -ForegroundColor Green
python bw-studio/backend/server.py
