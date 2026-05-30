@echo off
REM Build a standalone Windows BOZO Ball (3D / pywebview) executable.
REM Requires: a .venv with deps installed, and the Microsoft Edge WebView2
REM runtime (preinstalled on Windows 10/11).
setlocal
cd /d "%~dp0"

set APP_NAME=BOZO_BALL
set VENV_PY=.venv\Scripts\python.exe

if not exist "%VENV_PY%" (
    echo error: %VENV_PY% not found - create the venv first
    exit /b 1
)

"%VENV_PY%" -m pip show pyinstaller >nul 2>&1 || "%VENV_PY%" -m pip install --quiet pyinstaller

rmdir /s /q build dist 2>nul
del /q "%APP_NAME%.spec" 2>nul

echo Building %APP_NAME%.exe ...
"%VENV_PY%" -m PyInstaller ^
    --name "%APP_NAME%" ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --add-data "kelly_ball/web;kelly_ball/web" ^
    --collect-submodules kelly_ball ^
    --collect-all webview ^
    bozo_ball.py

if not exist "dist\%APP_NAME%" (
    echo error: PyInstaller produced no build
    exit /b 1
)

echo Done. See dist\%APP_NAME%\%APP_NAME%.exe
endlocal
