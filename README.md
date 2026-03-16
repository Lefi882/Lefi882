# Porovnání kurzů českých sázkovek (pregame MVP)

Tento repozitář obsahuje MVP nástroj pro:

- stažení **celé pregame 1X2 nabídky** fotbalu z více bookmakerů,
- párování stejných zápasů mezi sázkovkami (i při odlišných názvech),
- porovnání nejlepších kurzů a detekci arbitráže,
- periodický sběr snapshotů (typicky každých 60 sekund).

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

Příklady:

```bash
node scripts/betano.js
node scripts/betano.js --json
```

> Skript je zaměřený na rychlý praktický sběr (stejně jako Tipsport varianta) a vyžaduje nainstalovaný `playwright` v Node.js prostředí.

