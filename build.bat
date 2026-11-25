@echo off
REM ============================================================
REM  Builds Buddy.exe  (double-click this file)
REM  Result: dist\Buddy\Buddy.exe  + her characters + your settings
REM ============================================================
cd /d "%~dp0"

echo [1/3] Installing PyInstaller (only the first time)...
py -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 goto failed

echo [2/3] Building Buddy.exe (takes 1-3 minutes)...
py -m PyInstaller --noconfirm --clean --windowed --name Buddy --icon buddy.ico ^
   --exclude-module tkinter buddy.py
if errorlevel 1 goto failed

echo [3/3] Copying characters and settings next to Buddy.exe...
xcopy /E /I /Y /Q assets "dist\Buddy\assets" >nul
if exist characters xcopy /E /I /Y /Q characters "dist\Buddy\characters" >nul
if exist settings.json copy /Y settings.json "dist\Buddy\settings.json" >nul

echo.
echo Done!  Your app:  %~dp0dist\Buddy\Buddy.exe
echo Move the whole "Buddy" folder wherever you like (keep everything inside it together).
explorer "dist\Buddy"
pause
exit /b 0

:failed
echo.
echo Build failed - scroll up for the red error, or send a screenshot.
pause
exit /b 1
