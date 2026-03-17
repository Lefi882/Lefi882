# Porovnání kurzů českých sázkovek (pregame MVP)

Tento repozitář obsahuje MVP nástroj pro:

- stažení **celé pregame 1X2 nabídky** fotbalu z více bookmakerů,
- párování stejných zápasů mezi sázkovkami (i při odlišných názvech),
- porovnání nejlepších kurzů a detekci arbitráže,
- periodický sběr snapshotů (typicky každých 60 sekund).

## Rychlý start (jak spustit)

1. Nainstaluj Python závislosti (a případně Node + Playwright pro scrapers).
2. Pro Windows bez CMD použij `START_HERE.bat` (dvojklik).
3. Pro CLI použij `python3 scripts/run_all.py`.

## Spuštění bez psaní do CMD (BAT / EXE)

Pokud nechceš psát příkazy ručně, stačí ve Windows spustit dvojklikem:

- `START_HERE.bat` → rozcestník (výběr 1/2/3),
- `start_pipeline.bat` → spustí celý pipeline pro **all sports** + detailní Tipsport trhy (karty/rohy apod.),
- `start_valuebet_demo.bat` → spustí konkrétní demo (Arsenal vs Chelsea),
- `start_snapshot.bat` → udělá jeden snapshot přes `main.py`.

### EXE varianta (volitelné)

Ano, jde to i jako `.exe` pomocí PyInstalleru (zabalí Python skript do jednoho souboru):

```bat
py -3 -m pip install pyinstaller
py -3 -m PyInstaller --onefile --name lefi_pipeline scripts\run_all.py
```

Výsledný soubor bude v `dist\lefi_pipeline.exe`.

## Nejjednodušší cesta stahování

Použij `providers.json` a u každé sázkovky vyplň:

- `data_file` (lokální JSON), nebo `source_url` (přímé URL na JSON feed),
- `format`:
  - `events` (obecný normalizovaný feed),
  - `tipsport_offer_v2` (nativní Tipsport `rest/offer/v2/offer`).

Ukázka (`providers.json`):

```json
{
  "providers": [
    {
      "bookmaker": "Tipsport",
      "source_url": "https://www.tipsport.cz/rest/offer/v2/offer?limit=75",
      "format": "tipsport_offer_v2"
    },
    {
      "bookmaker": "Fortuna",
      "data_file": "data/fortuna.json",
      "format": "events"
    }
  ]
}
```

## Spuštění

### Jak spustit snapshot

Jednorázový snapshot:

```bash
python3 main.py --iterations 1
```

Sběr každou minutu:

```bash
python3 main.py --interval-sec 60 --iterations 0
```

Vlastní config providerů:

```bash
python3 main.py --providers-file providers.json --iterations 1
```

## Formáty feedu

### `events` (obecný)

```json
{
  "events": [
    {
      "event_id": "id-1",
      "event_name": "Sparta Praha vs Slavia Praha",
      "sport": "football",
      "market": "1X2",
      "kickoff": "2026-02-20T18:00:00",
      "odds": {"1": 2.35, "X": 3.50, "2": 3.10}
    }
  ]
}
```

### `tipsport_offer_v2` (nativní Tipsport)

Parser bere pouze:

- `superSportId = 16` (fotbal),
- `matchView = WINNER_WHOLE_MATCH`,
- kurzy `type` = `1`, `x`, `2` (mapované na `1/X/2`),
- ignoruje `race=true` (celkové pořadí/outright).

## Výstup

- V konzoli se vypíše počet nabídek, počet spárovaných eventů, nejlepší kurzy a arbitrážní info.
- Každý běh se uloží do `snapshots/pregame_offers.jsonl`.


## Tipsport Playwright scraper (rychlý sběr)

Přidal jsem i samostatný skript `scripts/tipsport2.js`, který umí:

- stáhnout kurzy z Tipsportu přes Playwright,
- volit sport (`--sport 16` fotbal, `--sport 188` esporty),
- volitelně stáhnout detailní trhy každého zápasu (`--details`),
- uložit výstup do JSON (`--json`).

### Jak spustit Tipsport scraper

Příklady:

```bash
node scripts/tipsport2.js
node scripts/tipsport2.js --sport 188
node scripts/tipsport2.js --sport 188 --details --limit 5
node scripts/tipsport2.js --json
```

> Pozn.: vyžaduje nainstalovaný `playwright` v Node.js prostředí.



## Betano Playwright scraper (rychlý sběr)

Přidal jsem samostatný skript `scripts/betano.js`, který zachytává:

- overview endpointy (`/danae-webapi/api/live/overview/...`),
- fallback detail endpointy (`/api/zapas-sance/...`),
- mapování 1X2 (`1`, `0`, `2` -> `1`, `X`, `2`).

### Jak spustit Betano scraper

Příklady:

```bash
node scripts/betano.js
node scripts/betano.js --json
node scripts/betano.js --esports
```

> Skript je zaměřený na rychlý praktický sběr (stejně jako Tipsport varianta) a vyžaduje nainstalovaný `playwright` v Node.js prostředí.




## One-command automat (stáhnout + vyhodnotit)

### Jak spustit celý pipeline

Pokud chceš všechno spustit jedním příkazem (Tipsport + Betano scraping a následné value vyhodnocení), použij:

```bash
python3 scripts/run_all.py
```

Volitelně:

```bash
python3 scripts/run_all.py --target betano --min-edge 1.5 --top 30
python3 scripts/run_all.py --tipsport-sport all --tipsport-details --betano-all
python3 scripts/run_all.py --run-snapshot
```

Na Windows:

```bat
py scripts\run_all.py
```


## Value bet evaluátor (Tipsport vs Betano)

### Jak spustit value-bet evaluátor

Po nasbírání dat přes Playwright scrapers můžeš spustit jednoduchý vyhodnocovací systém VALUE betů:

```bash
python3 scripts/valuebets_tipsport_betano.py \
  --tipsport tipsport_odds.json \
  --betano betano_odds.json \
  --target tipsport \
  --min-edge 1.0
```

Co to dělá:

- spáruje podobné zápasy mezi Tipsport a Betano,
- z referenční sázkovky dopočítá „fair" pravděpodobnost 1X2 (normalizací marže),
- spočítá edge (%) pro cílovou sázkovku,
- vypíše nejlepší value kandidáty (event, outcome, ratio, edge).

Tip: přepni `--target betano`, pokud chceš hledat value na Betanu vůči Tipsportu.

Pozn.: pokud nic neprojde přes `--min-edge`, skript automaticky vypíše nejsilnější cenové rozdíly (`--fallback-top`).

Pro rychlý test s **konkrétním zápasem** (Arsenal vs Chelsea) a garantovaným nálezem value-betu:

```bash
python3 scripts/valuebets_tipsport_betano.py --manual-demo --target tipsport --min-edge 1.0
```



## Hidden API scraper (Method 1: HTTP Requests)

Pro školní zadání bez oficiálního API je v repu i čistě HTTP varianta:

- skript: `scripts/hidden_api_scraper.py`
- cíl: stáhnout interní JSON endpointy (XHR/Fetch) a převést je do formátu `events`, který už umí `main.py` a pipeline.

### Příklad použití

```bash
python3 scripts/hidden_api_scraper.py \
  --bookmaker DemoBookie \
  --url "https://example.com/api/sports/events?sport=football" \
  --url "https://example.com/v2/odds/upcoming?market=1x2" \
  --min-delay 1.0 --max-delay 2.5 \
  --output data/demo_hidden_api.json
```

Pak stačí přidat provider do `providers.json` jako standardní `events` feed:

```json
{
  "bookmaker": "DemoBookie",
  "data_file": "data/demo_hidden_api.json",
  "format": "events"
}
```

Skript používá náhodné zpoždění mezi requesty (omezení blokace) a ukládá výstup rovnou v normalizovaném tvaru.
