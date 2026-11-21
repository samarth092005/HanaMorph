Write-Host "Stopping Studio local server on port 4004..." -ForegroundColor Cyan
$p = Get-NetTCPConnection -LocalPort 4004 -ErrorAction SilentlyContinue
if ($p) {
    Stop-Process -Id $p.OwningProcess -Force
    Write-Host "Process $($p.OwningProcess) terminated successfully." -ForegroundColor Green
} else {
    Write-Host "No process listening on port 4004." -ForegroundColor Yellow
}
