@echo off
setlocal
chcp 65001 >nul

echo ======================================
echo  ODHAD ES - LEFI882 (WTA/ATP)
echo ======================================
echo.

echo [1/4] Kontroluji Python...
py --version >nul 2>&1
if errorlevel 1 (
  echo [CHYBA] Python ^(py launcher^) neni nainstalovany nebo neni v PATH.
  echo Nainstaluj Python z https://www.python.org/downloads/
  goto :END
)

echo [2/4] Prepinam do slozky se skriptem...
pushd "%~dp0" >nul 2>&1
if errorlevel 1 (
  echo [CHYBA] Nepodarilo se prejit do slozky skriptu.
  goto :END
)

if not exist "tournament_ace_app.py" (
  echo [CHYBA] Nenasel jsem tournament_ace_app.py v tehle slozce:
  echo %CD%
  echo Ujisti se, ze SPUSTIT_ESA.bat je ve stejne slozce jako Python soubory.
  goto :END
)

echo [3/4] Vyber rezim
echo 1^) WTA ^(Merida / Guadalajara^)
echo 2^) ATP ^(Dubai / Acapulco / Los Cabos ...^)
set /p MODE=Vyber 1 nebo 2 a stiskni Enter: 

echo.
echo [4/4] Spoustim vypocet...
if "%MODE%"=="1" (
  py tournament_ace_app.py --csv-files sample_wta_matches.csv
) else (
  py tournament_ace_app.py --csv-files sample_atp_matches.csv
)

:END
echo.
echo Hotovo. Zmackni libovolnou klavesu pro zavreni.
pause >nul
endlocal
