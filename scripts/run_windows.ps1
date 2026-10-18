# PowerShell alternative to run_windows.bat
#   If scripts are blocked:  Set-ExecutionPolicy -Scope Process Bypass
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment and installing dependencies..."
    py -3 -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
}
& .\.venv\Scripts\python.exe main.py
