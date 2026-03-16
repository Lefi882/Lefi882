@echo off
setlocal
cd /d "%~dp0"

echo ======================================
echo LEFI Odds - Full pipeline (double-click)
echo ======================================

after_python:
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\run_all.py --tipsport-sport all --tipsport-details --betano-all
) else (
  python scripts\run_all.py --tipsport-sport all --tipsport-details --betano-all
)

set EXIT_CODE=%errorlevel%
echo.
if not "%EXIT_CODE%"=="0" (
  echo Pipeline FAILED with exit code %EXIT_CODE%.
) else (
  echo Pipeline finished successfully.
)

echo.
pause
exit /b %EXIT_CODE%
