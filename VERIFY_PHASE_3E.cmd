@echo off
setlocal
cd /d "%~dp0"
echo === Kazi Sasa PS_2 - Phase 3E verification ===
echo Checking required Python packages...
python -c "import bs4, requests" >nul 2>nul
if errorlevel 1 (
  echo Required packages are missing. Installing requirements now...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo ERROR: Could not install required Python packages.
    echo Try running manually: python -m pip install -r requirements.txt
    goto fail
  )
)

echo.
python scripts\validate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
if errorlevel 1 goto fail
python scripts\verify_phase3.py
if errorlevel 1 goto fail
python scripts\verify_phase3b.py
if errorlevel 1 goto fail
python scripts\verify_phase3c.py
if errorlevel 1 goto fail
python scripts\verify_phase3d.py
if errorlevel 1 goto fail
python scripts\verify_phase3e.py
if errorlevel 1 goto fail

echo.
echo Checking optional parser tests...
python -c "import pytest" >nul 2>nul
if errorlevel 1 (
  echo NOTE: pytest is not installed, so optional parser tests were skipped.
  echo       Core Phase 3E validation passed. To run tests later:
  echo       python -m pip install -r requirements.txt
  echo       python -m pytest -q scripts\tests
) else (
  python -m pytest -q scripts\tests
  if errorlevel 1 goto fail
)

echo.
echo Phase 3E verification passed.
pause
exit /b 0
:fail
echo.
echo Phase 3E verification failed.
pause
exit /b 1
