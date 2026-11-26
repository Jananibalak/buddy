@echo off
REM ============================================================
REM  Builds Kutty.exe  (double-click this file)
REM  Result: dist\Kutty\Kutty.exe  + her characters + your settings
REM ============================================================
cd /d "%~dp0"

echo [1/3] Installing PyInstaller (only the first time)...
py -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 goto failed

echo [2/3] Building Kutty.exe (takes 1-3 minutes)...
py -m PyInstaller --noconfirm --clean --windowed --name Kutty --icon kutty.ico ^
   --exclude-module tkinter kutty.py
if errorlevel 1 goto failed

echo [3/3] Copying characters and settings next to Kutty.exe...
xcopy /E /I /Y /Q assets "dist\Kutty\assets" >nul
if exist characters xcopy /E /I /Y /Q characters "dist\Kutty\characters" >nul
if exist settings.json copy /Y settings.json "dist\Kutty\settings.json" >nul

echo.
echo Done!  Your app:  %~dp0dist\Kutty\Kutty.exe
echo Move the whole "Kutty" folder wherever you like (keep everything inside it together).
explorer "dist\Kutty"
pause
exit /b 0

:failed
echo.
echo Build failed - scroll up for the red error, or send a screenshot.
pause
exit /b 1
