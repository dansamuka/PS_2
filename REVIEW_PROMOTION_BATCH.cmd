@echo off
setlocal
cd /d "%~dp0"
echo === Build Phase 3E manual review batch ===
python scripts\review_batch.py --limit 25
if errorlevel 1 (
  echo Failed to build manual review batch.
  pause
  exit /b 1
)
echo.
echo Review files created/updated:
echo   data\manual_review_batch_1.json
echo   data\manual_review_batch_1.csv
echo   data\manual_review_batch_1.md
echo.
echo After human review, copy approved records into data\reviewed_promotions.json,
echo then run: python scripts\refresh_public_sector_feed.py
pause
