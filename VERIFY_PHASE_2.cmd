@echo off
setlocal
cd /d "%~dp0"
echo === Kazi Sasa PS_2 - Phase 2 verification ===
py scriptsalidate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
if errorlevel 1 goto fail
py scriptserify_phase2.py
if errorlevel 1 goto fail
echo.
echo Phase 2 verification passed.
pause
exit /b 0
:fail
echo.
echo Phase 2 verification failed.
pause
exit /b 1
