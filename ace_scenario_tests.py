"""Scenario-based validation for ace predictions.

Usage:
  python3 ace_scenario_tests.py --csv-files sample_atp_matches.csv --surface Hard
"""

from __future__ import annotations

import argparse
import statistics
from typing import Dict, List, Tuple

from ace_engine import estimate_aces_for_match, load_rows


DEFAULT_SCENARIOS: List[Tuple[str, str, str, float, float]] = [
    # player_a, player_b, surface, actual_a_aces, actual_b_aces
    ("Novak Djokovic", "Carlos Alcaraz", "Hard", 8.0, 6.0),
    ("Carlos Alcaraz", "Jannik Sinner", "Hard", 10.0, 9.0),
    ("Novak Djokovic", "Jannik Sinner", "Hard", 11.0, 7.0),
    # User-reported scenario (kept as a tracked benchmark)
    ("Yannick Hanfmann", "Luciano Darderi", "Clay", 10.0, 6.0),
]


def run_scenarios(rows: List[Dict[str, str]], scenarios: List[Tuple[str, str, str, float, float]]) -> None:
    errors: List[float] = []
    print("=== ACE SCENARIO TESTS ===")
    for p1, p2, surface, y1, y2 in scenarios:
        try:
            p1_hat, p2_hat, _, _ = estimate_aces_for_match(rows, p1, p2, surface, 1.0)
        except Exception as exc:
            print(f"- SKIP {p1} vs {p2} ({surface}): {exc}")
            continue

        e1 = abs(p1_hat - y1)
        e2 = abs(p2_hat - y2)
        errors.extend([e1, e2])
        print(
            f"- {p1} vs {p2} ({surface}) | pred {p1_hat:.1f}-{p2_hat:.1f} | "
            f"actual {y1:.1f}-{y2:.1f} | abs err {e1:.1f}/{e2:.1f}"
        )

    if errors:
        print(f"\nMAE (aces, scenario set): {statistics.mean(errors):.2f}")
    else:
        print("\nNo scenario could be evaluated with current data.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Scenario tests for ace estimator")
    ap.add_argument("--tour", choices=["atp", "wta"], default="atp")
    ap.add_argument("--years", nargs="+", type=int, default=[2024, 2025, 2026])
    ap.add_argument("--csv-files", nargs="*", default=[])
    args = ap.parse_args()

    rows = load_rows(args.tour, args.years, csv_files=args.csv_files)
    run_scenarios(rows, DEFAULT_SCENARIOS)


if __name__ == "__main__":
    main()
