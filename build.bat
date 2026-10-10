@echo off
rem keep the data of an older build that stored it next to the exe
if exist dist\spoty-you\spoty.db if not exist "%APPDATA%\spoty-you\spoty.db" (
    mkdir "%APPDATA%\spoty-you"
    for %%f in (.env .cache spoty.db headers_auth.json oauth.json playlist_id.txt) do (
        if exist dist\spoty-you\%%f copy dist\spoty-you\%%f "%APPDATA%\spoty-you\"
    )
)
pip install pyinstaller
python -m PyInstaller --noconfirm --windowed --name spoty-you --icon static\icon.ico --add-data "static;static" --collect-data ytmusicapi app.py
echo.
echo Done. The app is in dist\spoty-you\spoty-you.exe
echo Its data (keys, logins, track list) is in %APPDATA%\spoty-you
