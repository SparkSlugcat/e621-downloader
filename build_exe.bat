@echo off
cd /d "%~dp0"
echo ============================================
echo   E621 Downloader - Build standalone exe
echo ============================================
echo Installing PyInstaller (skipped if already installed)...
pip install pyinstaller

echo Building the standalone exe (1-2 minutes)...
pyinstaller -F -w -n "E621Downloader" --icon assets\icon.ico --collect-all requests app.py

echo.
echo Build complete!
echo Output: dist\E621Downloader.exe
echo Icon: assets\icon.ico. The exe runs standalone on any Windows machine.
pause