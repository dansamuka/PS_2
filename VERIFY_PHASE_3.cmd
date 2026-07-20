@echo off
setlocal
cd /d "%~dp0"
echo === Kazi Sasa PS_2 - Phase 3 verification ===
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set PY=py
) else (
  set PY=python
)
%PY% scripts\validate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
if errorlevel 1 goto fail
%PY% scripts\verify_phase3.py
if errorlevel 1 goto fail
echo.
echo Phase 3 verification passed.
pause
exit /b 0
:fail
echo.
echo Phase 3 verification failed.
pause
exit /b 1
