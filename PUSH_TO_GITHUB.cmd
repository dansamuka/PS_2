@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM ============================================================
REM Kazi Sasa Public Sector Viewer - Update Existing GitHub Repo
REM Target repo: https://github.com/dansamuka/PS_2.git
REM This script DOES NOT create a fresh repository.
REM It validates the feed, clones/pulls the existing repo, copies this package
REM into that repo, commits the changes, and pushes to main.
REM ============================================================

echo ============================================================
echo Kazi Sasa Public Sector Viewer - Update Existing Repo
echo ============================================================
echo.

set DEFAULT_REMOTE=https://github.com/dansamuka/PS_2.git
set DEFAULT_BRANCH=main
set DEFAULT_COMMIT=Implement Phase 3 central government collectors

set /p REMOTE_URL=Existing GitHub repo URL [%DEFAULT_REMOTE%]: 
if "%REMOTE_URL%"=="" set REMOTE_URL=%DEFAULT_REMOTE%

set /p BRANCH=Branch [%DEFAULT_BRANCH%]: 
if "%BRANCH%"=="" set BRANCH=%DEFAULT_BRANCH%

set /p COMMIT_MSG=Commit message [%DEFAULT_COMMIT%]: 
if "%COMMIT_MSG%"=="" set COMMIT_MSG=%DEFAULT_COMMIT%

echo.
echo Target: %REMOTE_URL%
echo Branch: %BRANCH%
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: git is not installed or not on PATH.
  echo Install Git for Windows, then run this file again.
  pause
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python is not installed or not on PATH.
  echo Install Python 3, then run this file again.
  pause
  exit /b 1
)

if not exist "scripts\validate_public_sector_feed.py" (
  echo ERROR: scripts\validate_public_sector_feed.py not found.
  echo Run this script from the project root folder.
  pause
  exit /b 1
)

if not exist "data\public_sector_feed.json" (
  echo ERROR: data\public_sector_feed.json not found.
  pause
  exit /b 1
)

echo [1/5] Validating feed and Phase 3 scope...
python scripts\validate_public_sector_feed.py data\public_sector_feed.json --registry data\source_registry.json
if errorlevel 1 (
  echo ERROR: Feed validation failed. Fix errors before pushing.
  pause
  exit /b 1
)
python scripts\verify_phase3.py
if errorlevel 1 (
  echo ERROR: Phase 3 scope verification failed. Fix errors before pushing.
  pause
  exit /b 1
)

echo.
echo [2/5] Preparing clean update worktree...
set WORK_ROOT=%TEMP%\kazi_sasa_ps2_push
set WORK_REPO=%WORK_ROOT%\PS_2

if exist "%WORK_ROOT%" rmdir /S /Q "%WORK_ROOT%"
mkdir "%WORK_ROOT%" >nul 2>nul

echo Cloning existing repo...
git clone --branch "%BRANCH%" "%REMOTE_URL%" "%WORK_REPO%"
if errorlevel 1 (
  echo ERROR: Could not clone %REMOTE_URL% branch %BRANCH%.
  echo Check that the repo exists, you have access, and Git credentials are configured.
  pause
  exit /b 1
)

echo.
echo [3/5] Copying current package into existing repo...
REM Mirror files into the cloned repo while preserving the cloned .git folder.
REM Exclude local git folders, temporary push worktrees, caches and OS/editor noise.
robocopy "%CD%" "%WORK_REPO%" /MIR ^
  /XD ".git" ".push_worktree" ".gradle" "build" "node_modules" "__pycache__" ^
  /XF ".DS_Store" "Thumbs.db" "*.tmp" "*.log"

REM Robocopy returns 0-7 for success/no-op/copy differences; 8+ is a real error.
if %ERRORLEVEL% GEQ 8 (
  echo ERROR: File copy failed with robocopy exit code %ERRORLEVEL%.
  pause
  exit /b 1
)

echo.
echo [4/5] Committing changes...
cd /d "%WORK_REPO%"

git status --short

git add .
git diff --cached --quiet
if not errorlevel 1 (
  echo No changes to commit. Existing repo is already up to date.
) else (
  git commit -m "%COMMIT_MSG%"
  if errorlevel 1 (
    echo ERROR: git commit failed.
    pause
    exit /b 1
  )
)

echo.
echo [5/5] Pushing to existing repo...
git push origin "%BRANCH%"
if errorlevel 1 (
  echo ERROR: git push failed.
  echo You may need to authenticate GitHub, pull latest changes, or resolve conflicts.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo UPDATE SUCCESSFUL
echo ============================================================
echo Existing repo updated:
echo   %REMOTE_URL%
echo.
echo GitHub Pages URL is likely:
echo   https://dansamuka.github.io/PS_2/
echo.
echo Raw feed URL is likely:
echo   https://raw.githubusercontent.com/dansamuka/PS_2/%BRANCH%/data/public_sector_feed.json
echo.
echo Note: your screenshot shows PS_2 is PUBLIC. Do not put private notes,
echo private CVs, or sensitive data in this repo while it remains public.
echo.
pause
