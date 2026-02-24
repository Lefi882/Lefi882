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
