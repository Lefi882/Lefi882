"""Live odhad es podle aktuálního turnaje přes API-Tennis + historická data.

Princip:
1) API-Tennis dá dnešní/konkrétní zápasy pro turnaj.
2) Pro hráče v zápase se z historických dat spočte ace profil.
3) Vrátí odhad es pro oba hráče bez ručního výběru.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError

from ace_estimator import (
    build_profile,
    estimate_aces,
    fetch_year_matches,
    read_local_matches,
    resolve_player_name,
)

API_BASE = "https://api.api-tennis.com/tennis/"


def fetch_live_fixtures(api_key: str, date_str: str) -> List[Dict[str, str]]:
    params = {
        "method": "get_fixtures",
        "APIkey": api_key,
        "date_start": date_str,
        "date_stop": date_str,
    }
    url = f"{API_BASE}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
    except URLError as e:
        raise SystemExit(f"API request selhal: {e}")
    return data.get("result", []) if isinstance(data, dict) else []


def load_history(tour: str, years: List[int], csv_files: List[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if csv_files:
        for f in csv_files:
            rows.extend(read_local_matches(f))
        return rows

    for y in years:
        rows.extend(fetch_year_matches(tour, y))
    return rows


def match_tournament(name: str, query: str) -> bool:
    return query.lower() in (name or "").lower()


def main() -> None:
    ap = argparse.ArgumentParser(description="Live API odhad es pro aktuální zápasy turnaje")
    ap.add_argument("--tournament", required=True, help="např. merida, dubai, acapulco")
    ap.add_argument("--tour", choices=["atp", "wta"], default="wta")
    ap.add_argument("--date", default=datetime.utcnow().strftime("%Y-%m-%d"), help="YYYY-MM-DD")
    ap.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    ap.add_argument("--csv-files", nargs="*", default=[])
    ap.add_argument("--api-key", default=os.getenv("API_TENNIS_KEY", ""))
    args = ap.parse_args()

    if not args.api_key:
        raise SystemExit("Chybí API klíč. Dej --api-key ... nebo nastav API_TENNIS_KEY.")

    history_rows = load_history(args.tour, args.years, args.csv_files)
    if not history_rows:
        raise SystemExit("Nepodařilo se načíst historická data pro výpočet.")

    fixtures = fetch_live_fixtures(args.api_key, args.date)
    if not fixtures:
        raise SystemExit("API nevrátilo žádné zápasy pro zadané datum.")

    filtered = [f for f in fixtures if match_tournament(f.get("tournament_name", ""), args.tournament)]
    if not filtered:
        raise SystemExit(f"Nenašel jsem zápasy pro turnaj '{args.tournament}' na {args.date}.")

    print(f"=== LIVE ODHAD ES ({args.tournament}, {args.date}) ===")
    for f in filtered:
        p1_raw = (f.get("event_first_player") or "").strip()
        p2_raw = (f.get("event_second_player") or "").strip()
        tname = f.get("tournament_name", "?")

        p1 = resolve_player_name(history_rows, p1_raw) or p1_raw
        p2 = resolve_player_name(history_rows, p2_raw) or p2_raw

        try:
            a = build_profile(p1, history_rows, "Hard")
            b = build_profile(p2, history_rows, "Hard")
        except Exception as e:
            print(f"- {p1_raw} vs {p2_raw} ({tname}): přeskočeno ({e})")
            continue

        a_aces = estimate_aces(a, b, "Hard")
        b_aces = estimate_aces(b, a, "Hard")
        print(f"- {p1_raw} vs {p2_raw} | odhad es: {a_aces:.1f} - {b_aces:.1f} | {tname}")


if __name__ == "__main__":
    main()
