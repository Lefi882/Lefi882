@echo off
setlocal
cd /d "%~dp0"

echo ======================================
echo LEFI Odds - START HERE
echo ======================================
echo.
echo 1) Full pipeline:          start_pipeline.bat
echo 2) One snapshot:           start_snapshot.bat
echo 3) Valuebet concrete demo: start_valuebet_demo.bat
echo.
choice /c 123 /n /m "Select [1/2/3]: "
if errorlevel 3 call start_valuebet_demo.bat & exit /b %errorlevel%
if errorlevel 2 call start_snapshot.bat & exit /b %errorlevel%
if errorlevel 1 call start_pipeline.bat & exit /b %errorlevel%
