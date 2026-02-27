"""Backtest + jednoduché doladění odhadu es na historických zápasech.

Použití:
  python3 ace_backtest.py --csv-files atp_matches_2024.csv --surface Hard --tests 50
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from pathlib import Path
from typing import Dict, List, Tuple

from ace_estimator import (
    DATA_URL_TEMPLATE,
    fetch_year_matches,
    read_local_matches,
    player_rows,
    ace_features,
    safe_float,
)


def build_profile_from_rows(player: str, rows: List[Dict[str, str]], surface: str, recent_n: int = 30) -> Tuple[float, float, float]:
    prs = player_rows(rows, player, surface)
    if not prs:
        prs = player_rows(rows, player, None)
    if not prs:
        raise ValueError(player)
    feats = [ace_features(r, player) for r in prs[:recent_n]]
    ace_rate = statistics.mean(x["own_ace_rate"] for x in feats)
    ace_allowed = statistics.mean(x["opp_ace_allowed_rate"] for x in feats)
    svpt = statistics.mean(x["own_svpt"] for x in feats)
    return ace_rate, ace_allowed, svpt


def actual_aces(row: Dict[str, str], player: str) -> float:
    if row.get("winner_name") == player:
        return safe_float(row.get("w_ace"))
    return safe_float(row.get("l_ace"))


def predict_aces(ace_rate: float, opp_ace_allowed: float, svpt: float, alpha: float, surface_mult: float) -> float:
    rate = alpha * ace_rate + (1 - alpha) * opp_ace_allowed
    return max(0.0, rate * svpt * surface_mult)


def surface_factor(surface: str, clay: float, hard: float, grass: float, carpet: float) -> float:
    m = {"clay": clay, "hard": hard, "grass": grass, "carpet": carpet}
    return m.get(surface.lower(), 1.0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest odhadu es")
    ap.add_argument("--tour", choices=["atp", "wta"], default="atp")
    ap.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    ap.add_argument("--csv-files", nargs="*", default=[])
    ap.add_argument("--surface", choices=["Hard", "Clay", "Grass", "Carpet"], default="Hard")
    ap.add_argument("--tests", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows: List[Dict[str, str]] = []
    if args.csv_files:
        for f in args.csv_files:
            rows.extend(read_local_matches(f))
    else:
        for y in args.years:
            rows.extend(fetch_year_matches(args.tour, y))

    if not rows:
        raise SystemExit("Žádná data pro backtest. Dej --csv-files nebo roky s dostupnými daty.")

    rows = [r for r in rows if r.get("winner_name") and r.get("loser_name")]
    rows.sort(key=lambda r: r.get("tourney_date", ""))

    candidates = [r for r in rows if r.get("surface", "").lower() == args.surface.lower()]
    if len(candidates) < args.tests:
        raise SystemExit(f"Pro povrch {args.surface} je jen {len(candidates)} zápasů, požadováno {args.tests}.")

    rnd = random.Random(args.seed)
    sample = rnd.sample(candidates, args.tests)

    # Grid-search jednoduché kalibrace
    best = None
    for alpha in [0.5, 0.6, 0.7, 0.8]:
        for clay in [0.80, 0.84, 0.88]:
            for hard in [0.95, 1.00, 1.05]:
                for grass in [1.10, 1.18, 1.25]:
                    for carpet in [1.10, 1.22, 1.30]:
                        abs_errs: List[float] = []
                        for m in sample:
                            dt = m.get("tourney_date", "")
                            train = [x for x in rows if x.get("tourney_date", "") < dt]
                            if len(train) < 6:
                                continue
                            a = m["winner_name"]
                            b = m["loser_name"]
                            try:
                                a_rate, _, a_svpt = build_profile_from_rows(a, train, args.surface)
                                b_rate, _, b_svpt = build_profile_from_rows(b, train, args.surface)
                                _, b_allow, _ = build_profile_from_rows(b, train, args.surface)
                                _, a_allow, _ = build_profile_from_rows(a, train, args.surface)
                            except Exception:
                                continue

                            sf = surface_factor(args.surface, clay, hard, grass, carpet)
                            p_a = predict_aces(a_rate, b_allow, a_svpt, alpha, sf)
                            p_b = predict_aces(b_rate, a_allow, b_svpt, alpha, sf)
                            y_a = actual_aces(m, a)
                            y_b = actual_aces(m, b)
                            abs_errs.extend([abs(p_a - y_a), abs(p_b - y_b)])

                        if not abs_errs:
                            continue
                        mae = statistics.mean(abs_errs)
                        key = (mae, alpha, clay, hard, grass, carpet)
                        if best is None or key < best:
                            best = key

    if best is None:
        raise SystemExit("Nepodařilo se spočítat backtest (málo trénovacích dat).")

    mae, alpha, clay, hard, grass, carpet = best
    print("=== BACKTEST ODHADU ES ===")
    print(f"Počet test zápasů: {args.tests}")
    print(f"Povrch: {args.surface}")
    print(f"Nejlepší MAE (esa): {mae:.2f}")
    print(f"alpha={alpha}, surface_factors: clay={clay}, hard={hard}, grass={grass}, carpet={carpet}")


if __name__ == "__main__":
    main()
