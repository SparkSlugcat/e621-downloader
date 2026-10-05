@echo off
cd /d "%~dp0"
echo ============================================
echo   E621 下载器 - 打包成独立 exe
echo ============================================
echo 正在安装 PyInstaller（已安装会自动跳过）...
pip install pyinstaller

echo 开始打包（约需几分钟）...
pyinstaller -F -w -n "E621Downloader" --icon assets\icon.ico --collect-all requests app.py

echo.
echo 打包完成！
echo 生成的 exe 文件在： dist\E621Downloader.exe
echo 图标使用 assets\icon.ico，复制 exe 到任何 Windows 电脑即可使用。
pause