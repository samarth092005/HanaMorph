Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  HanaMorph BW Migration Studio - Environment Check" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$allPass = $true

# Check Git
if (Get-Command git -ErrorAction SilentlyContinue) {
    $v = (git --version)
    Write-Host "[PASS] Git: $v" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Git not found on PATH" -ForegroundColor Red
    $allPass = $false
}

# Check Node
if (Get-Command node -ErrorAction SilentlyContinue) {
    $v = (node --version)
    Write-Host "[PASS] Node.js: $v" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Node.js not found on PATH" -ForegroundColor Red
    $allPass = $false
}

# Check Python
if (Get-Command python -ErrorAction SilentlyContinue) {
    $v = (python --version)
    Write-Host "[PASS] Python: $v" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Python not found on PATH" -ForegroundColor Red
    $allPass = $false
}

# Check SQLite Database
$dbPath = "bw-studio/database/bw_studio.sqlite"
if (Test-Path $dbPath) {
    Write-Host "[PASS] Local SQLite DB exists ($dbPath)" -ForegroundColor Green
} else {
    Write-Host "[WARN] Local SQLite DB not initialized. Run init_db.py first." -ForegroundColor Yellow
}

Write-Host "--------------------------------------------------" -ForegroundColor Cyan
if ($allPass) {
    Write-Host "Environment check passed. Ready for local execution." -ForegroundColor Green
} else {
    Write-Host "Environment check encountered missing dependencies." -ForegroundColor Red
}
