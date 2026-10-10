@echo off
pip install pyinstaller
python -m PyInstaller --noconfirm --windowed --name spoty-you --add-data "static;static" --collect-data ytmusicapi app.py
echo.
echo Done. The app is in dist\spoty-you\spoty-you.exe
