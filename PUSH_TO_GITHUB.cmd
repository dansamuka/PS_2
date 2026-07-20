@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo Kazi Sasa Public Sector Viewer - Push to GitHub
echo ============================================================
echo.

set DEFAULT_REPO=kazi-sasa-public-sector-viewer
set /p REPO_NAME=Repo name [%DEFAULT_REPO%]: 
if "%REPO_NAME%"=="" set REPO_NAME=%DEFAULT_REPO%

where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: git is not installed or not on PATH.
  echo Install Git for Windows, then run this file again.
  pause
  exit /b 1
)

python scripts\validate_public_sector_feed.py data\public_sector_feed.json
if errorlevel 1 (
  echo ERROR: Feed validation failed. Fix errors before pushing.
  pause
  exit /b 1
)

if not exist .git (
  git init
  git branch -M main
)

git add .
git commit -m "Initial public-sector viewer with actual feed" 2>nul
if errorlevel 1 (
  echo No new local changes to commit, continuing...
)

where gh >nul 2>nul
if not errorlevel 1 (
  echo GitHub CLI found.
  gh repo view %REPO_NAME% >nul 2>nul
  if errorlevel 1 (
    echo Creating private GitHub repo: %REPO_NAME%
    gh repo create %REPO_NAME% --private --source=. --remote=origin --push
  ) else (
    echo Repo exists. Ensuring remote origin...
    git remote get-url origin >nul 2>nul
    if errorlevel 1 git remote add origin https://github.com/%USERNAME%/%REPO_NAME%.git
    git push -u origin main
  )
) else (
  echo.
  echo GitHub CLI not found. Manual fallback:
  echo 1. Create a PRIVATE GitHub repo named %REPO_NAME% in your browser.
  echo 2. Copy its HTTPS URL, for example:
  echo    https://github.com/YOUR_USERNAME/%REPO_NAME%.git
  echo.
  set /p REMOTE_URL=Paste remote URL, or press Enter to skip: 
  if not "!REMOTE_URL!"=="" (
    git remote remove origin >nul 2>nul
    git remote add origin !REMOTE_URL!
    git push -u origin main
  ) else (
    echo Skipped remote push. Local repo is ready.
  )
)

echo.
echo Done.
echo If using GitHub Pages, enable Pages from repo Settings ^> Pages.
echo Feed raw URL will usually be:
echo https://raw.githubusercontent.com/YOUR_USERNAME/%REPO_NAME%/main/public_sector_feed.json
echo.
pause
