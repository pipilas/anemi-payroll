@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM  Build Stamhad Payroll — Windows (.exe)
REM  Run from the project root: build_windows.bat
REM ═══════════════════════════════════════════════════════════════════════════

set APP_NAME=StamhadPayroll
set VERSION=1.0.0

echo.
echo ══════════════════════════════════════════════════════════
echo   Building %APP_NAME% v%VERSION% for Windows
echo ══════════════════════════════════════════════════════════
echo.

REM ── Step 1: Install build dependencies ────────────────────────────────────
echo [1/3] Installing dependencies...
pip install pyinstaller reportlab requests flask --quiet

REM ── Step 2: Clean previous builds ─────────────────────────────────────────
echo [2/3] Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM ── Step 3: Build with PyInstaller ────────────────────────────────────────
echo [3/3] Building .exe with PyInstaller...
pyinstaller stamhad_payroll.spec --clean --noconfirm

if not exist "dist\%APP_NAME%.exe" (
    echo.
    echo ERROR: .exe was not created!
    pause
    exit /b 1
)

echo.
echo ══════════════════════════════════════════════════════════
echo   BUILD COMPLETE!
echo.
echo   .exe:  dist\%APP_NAME%.exe
echo ══════════════════════════════════════════════════════════
echo.
pause
