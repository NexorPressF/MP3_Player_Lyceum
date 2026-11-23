@echo off
pip install pyinstaller
pyinstaller --noconsole --onefile --name MP3Player --icon assets\app_icon.ico ^
    --add-data "ui;ui" --add-data "assets;assets" main.py
echo.
echo Done: dist\MP3Player.exe  (database and settings appear next to it, in the data folder)
pause
