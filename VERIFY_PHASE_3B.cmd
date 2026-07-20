@echo off
setlocal
cd /d "%~dp0"
echo === Kazi Sasa PS_2 - Phase 3B verification ===
python scripts\validate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
if errorlevel 1 goto fail
python scripts\verify_phase3.py
if errorlevel 1 goto fail
python scripts\verify_phase3b.py
if errorlevel 1 goto fail

echo.
echo Checking optional parser tests...
python -c "import pytest" >nul 2>nul
if errorlevel 1 (
  echo NOTE: pytest is not installed, so optional parser tests were skipped.
  echo       Core Phase 3B validation passed. To run parser tests later, use:
  echo       python -m pip install -r requirements.txt
  echo       python -m pytest -q scripts\tests
) else (
  python -m pytest -q scripts\tests
  if errorlevel 1 goto fail
)

echo.
echo Phase 3B verification passed.
pause
exit /b 0
:fail
echo.
echo Phase 3B verification failed.
pause
exit /b 1
