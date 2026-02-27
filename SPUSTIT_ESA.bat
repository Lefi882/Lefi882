@echo off
setlocal
chcp 65001 >nul

echo ======================================
echo  FINAL ACE APP - LEFI882
 echo ======================================

echo Kontroluji Python...
py --version >nul 2>&1
if errorlevel 1 (
  echo [CHYBA] Python (py launcher) neni nainstalovany.
  echo Nainstaluj Python z https://www.python.org/downloads/
  goto :END
)

pushd "%~dp0" >nul 2>&1
if errorlevel 1 (
  echo [CHYBA] Nepodarilo se prejit do slozky skriptu.
  goto :END
)

if not exist "final_ace_app.py" (
  echo [CHYBA] Nenasel jsem final_ace_app.py ve slozce:
  echo %CD%
  goto :END
)

echo Spoustim klikaci appku...
py final_ace_app.py

:END
echo.
echo Hotovo. Zmackni libovolnou klavesu pro zavreni.
pause >nul
endlocal
