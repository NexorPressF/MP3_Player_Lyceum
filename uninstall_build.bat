@echo off
cd /d "%~dp0"
echo This will delete: the build folder, the dist folder with MP3Player.exe, and MP3Player.spec.
echo Copy MP3Player.exe somewhere else first if you want to keep it.
choice /c YN /m "Continue"
if errorlevel 2 exit /b
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MP3Player.spec del /q MP3Player.spec
echo.
choice /c YN /m "Also remove PyInstaller from the virtual environment"
if errorlevel 2 goto done
set PY=python
if exist ".venv\Scripts\python.exe" set PY=".venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set PY="venv\Scripts\python.exe"
%PY% -m pip uninstall -y pyinstaller pyinstaller-hooks-contrib altgraph pefile pywin32-ctypes
:done
echo.
echo Done. The project folder is back to its state before the build.
pause
