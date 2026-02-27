"""Odhad počtu es pro konkrétní tenisový zápas.

Zaměřeno pouze na esa (bez odhadu výhry, gamů apod.).
Vstupem jsou historické zápasy ve formátu Jeff Sackmann CSV.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import URLError
from urllib.request import urlopen

DATA_URL_TEMPLATE = "https://raw.githubusercontent.com/JeffSackmann/tennis_{tour}/master/{tour}_matches_{year}.csv"
CACHE_DIR = Path(".cache_tennis")


@dataclass
class AceProfile:
    name: str
    ace_rate_srv_point: float
    ace_per_match: float
    ace_allowed_rate: float
    expected_service_points: float


def safe_float(v: Optional[str], default: float = 0.0) -> float:
    if not v:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def fetch_year_matches(tour: str, year: int, use_cache: bool = True) -> List[Dict[str, str]]:
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{tour}_matches_{year}.csv"

    content: Optional[str] = None
    if use_cache and cache_file.exists():
        content = cache_file.read_text(encoding="utf-8")
    else:
        url = DATA_URL_TEMPLATE.format(tour=tour, year=year)
        try:
            with urlopen(url, timeout=20) as response:
                content = response.read().decode("utf-8", errors="ignore")
        except URLError:
            return []
        if use_cache and content:
            cache_file.write_text(content, encoding="utf-8")

    if not content:
        return []

    return list(csv.DictReader(StringIO(content)))


def read_local_matches(csv_path: str) -> List[Dict[str, str]]:
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f"Chybí dataset: {csv_path}")
    return list(csv.DictReader(p.read_text(encoding="utf-8").splitlines()))


def player_rows(rows: Iterable[Dict[str, str]], player: str, surface: Optional[str]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for r in rows:
        if surface and r.get("surface", "").lower() != surface.lower():
            continue
        if r.get("winner_name") == player or r.get("loser_name") == player:
            out.append(r)
    out.sort(key=lambda x: x.get("tourney_date", ""), reverse=True)
    return out


def ace_features(row: Dict[str, str], player: str) -> Dict[str, float]:
    is_winner = row.get("winner_name") == player

    if is_winner:
        own_ace = safe_float(row.get("w_ace"))
        own_svpt = max(1.0, safe_float(row.get("w_svpt"), 1.0))
        opp_ace = safe_float(row.get("l_ace"))
        opp_svpt = max(1.0, safe_float(row.get("l_svpt"), 1.0))
    else:
        own_ace = safe_float(row.get("l_ace"))
        own_svpt = max(1.0, safe_float(row.get("l_svpt"), 1.0))
        opp_ace = safe_float(row.get("w_ace"))
        opp_svpt = max(1.0, safe_float(row.get("w_svpt"), 1.0))

    return {
        "own_ace_rate": own_ace / own_svpt,
        "own_ace": own_ace,
        "opp_ace_allowed_rate": opp_ace / opp_svpt,
        "own_svpt": own_svpt,
    }


def build_profile(name: str, rows: List[Dict[str, str]], surface: str, recent_n: int = 30) -> AceProfile:
    prs = player_rows(rows, name, surface)
    if not prs:
        prs = player_rows(rows, name, None)
    if not prs:
        raise ValueError(f"Hráč '{name}' nebyl v datech.")

    feats = [ace_features(r, name) for r in prs[:recent_n]]

    ace_rate = statistics.mean(x["own_ace_rate"] for x in feats)
    ace_per_match = statistics.mean(x["own_ace"] for x in feats)
    ace_allowed = statistics.mean(x["opp_ace_allowed_rate"] for x in feats)
    expected_svpt = statistics.mean(x["own_svpt"] for x in feats)

    return AceProfile(
        name=name,
        ace_rate_srv_point=ace_rate,
        ace_per_match=ace_per_match,
        ace_allowed_rate=ace_allowed,
        expected_service_points=expected_svpt,
    )


def surface_factor(surface: str) -> float:
    # hrubá korekce rychlosti podmínek pro esa
    return {
        "grass": 1.18,
        "hard": 1.00,
        "clay": 0.84,
        "carpet": 1.22,
    }.get(surface.lower(), 1.0)


def estimate_aces(server: AceProfile, returner: AceProfile, surface: str) -> float:
    interaction_rate = 0.7 * server.ace_rate_srv_point + 0.3 * returner.ace_allowed_rate
    projected = interaction_rate * server.expected_service_points * surface_factor(surface)
    return max(0.0, round(projected, 1))


def main() -> None:
    p = argparse.ArgumentParser(description="Odhad počtu es (2 hráči)")
    p.add_argument("player_a", nargs="?", help="Jméno hráče A")
    p.add_argument("player_b", nargs="?", help="Jméno hráče B")
    p.add_argument("--tour", choices=["atp", "wta"], default="atp")
    p.add_argument("--surface", choices=["Hard", "Clay", "Grass", "Carpet"], default="Hard")
    p.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    p.add_argument("--csv-files", nargs="*", default=[])
    args = p.parse_args()

    if not args.player_a:
        args.player_a = input("Zadej hráče A: ").strip()
    if not args.player_b:
        args.player_b = input("Zadej hráče B: ").strip()
    if not args.player_a or not args.player_b:
        raise SystemExit("Musíš zadat oba hráče.")

    rows: List[Dict[str, str]] = []
    if args.csv_files:
        for f in args.csv_files:
            rows.extend(read_local_matches(f))
    else:
        for y in args.years:
            rows.extend(fetch_year_matches(args.tour, y))

    if not rows:
        raise SystemExit("Nepodařilo se načíst data. Použij --csv-files nebo zkontroluj internet.")

    a = build_profile(args.player_a, rows, args.surface)
    b = build_profile(args.player_b, rows, args.surface)

    a_aces = estimate_aces(a, b, args.surface)
    b_aces = estimate_aces(b, a, args.surface)

    print("=== ODHAD ES (AUTO) ===")
    print(f"Povrch: {args.surface}")
    print(f"{a.name}: {a_aces} es")
    print(f"{b.name}: {b_aces} es")


if __name__ == "__main__":
    main()
