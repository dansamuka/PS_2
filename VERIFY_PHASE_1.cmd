@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo Kazi Sasa PS_2 - Phase 1 Verification
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    pause
    exit /b 1
  ) else (
    set PY=py
  )
) else (
  set PY=python
)

echo [1/2] Validating feed and registry...
%PY% scripts\validate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
if errorlevel 1 (
  echo ERROR: Feed validation failed.
  pause
  exit /b 1
)

echo.
echo [2/2] Running Phase 1 scope checks...
%PY% scripts\verify_phase1.py
if errorlevel 1 (
  echo ERROR: Phase 1 scope checks failed.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo PHASE 1 VERIFICATION PASSED
echo ============================================================
echo Ready to run PUSH_TO_GITHUB.cmd
pause
