@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Installing dependencies...
py -m pip install --upgrade pip
py -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

echo [2/3] Building Windows application...
py -m PyInstaller --noconfirm --clean --windowed --name "AnastasiaDaysMysteryGame" --add-data "data;data" --add-data "assets;assets" main.py
if errorlevel 1 goto :error

echo [3/3] Build complete.
echo Executable: dist\AnastasiaDaysMysteryGame\AnastasiaDaysMysteryGame.exe
echo Copy the entire dist\AnastasiaDaysMysteryGame folder to the target PC.
pause
exit /b 0

:error
echo Build failed. Read the error above.
pause
exit /b 1
