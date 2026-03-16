@echo off
setlocal
cd /d "%~dp0"

echo =============================================
echo LEFI Odds - Concrete value-bet demo (double-click)
echo =============================================

echo Running manual demo: Arsenal vs Chelsea...
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\valuebets_tipsport_betano.py --manual-demo --target tipsport --min-edge 1.0 --top 10
) else (
  python scripts\valuebets_tipsport_betano.py --manual-demo --target tipsport --min-edge 1.0 --top 10
)

set EXIT_CODE=%errorlevel%
echo.
if not "%EXIT_CODE%"=="0" (
  echo Demo FAILED with exit code %EXIT_CODE%.
) else (
  echo Demo finished successfully.
)

echo.
pause
exit /b %EXIT_CODE%
