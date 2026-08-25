@echo off
cd /d "%~dp0"

where pythonw.exe >nul 2>nul
if not errorlevel 1 goto :use_pythonw
goto :use_python

:use_pythonw
start "" pythonw.exe app.py
exit /b 0

:use_python
echo 未找到 pythonw，改用 python 启动（将显示命令行窗口）...
python app.py
if errorlevel 1 (
    echo.
    echo 启动失败，请确认已安装 Python 3.8+ 和 requests 库：
    echo 运行 pip install requests 安装依赖
    pause
)