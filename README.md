# Odhad pravděpodobnosti v tenise (výpočetní přístup)

Tento mini-projekt ukazuje jednoduchý, praktický framework na odhad pravděpodobnosti výhry v tenisovém zápase.

## Co sledovat (feature engineering)

- **Síla hráče na konkrétním povrchu** (nejlépe surface ELO).
- **Aktuální forma** (např. posledních 5–10 zápasů, váženě podle kvality soupeřů).
- **Únava / zatížení** (délka minulých zápasů, počet setů, cestování, back-to-back dny).
- **Servisní profil** (esa, % 1. servisu, body po 1./2. servisu).
- **Return profil soupeře** (% vyhraných return pointů, break conversion).
- **Kontext zápasu** (důležitost kola, tlak, typ turnaje).
- **Podmínky** (počasí, indoor/outdoor, rychlost kurtu).

## Jak to počítat

V souboru `tenis_probability_model.py` je transparentní model:

1. Spočte rozdíly hráč A vs hráč B ve featurách.
2. Každý rozdíl vynásobí vahou.
3. Sečte je do jednoho skóre.
4. Skóre převede přes logistickou funkci na pravděpodobnost 0–1.

To je výborný start. Jakmile budeš mít data, doporučení je:

- nahradit ručně zadané váhy tréninkem (logistická regrese, gradient boosting),
- použít **time-decay** (čerstvá data mají vyšší váhu),
- model průběžně kalibrovat (Brier score, reliability curve),
- netrénovat na „future leakage“ datech.

## Spuštění

```bash
python3 tenis_probability_model.py
```

Ukázkový výstup:

```text
P(Hráč A vyhraje) = 0.700
```

## Poznámka k přesnosti

Nejdůležitější je kvalita vstupních dat a validace na historických zápasech.
I jednoduchý model může být velmi použitelný, pokud má dobře navržené feature a pravidelnou rekalibraci.


## Interaktivní appka (2 hráči)

Pokud chceš zadat vlastní zápas ručně (hráč 1 vs hráč 2), spusť:

```bash
python3 tenis_app.py
```

Appka se tě zeptá na parametry obou hráčů a kontext zápasu,
a pak vrátí odhad v procentech pro oba hráče.


## Automatický režim (stahování dat + odhady)

Pokud nechceš ručně vyplňovat hráče a statistiky, použij automatický skript:

```bash
python3 auto_tennis_predictor.py "Novak Djokovic" "Carlos Alcaraz" --tour atp --surface Hard --years 2023 2024
```

Co skript udělá automaticky:
- stáhne historická data zápasů (ATP/WTA) z veřejného datasetu,
- spočítá pro oba hráče formu, povrchový rating, ace-rate, return a pressure index,
- vrátí odhad % výhry/prohry,
- vrátí odhad celkového počtu gamů,
- vrátí odhad es a dvojchyb pro oba hráče.

Pozn.: jde o modelový odhad (ne garance), přesnost roste s lepším feature engineeringem a kalibrací.

Pokud ti nejde stahování z internetu, můžeš dát lokální CSV:

```bash
python3 auto_tennis_predictor.py "Novak Djokovic" "Carlos Alcaraz" --surface Hard --csv-files sample_atp_matches.csv
```


### Ještě jednodušší použití (bez ELO vyplňování)

Spusť jen:

```bash
python3 auto_tennis_predictor.py --surface Hard --csv-files sample_atp_matches.csv
```

Aplikace se tě pak zeptá pouze na jména 2 hráčů.


## Odhad pouze počtu es (nová appka)

Pokud chceš pouze odhad es (bez dalších metrik), použij:

```bash
python3 ace_estimator.py --surface Hard --csv-files sample_atp_matches.csv
```

Skript se zeptá jen na 2 jména hráčů a vrátí odhad počtu es pro oba.

Můžeš také zadat jména rovnou:

```bash
python3 ace_estimator.py "Novak Djokovic" "Carlos Alcaraz" --surface Hard --csv-files sample_atp_matches.csv
```


## Backtest a doladění odhadu es (např. 50 zápasů)

Ano, jde to: můžeš vzít historické zápasy a model kalibrovat, aby byl blízko realitě.

```bash
python3 ace_backtest.py --csv-files atp_matches_2024.csv --surface Hard --tests 50
```

Skript:
- vezme náhodný vzorek zápasů (`--tests`, třeba 50),
- pro každý zápas použije jen data dostupná před zápasem,
- provede grid-search parametrů (váha server/return + surface multipliers),
- vypíše MAE (průměrnou absolutní chybu v počtu es).


Tip: můžeš zadat i zkrácené jméno (např. `Alcaraz`, `Medvedev`) a skript ho zkusí automaticky spárovat na plné jméno z datasetu.


## Turnajová appka (výběr turnaje + hráčů)

Pokud nechceš psát jména ručně, použij výběrovou appku:

```bash
python3 tournament_ace_app.py --csv-files sample_atp_matches.csv
```

Postup:
1. vybereš turnaj (např. Dubai),
2. vybereš hráče A ze seznamu,
3. vybereš hráče B ze seznamu,
4. appka vrátí odhad es pro oba.

Turnaje mají vlastní `ace_boost` (např. Dubai je rychlejší hard), takže odhad reflektuje podmínky turnaje.


Pozn.: přidané turnaje zahrnují i Mexiko (např. **Acapulco** / **Los Cabos**) a WTA turnaje (**Mérida Open Akron**, **Guadalajara Open**).

Pro WTA lokální test můžeš použít:

```bash
python3 tournament_ace_app.py --csv-files sample_wta_matches.csv
```

### Mimo Python (varianta .exe pro Windows)

Pokud nechceš spouštět `.py`, můžeš zabalit appku do `.exe`:

```bash
py -m pip install pyinstaller
py -m PyInstaller --onefile tournament_ace_app.py
```

Pak spouštíš `dist\tournament_ace_app.exe` bez ruční práce s Python soubory.


## Windows: jedno kliknutí přes BAT

Spusť soubor `SPUSTIT_ESA.bat` (dvojklik) **ve stejné složce jako Python soubory**.

BAT teď funguje nezávisle na cestě (nepotřebuje pevnou adresu `C:\...`):
- automaticky se přepne do složky, kde leží `.bat`,
- zkontroluje, že tam je `tournament_ace_app.py`,
- zeptá se, jestli chceš WTA nebo ATP,
- spustí výpočet a na konci vždy čeká na klávesu (okno se hned nezavře).


## LIVE režim přes API (bez ručního výběru hráčů)

Pokud chceš opravdu aktuální turnaj + aktuální zápasy (bez klikaní hráčů), použij:

```bash
python3 live_api_ace_runner.py --tournament merida --tour wta --date 2026-02-27 --api-key TVUJ_API_KLIC
```

Co to dělá:
- stáhne aktuální zápasy turnaje z API,
- k hráčům dohledá historické profily,
- vrátí odhad es pro každý nalezený zápas.

Pozn.: potřebuješ API klíč (`API_TENNIS_KEY` nebo `--api-key`).


## FINAL ACE APP (klikací GUI)

Tohle je finální jednoduchá appka (klikací):

```bash
python3 final_ace_app.py
```

Postup:
1. vyber turnaj,
2. klikni **Načti hráče pro turnaj**,
3. vyber hráče A a B,
4. klikni **VYPOČTI ESA**.

Výstup obsahuje i interval nejistoty (80 %).


Nově appka při načtení hráčů cílí na **top 200** pool (podle recent zápasové aktivity + výkonnosti) z načtených ATP/WTA dat.
Pokud nejde internet, spadne to na lokální sample data (pak uvidíš méně hráčů).


Na Windows můžeš final GUI spustit i dvojklikem na `SPUSTIT_ESA.bat`.
Na Windows můžeš final GUI spustit i dvojklikem na `SPUSTIT_ESA.bat`.
