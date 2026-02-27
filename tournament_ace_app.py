"""Interaktivní appka: výběr turnaje + 2 hráčů => odhad es.

Cíl: žádné ruční psaní ELO/statistik. Uživatel jen vybere turnaj a hráče.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from ace_estimator import (
    build_profile,
    estimate_aces,
    fetch_year_matches,
    read_local_matches,
)


@dataclass(frozen=True)
class TournamentProfile:
    name: str
    tour: str
    surface: str
    ace_boost: float  # >1 rychlejší podmínky, <1 pomalejší


TOURNAMENTS: Dict[str, TournamentProfile] = {
    "dubai": TournamentProfile("Dubai", "atp", "Hard", 1.08),
    "acapulco": TournamentProfile("Acapulco (Abierto Mexicano)", "atp", "Hard", 1.06),
    "los cabos": TournamentProfile("Los Cabos", "atp", "Hard", 1.05),
    "merida": TournamentProfile("Mérida Open Akron", "wta", "Hard", 1.03),
    "guadalajara": TournamentProfile("Guadalajara Open", "wta", "Hard", 1.04),
    "wimbledon": TournamentProfile("Wimbledon", "atp", "Grass", 1.16),
    "roland garros": TournamentProfile("Roland Garros", "atp", "Clay", 0.86),
    "us open": TournamentProfile("US Open", "atp", "Hard", 1.02),
    "australian open": TournamentProfile("Australian Open", "atp", "Hard", 1.03),
}

FALLBACK_SAMPLES = {
    "atp": "sample_atp_matches.csv",
    "wta": "sample_wta_matches.csv",
}


def choose_tournament() -> TournamentProfile:
    print("=== Výběr turnaje ===")
    items = list(TOURNAMENTS.values())
    for i, t in enumerate(items, start=1):
        print(f"{i}. {t.name} ({t.tour.upper()}, {t.surface}, boost {t.ace_boost})")
    while True:
        raw = input("Vyber číslo turnaje: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1]
        print("Neplatná volba, zkus to znovu.")


def extract_players(rows: List[Dict[str, str]]) -> List[str]:
    names = set()
    for r in rows:
        w = r.get("winner_name")
        l = r.get("loser_name")
        if w:
            names.add(w)
        if l:
            names.add(l)
    return sorted(names)


def choose_player(players: List[str], label: str) -> str:
    print(f"\n=== Výběr {label} ===")
    for i, p in enumerate(players, start=1):
        print(f"{i}. {p}")
    while True:
        raw = input("Zadej číslo hráče: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(players):
            return players[int(raw) - 1]
        print("Neplatná volba, zkus to znovu.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Turnajová appka pro odhad es")
    ap.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    ap.add_argument("--csv-files", nargs="*", default=[])
    args = ap.parse_args()

    tournament = choose_tournament()

    rows: List[Dict[str, str]] = []
    if args.csv_files:
        for f in args.csv_files:
            rows.extend(read_local_matches(f))
    else:
        for y in args.years:
            rows.extend(fetch_year_matches(tournament.tour, y))

        # fallback když je blokovaný internet
        if not rows:
            fallback = Path(FALLBACK_SAMPLES[tournament.tour])
            if fallback.exists():
                rows.extend(read_local_matches(str(fallback)))

    if not rows:
        raise SystemExit("Nepodařilo se načíst data. Přidej --csv-files nebo zkontroluj internet.")

    players = extract_players(rows)
    if len(players) < 2:
        raise SystemExit("V datech není dost hráčů pro výběr.")

    player_a = choose_player(players, "hráče A")
    player_b = choose_player(players, "hráče B")

    a = build_profile(player_a, rows, tournament.surface)
    b = build_profile(player_b, rows, tournament.surface)

    a_aces = round(estimate_aces(a, b, tournament.surface) * tournament.ace_boost, 1)
    b_aces = round(estimate_aces(b, a, tournament.surface) * tournament.ace_boost, 1)

    print("\n=== ODHAD ES PODLE TURNAJE ===")
    print(f"Turnaj: {tournament.name} ({tournament.tour.upper()}, {tournament.surface})")
    print(f"{a.name}: {a_aces} es")
    print(f"{b.name}: {b_aces} es")


if __name__ == "__main__":
    main()
