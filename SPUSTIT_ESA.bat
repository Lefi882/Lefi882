@echo off
setlocal
chcp 65001 >nul

title FINAL ACE APP - LEFI882

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ======================================
echo  FINAL ACE APP - LEFI882
echo ======================================
echo.

echo [1/3] Kontroluji Python launcher...
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

echo.
if not "%EXIT_CODE%"=="0" (
  echo [CHYBA] Aplikace skoncila s kodem %EXIT_CODE%.
  echo Posli screenshot teto chyby a opravime to.
) else (
  echo [OK] Aplikace byla ukoncena korektne.
)

:END
echo.
echo Hotovo. Toto okno zustane otevrene. Zmackni libovolnou klavesu pro zavreni.
pause >nul
endlocal
