@echo off
REM Build script for Windows

echo Building Ænglisc Toolkit for Windows...

REM Check if virtual environment is activated
if "%VIRTUAL_ENV%"=="" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Install PyInstaller if not already installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

REM Build the application
echo Building application...
pyinstaller oe_annotator.spec

REM Check if build succeeded
if exist "dist\oe_annotator.exe" (
    echo Application built successfully!
    echo Location: dist\oe_annotator.exe
) else (
    echo Build failed - oe_annotator.exe not found
    exit /b 1
)

