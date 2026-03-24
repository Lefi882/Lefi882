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

echo [1/4] Kontroluji Python launcher...
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

echo [2/4] Kontroluji soubory...
if not exist "final_ace_app.py" (
  echo [CHYBA] Nenasel jsem final_ace_app.py ve slozce:
  echo %CD%
  goto :END
)
if not exist "tennisratio_api_client.py" (
  echo [CHYBA] Nenasel jsem tennisratio_api_client.py ve slozce:
  echo %CD%
  goto :END
)

echo [3/4] Kontroluji konfliktni znacky a syntax Pythonu...
findstr /N /R /C:"^<<<<<<<" /C:"^=======" /C:"^>>>>>>>" tennisratio_api_client.py final_ace_app.py >nul
if not errorlevel 1 (
  echo [CHYBA] V kodu jsou konfliktni merge znacky (<<<<<<<, =======, >>>>>>>).
  echo Otevri soubor a odstran konflikt, nebo stahni cistou verzi repozitare.
  echo Tip: zkus aktualizovat repozitar znovu (git pull / nova kopie slozky).
  goto :END
)

%PY_CMD% -m py_compile tennisratio_api_client.py final_ace_app.py >nul 2>&1
if errorlevel 1 (
  echo [CHYBA] Python soubory obsahuji syntaktickou chybu.
  echo Spust detail: %PY_CMD% -m py_compile tennisratio_api_client.py final_ace_app.py
  goto :END
)

echo [4/4] Spoustim klikaci appku...
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
