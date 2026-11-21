# Local Setup Guide: BW Migration Studio

## 1. Prerequisites
- **Node.js**: v20.18+ LTS
- **Python**: 3.10+ (for test automation and discovery parser scripts)
- **PowerShell**: 7.x or Windows PowerShell 5.1

## 2. Step-by-Step Setup
1. Open PowerShell and navigate to the studio directory:
   ```powershell
   cd C:\Users\samarth\BW-hanamorph\BW_Migration_Studio
   ```
2. Verify system prerequisites:
   ```powershell
   powershell -File scripts\check-environment.ps1
   ```
3. Initialize the local database:
   ```powershell
   python bw-studio\database\init_db.py
   ```
4. Run the automated test suite:
   ```powershell
   powershell -File scripts\run-tests.ps1
   ```
5. Launch the local Studio server:
   ```powershell
   powershell -File scripts\start-local.ps1
   ```
