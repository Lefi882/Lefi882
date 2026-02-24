"""Automatický tenisový prediktor nad veřejnými ATP/WTA daty (Jeff Sackmann).

Vrací:
- pravděpodobnost výhry hráče A/B
- odhad celkového počtu gamů
- odhad es a dvojchyb pro oba hráče
"""

from __future__ import annotations

import argparse
import csv
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import URLError
from urllib.request import urlopen

from tenis_probability_model import MatchContext, PlayerFeatures, Weights, estimate_win_probability

DATA_URL_TEMPLATE = "https://raw.githubusercontent.com/JeffSackmann/tennis_{tour}/master/{tour}_matches_{year}.csv"
CACHE_DIR = Path(".cache_tennis")


@dataclass
class PlayerStats:
    name: str
    surface_rating: float
    recent_form: float
    fatigue: float
    ace_rate: float
    return_points_won: float
    pressure_index: float
    aces_per_match: float
    double_faults_per_match: float


def safe_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return None


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
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Soubor s daty neexistuje: {csv_path}")
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def collect_player_matches(rows: Iterable[Dict[str, str]], player_name: str, surface: Optional[str]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for r in rows:
        if surface and r.get("surface", "").lower() != surface.lower():
            continue
        if r.get("winner_name") == player_name or r.get("loser_name") == player_name:
            out.append(r)
    out.sort(key=lambda x: x.get("tourney_date", ""), reverse=True)
    return out


def row_features_for_player(row: Dict[str, str], player_name: str) -> Dict[str, float]:
    is_winner = row.get("winner_name") == player_name

    if is_winner:
        ace = safe_float(row.get("w_ace"))
        df = safe_float(row.get("w_df"))
        svpt = max(safe_float(row.get("w_svpt"), 1.0), 1.0)
        opp_svpt = max(safe_float(row.get("l_svpt"), 1.0), 1.0)
        opp_1st_won = safe_float(row.get("l_1stWon"))
        opp_2nd_won = safe_float(row.get("l_2ndWon"))
        bp_saved = safe_float(row.get("w_bpSaved"))
        bp_faced = safe_float(row.get("w_bpFaced"))
    else:
        ace = safe_float(row.get("l_ace"))
        df = safe_float(row.get("l_df"))
        svpt = max(safe_float(row.get("l_svpt"), 1.0), 1.0)
        opp_svpt = max(safe_float(row.get("w_svpt"), 1.0), 1.0)
        opp_1st_won = safe_float(row.get("w_1stWon"))
        opp_2nd_won = safe_float(row.get("w_2ndWon"))
        bp_saved = safe_float(row.get("l_bpSaved"))
        bp_faced = safe_float(row.get("l_bpFaced"))

    return_points_won = max(0.0, min(1.0, (opp_svpt - opp_1st_won - opp_2nd_won) / opp_svpt))
    ace_rate = ace / svpt
    pressure = bp_saved / bp_faced if bp_faced > 0 else 0.62

    return {
        "won": 1.0 if is_winner else 0.0,
        "ace": ace,
        "df": df,
        "ace_rate": ace_rate,
        "return_points_won": return_points_won,
        "pressure": pressure,
        "date_ordinal": parse_date(row.get("tourney_date", "") or "").toordinal() if parse_date(row.get("tourney_date", "")) else 0,
    }


def estimate_player_stats(player_name: str, all_rows: List[Dict[str, str]], surface: str, recent_n: int = 30) -> PlayerStats:
    surface_matches = collect_player_matches(all_rows, player_name, surface)
    all_matches = collect_player_matches(all_rows, player_name, None)

    if not all_matches:
        raise ValueError(f"Hráč '{player_name}' nebyl v datech nalezen.")

    recent = all_matches[:recent_n]
    recent_feats = [row_features_for_player(r, player_name) for r in recent]

    recent_form = statistics.mean(x["won"] for x in recent_feats) if recent_feats else 0.5

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    matches_last_week = 0
    for r in all_matches[:20]:
        d = parse_date(r.get("tourney_date", "") or "")
        if d and d >= week_ago:
            matches_last_week += 1
    fatigue = min(1.0, matches_last_week / 5)

    surface_wins = 0
    for r in surface_matches[:80]:
        if r.get("winner_name") == player_name:
            surface_wins += 1
    swr = (surface_wins / max(1, len(surface_matches[:80]))) if surface_matches else recent_form
    surface_rating = 1500 + 450 * (swr - 0.5)

    ace_rate = statistics.mean(x["ace_rate"] for x in recent_feats) if recent_feats else 0.05
    return_won = statistics.mean(x["return_points_won"] for x in recent_feats) if recent_feats else 0.36
    pressure_index = statistics.mean(x["pressure"] for x in recent_feats) if recent_feats else 0.62

    aces_pm = statistics.mean(x["ace"] for x in recent_feats) if recent_feats else 5.0
    df_pm = statistics.mean(x["df"] for x in recent_feats) if recent_feats else 2.8

    return PlayerStats(
        name=player_name,
        surface_rating=surface_rating,
        recent_form=recent_form,
        fatigue=fatigue,
        ace_rate=ace_rate,
        return_points_won=return_won,
        pressure_index=pressure_index,
        aces_per_match=aces_pm,
        double_faults_per_match=df_pm,
    )


def surface_speed(surface: str) -> float:
    mapping = {
        "hard": 0.25,
        "grass": 0.7,
        "clay": -0.45,
        "carpet": 0.8,
    }
    return mapping.get(surface.lower(), 0.1)


def estimate_totals(p1: float, surface: str) -> float:
    base = {"clay": 22.8, "hard": 22.3, "grass": 23.2, "carpet": 23.0}.get(surface.lower(), 22.5)
    closeness = 1 - abs(2 * p1 - 1)
    return round(base + 5.0 * closeness, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatický odhad tenisového zápasu")
    parser.add_argument("player_a", help="Jméno hráče A, např. 'Novak Djokovic'")
    parser.add_argument("player_b", help="Jméno hráče B, např. 'Carlos Alcaraz'")
    parser.add_argument("--tour", choices=["atp", "wta"], default="atp")
    parser.add_argument("--surface", choices=["Hard", "Clay", "Grass", "Carpet"], default="Hard")
    parser.add_argument("--years", nargs="+", type=int, default=[datetime.utcnow().year - 1, datetime.utcnow().year])
    parser.add_argument("--importance", type=float, default=0.6, help="0..1")
    parser.add_argument(
        "--csv-files",
        nargs="*",
        default=[],
        help="Volitelné lokální CSV soubory se zápasy (když nechceš nebo nemůžeš stahovat data).",
    )
    args = parser.parse_args()

    rows: List[Dict[str, str]] = []
    if args.csv_files:
        for csv_file in args.csv_files:
            rows.extend(read_local_matches(csv_file))
    else:
        for y in args.years:
            rows.extend(fetch_year_matches(args.tour, y))

    if not rows:
        raise SystemExit(
            "Nepodařilo se načíst žádná data. Zkus jiné roky/připojení "
            "nebo použij --csv-files s lokálním CSV datasetem."
        )

    a = estimate_player_stats(args.player_a, rows, args.surface)
    b = estimate_player_stats(args.player_b, rows, args.surface)

    context = MatchContext(
        importance=max(0.0, min(1.0, args.importance)),
        weather_impact=0.0,
        speed_index=surface_speed(args.surface),
    )

    pa = PlayerFeatures(
        name=a.name,
        elo_surface=a.surface_rating,
        recent_form=a.recent_form,
        fatigue=a.fatigue,
        ace_rate=a.ace_rate,
        return_points_won=a.return_points_won,
        pressure_index=a.pressure_index,
    )
    pb = PlayerFeatures(
        name=b.name,
        elo_surface=b.surface_rating,
        recent_form=b.recent_form,
        fatigue=b.fatigue,
        ace_rate=b.ace_rate,
        return_points_won=b.return_points_won,
        pressure_index=b.pressure_index,
    )

    p_win_a = estimate_win_probability(pa, pb, context, Weights())
    p_win_b = 1 - p_win_a

    total_games = estimate_totals(p_win_a, args.surface)

    print("=== AUTOMATICKÝ ODHAD (bez ručního vyplňování statistik) ===")
    print(f"Data: {args.tour.upper()}, roky: {args.years}, povrch: {args.surface}")
    print()
    print(f"{a.name} výhra: {p_win_a * 100:.1f} %")
    print(f"{b.name} výhra: {p_win_b * 100:.1f} %")
    print(f"Odhad celkového počtu gamů: {total_games}")
    print()
    print("Odhad hráčských statistik (na zápas):")
    print(f"- {a.name}: esa {a.aces_per_match:.1f}, dvojchyby {a.double_faults_per_match:.1f}")
    print(f"- {b.name}: esa {b.aces_per_match:.1f}, dvojchyby {b.double_faults_per_match:.1f}")


if __name__ == "__main__":
    main()
