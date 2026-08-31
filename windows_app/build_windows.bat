@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv-build
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python make_icon.py
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SaikoLicenceControl --icon assets\app-icon.ico --add-data "assets\app-icon.ico;assets" app.py
echo.
echo Windows application created at:
echo %CD%\dist\SaikoLicenceControl.exe
endlocal
