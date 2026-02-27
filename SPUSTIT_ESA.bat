@echo off
setlocal
chcp 65001 >nul

echo ======================================
echo  FINAL ACE APP - LEFI882
 echo ======================================
chcp 65001 >nul

echo ======================================
echo  ODHAD ES - LEFI882 (WTA/ATP)
echo ======================================
echo.

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
  echo [CHYBA] Python (py launcher) neni nainstalovany nebo neni v PATH.
  echo Nainstaluj Python z https://www.python.org/downloads/
  pause
  exit /b 1
)

echo 1) WTA (Merida / Guadalajara)
echo 2) ATP (Dubai / Acapulco / Los Cabos ...)
set /p MODE=Vyber 1 nebo 2 a stiskni Enter: 

echo.
cd /d "C:\Users\David\Desktop\Lefi882-main"

if "%MODE%"=="1" (
  py tournament_ace_app.py --csv-files sample_wta_matches.csv
) else (
  py tournament_ace_app.py --csv-files sample_atp_matches.csv
)

echo.
echo Hotovo.
pause
