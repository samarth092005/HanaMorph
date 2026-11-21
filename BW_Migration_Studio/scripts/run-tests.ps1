Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Running HanaMorph BW Migration Studio Test Suite " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

python bw-studio/tests/run_all_tests.py
