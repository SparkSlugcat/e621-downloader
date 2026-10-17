@echo off
cd /d "%~dp0"

where pythonw.exe >nul 2>nul
if not errorlevel 1 goto :use_pythonw
goto :use_python

:use_pythonw
start "" pythonw.exe app.py
exit /b 0

:use_python
echo [WARN] pythonw.exe not found in PATH, falling back to python (a console window will appear)...
python app.py
if errorlevel 1 (
    echo.
    echo [FAIL] python exited with an error. Make sure you have installed Python 3.8+ and the "requests" library:
    echo Run: pip install requests to install the dependency
    pause
)