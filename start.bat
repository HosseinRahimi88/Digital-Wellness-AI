@echo off
REM Digital Wellness AI - double-click this file to start the app.
REM
REM It runs run.py, which starts the API (the API also serves the web
REM pages) and opens your browser at the right address. Do NOT open the
REM frontend folder with a separate web server or by double-clicking an
REM .html file: those serve pages but cannot answer a sign-in, and you
REM get "501 Unsupported method ('POST')" the moment you log in.

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py run.py
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python run.py
    ) else (
        echo.
        echo   Python was not found on this computer.
        echo   Install Python 3.11 from https://www.python.org/downloads/
        echo   and tick "Add Python to PATH" during setup.
        echo.
    )
)

echo.
pause
