@echo off
REM Creates a virtual environment and installs SHAHER's dependencies (needs internet ONCE).
cd /d "%~dp0\.."
where py >nul 2>nul
if %errorlevel%==0 ( set PY=py -3 ) else ( set PY=python )
%PY% --version || (echo Python was not found. Install Python 3.11 or 3.12 from python.org, tick "Add to PATH", then run this again. & pause & exit /b 1)
if not exist .venv ( %PY% -m venv .venv || (echo Could not create the virtual environment. & pause & exit /b 1) )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt || (echo Dependency installation failed. Check your internet connection. & pause & exit /b 1)
echo.
echo Setup finished. Start the app with scripts\run_windows.bat
pause
