@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=.venv-build\Scripts\python.exe"

if not exist "%PYTHON%" (
    py -3 -m venv .venv-build
    if errorlevel 1 goto failure
)

"%PYTHON%" -m pip install -r requirements-build.txt
if errorlevel 1 goto failure

"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name ShipmentPolicyProcessor main.py
if errorlevel 1 goto failure

echo.
echo Build complete: dist\ShipmentPolicyProcessor.exe
exit /b 0

:failure
echo.
echo Build failed. Review the error messages above.
exit /b 1
