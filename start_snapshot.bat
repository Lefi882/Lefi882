@echo off
setlocal
cd /d "%~dp0"

echo ======================================
echo LEFI Odds - One snapshot (double-click)
echo ======================================

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 main.py --iterations 1
) else (
  python main.py --iterations 1
)

set EXIT_CODE=%errorlevel%
echo.
if not "%EXIT_CODE%"=="0" (
  echo Snapshot FAILED with exit code %EXIT_CODE%.
) else (
  echo Snapshot finished successfully.
)

echo.
pause
exit /b %EXIT_CODE%
