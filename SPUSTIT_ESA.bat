@echo off
setlocal
chcp 65001 >nul

REM Relaunch in persistent console so the window never closes immediately.
if /I not "%~1"=="--hold" (
  start "FINAL ACE APP" cmd /k ""%~f0" --hold"
  exit /b
)

title FINAL ACE APP - LEFI882

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ======================================
echo  FINAL ACE APP - LEFI882
echo ======================================
echo.

echo [1/3] Kontroluji Python launcher (py)...
where py >nul 2>&1
if errorlevel 1 (
  echo [INFO] py launcher neni dostupny, zkousim python...
  where python >nul 2>&1
  if errorlevel 1 (
    echo [CHYBA] Neni dostupny ani 'py' ani 'python'.
    echo Nainstaluj Python z https://www.python.org/downloads/
    goto :END
  )
  set "PY_CMD=python"
) else (
  set "PY_CMD=py"
)

echo [2/3] Kontroluji soubory...
if not exist "final_ace_app.py" (
  echo [CHYBA] Nenasel jsem final_ace_app.py ve slozce:
  echo %CD%
  goto :END
)

echo [3/3] Spoustim klikaci appku...
%PY_CMD% final_ace_app.py
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [CHYBA] Aplikace skoncila s kodem %EXIT_CODE%.
  echo Pokud se okno appky neotevre, posli prosim screenshot teto chyby.
) else (
  echo.
  echo [OK] Aplikace byla ukoncena korektne.
)

:END
echo.
echo Hotovo. Toto okno zustane otevrene. Zmackni libovolnou klavesu pro zavreni.
pause >nul
endlocal
