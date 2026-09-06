@echo off
REM Build script for bootstrap_google.exe using PyInstaller
REM Assumes Python virtual environment is activated

REM Install PyInstaller if not present
pip install pyinstaller

REM Build the executable
pyinstaller --onefile --windowed --name bootstrap-google bootstrap_google.py

REM Copy to dist folder
echo Build completed. Executable is in dist/bootstrap-google.exe