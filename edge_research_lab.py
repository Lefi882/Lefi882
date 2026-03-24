"""Research lab for tennis betting edges: intransitivity, calibration, and CLV.

Subcommands:
  - intransitivity-backtest: evaluates upset-rate lift in high intransitivity matches
  - calibration-report: checks probability calibration vs outcomes
  - clv-report: summarizes CLV and ROI from a bet log CSV
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ace_estimator import read_local_matches, safe_float


@dataclass
class MatchObs:
    date: str
    winner: str
    loser: str
    winner_rank: Optional[int]
    loser_rank: Optional[int]


def _safe_int(v: Optional[str]) -> Optional[int]:
    if not v:
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def load_match_obs(csv_files: List[str], surface: Optional[str] = None) -> List[MatchObs]:
    rows: List[Dict[str, str]] = []
    for f in csv_files:
        rows.extend(read_local_matches(f))

    out: List[MatchObs] = []
    for r in rows:
        if surface and r.get("surface", "").lower() != surface.lower():
            continue
        w = (r.get("winner_name") or "").strip()
        l = (r.get("loser_name") or "").strip()
        if not w or not l:
            continue
        out.append(
            MatchObs(
                date=r.get("tourney_date", ""),
                winner=w,
                loser=l,
                winner_rank=_safe_int(r.get("winner_rank")),
                loser_rank=_safe_int(r.get("loser_rank")),
            )
        )

    out.sort(key=lambda m: m.date)
    return out


class HeadToHeadStore:
    def __init__(self) -> None:
        self.wins_vs: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.losses_vs: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.opponents: Dict[str, set[str]] = defaultdict(set)

    def add(self, winner: str, loser: str) -> None:
        self.wins_vs[winner][loser] += 1
        self.losses_vs[loser][winner] += 1
        self.opponents[winner].add(loser)
        self.opponents[loser].add(winner)

    def wins(self, a: str, b: str) -> int:
        return self.wins_vs[a].get(b, 0)

    def losses(self, a: str, b: str) -> int:
        return self.losses_vs[a].get(b, 0)


def intransitivity_score(h2h: HeadToHeadStore, a: str, b: str, max_common: int = 80) -> float:
    """Score > 0 means stronger cyclic evidence around matchup a vs b.

    We count two pattern families:
      - A beats C and C beats B (supports A)
      - B beats D and D beats A (supports B)
    High values for both directions imply rock-paper-scissors structure.
    """
    commons = list(h2h.opponents[a].intersection(h2h.opponents[b]))[:max_common]
    if not commons:
        return 0.0

    supports_a = 0.0
    supports_b = 0.0
    for c in commons:
        a_over_c = h2h.wins(a, c)
        c_over_a = h2h.wins(c, a)
        b_over_c = h2h.wins(b, c)
        c_over_b = h2h.wins(c, b)

        if a_over_c > 0 and c_over_b > 0:
            supports_a += min(a_over_c, c_over_b)
        if b_over_c > 0 and c_over_a > 0:
            supports_b += min(b_over_c, c_over_a)

    # cyclicity requires evidence on both sides
    return math.sqrt(supports_a * supports_b)


def favored_player(obs: MatchObs) -> Optional[str]:
    if obs.winner_rank is None or obs.loser_rank is None:
        return None
    return obs.winner if obs.winner_rank < obs.loser_rank else obs.loser


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def base_rank_probability(rank_a: Optional[int], rank_b: Optional[int], slope: float = 0.045) -> Optional[float]:
    if rank_a is None or rank_b is None:
        return None
    diff = rank_b - rank_a
    return logistic(slope * diff)


def run_intransitivity_backtest(matches: List[MatchObs], min_hist_matches: int = 80, score_threshold: float = 1.5) -> None:
    h2h = HeadToHeadStore()

    n_total = 0
    n_upsets_total = 0
    n_tagged = 0
    n_upsets_tagged = 0

    for m in matches:
        total_hist = sum(sum(v.values()) for v in h2h.wins_vs.values())
        if total_hist >= min_hist_matches:
            fav = favored_player(m)
            if fav:
                n_total += 1
                upset = (m.winner != fav)
                if upset:
                    n_upsets_total += 1

                score = intransitivity_score(h2h, m.winner, m.loser)
                if score >= score_threshold:
                    n_tagged += 1
                    if upset:
                        n_upsets_tagged += 1

        h2h.add(m.winner, m.loser)

    baseline = (n_upsets_total / n_total) if n_total else 0.0
    tagged = (n_upsets_tagged / n_tagged) if n_tagged else 0.0

    print("=== INTRANSITIVITY BACKTEST ===")
    print(f"Analyzované zápasy (s rank favorit/underdog): {n_total}")
    print(f"Baseline upset rate: {baseline*100:.2f}%")
    print(f"Tagované intransitivní zápasy: {n_tagged}")
    print(f"Upset rate v tagu: {tagged*100:.2f}%")
    if n_tagged:
        print(f"Lift vs baseline: {(tagged - baseline)*100:.2f} p.b.")


def run_calibration_report(matches: List[MatchObs], split_ratio: float = 0.7) -> None:
    """Train slope on train split by minimizing Brier; report calibration on test."""
    obs: List[Tuple[float, int]] = []
    for m in matches:
        # probability of winner being better-ranked player
        if m.winner_rank is None or m.loser_rank is None:
            continue
        p_winner = base_rank_probability(m.winner_rank, m.loser_rank, slope=0.045)
        if p_winner is None:
            continue
        y = 1  # winner actually won
        obs.append((p_winner, y))

    if len(obs) < 50:
        print("Málo dat pro kalibraci (min 50 pozorování).")
        return

    cut = int(len(obs) * split_ratio)
    train = obs[:cut]
    test = obs[cut:]

    best_slope = 0.045
    best_brier = 10.0
    for slope in [x / 1000 for x in range(10, 90, 2)]:
        brier = 0.0
        n = 0
        for p_raw, y in train:
            # reconstruct rank diff-ish via inverse-logit trick around current raw baseline
            logit = math.log(max(1e-6, min(1 - 1e-6, p_raw)) / max(1e-6, 1 - p_raw))
            p = logistic((slope / 0.045) * logit)
            brier += (p - y) ** 2
            n += 1
        brier = brier / max(1, n)
        if brier < best_brier:
            best_brier = brier
            best_slope = slope

    # evaluate on test with 10-bin calibration
    bins = [{"n": 0, "p_sum": 0.0, "y_sum": 0} for _ in range(10)]
    brier = 0.0
    for p_raw, y in test:
        logit = math.log(max(1e-6, min(1 - 1e-6, p_raw)) / max(1e-6, 1 - p_raw))
        p = logistic((best_slope / 0.045) * logit)
        brier += (p - y) ** 2
        bi = min(9, max(0, int(p * 10)))
        bins[bi]["n"] += 1
        bins[bi]["p_sum"] += p
        bins[bi]["y_sum"] += y

    brier /= max(1, len(test))
    ece = 0.0
    for b in bins:
        if b["n"] == 0:
            continue
        p_hat = b["p_sum"] / b["n"]
        y_hat = b["y_sum"] / b["n"]
        ece += (b["n"] / len(test)) * abs(p_hat - y_hat)

    print("=== CALIBRATION REPORT ===")
    print(f"Train size: {len(train)} | Test size: {len(test)}")
    print(f"Best slope (Brier train): {best_slope:.3f}")
    print(f"Test Brier: {brier:.5f}")
    print(f"Test ECE (10 bins): {ece:.5f}")


def run_clv_report(bets_csv: str) -> None:
    """Expected columns: timestamp,market,taken_odds,close_odds,stake,pnl."""
    p = Path(bets_csv)
    if not p.exists():
        raise FileNotFoundError(f"Missing bet log CSV: {bets_csv}")

    rows = list(csv.DictReader(p.read_text(encoding="utf-8").splitlines()))
    if not rows:
        print("Prázdný bet log.")
        return

    total_stake = 0.0
    total_pnl = 0.0
    clv_values: List[float] = []
    by_market: Dict[str, Dict[str, float]] = defaultdict(lambda: {"stake": 0.0, "pnl": 0.0, "clv_sum": 0.0, "n": 0})

    for r in rows:
        taken = safe_float(r.get("taken_odds"), 0.0)
        close = safe_float(r.get("close_odds"), 0.0)
        stake = safe_float(r.get("stake"), 0.0)
        pnl = safe_float(r.get("pnl"), 0.0)
        market = (r.get("market") or "unknown").strip()

        if taken <= 1.01 or close <= 1.01:
            continue

        # positive when we took a better price than close
        clv = (taken / close) - 1.0
        clv_values.append(clv)

        total_stake += stake
        total_pnl += pnl

        by_market[market]["stake"] += stake
        by_market[market]["pnl"] += pnl
        by_market[market]["clv_sum"] += clv
        by_market[market]["n"] += 1

    if not clv_values:
        print("Nenašel jsem validní řádky pro CLV (zkontroluj taken_odds/close_odds).")
        return

    roi = (total_pnl / total_stake) if total_stake else 0.0
    avg_clv = sum(clv_values) / len(clv_values)

    print("=== CLV REPORT ===")
    print(f"Počet sázek: {len(clv_values)}")
    print(f"Avg CLV: {avg_clv*100:.2f}%")
    print(f"ROI: {roi*100:.2f}%")
    print("\nBy market:")
    for m, vals in sorted(by_market.items(), key=lambda x: x[0]):
        n = int(vals["n"])
        if n == 0:
            continue
        m_roi = vals["pnl"] / vals["stake"] if vals["stake"] else 0.0
        m_clv = vals["clv_sum"] / n
        print(f"- {m:20} | n={n:4d} | CLV={m_clv*100:6.2f}% | ROI={m_roi*100:6.2f}%")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Edge research lab (intransitivity, calibration, CLV)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_in = sub.add_parser("intransitivity-backtest", help="Upset-lift check on intransitivity tags")
    p_in.add_argument("--csv-files", nargs="+", required=True)
    p_in.add_argument("--surface", choices=["Hard", "Clay", "Grass"], default=None)
    p_in.add_argument("--min-hist-matches", type=int, default=80)
    p_in.add_argument("--score-threshold", type=float, default=1.5)

    p_cal = sub.add_parser("calibration-report", help="Calibration report for rank-based probabilities")
    p_cal.add_argument("--csv-files", nargs="+", required=True)
    p_cal.add_argument("--surface", choices=["Hard", "Clay", "Grass"], default=None)
    p_cal.add_argument("--split", type=float, default=0.7)

    p_clv = sub.add_parser("clv-report", help="CLV/ROI summary from bet log")
    p_clv.add_argument("--bets-csv", required=True)

    return p


def main() -> None:
    p = build_parser()
    args = p.parse_args()

    if args.cmd == "clv-report":
        run_clv_report(args.bets_csv)
        return

    matches = load_match_obs(args.csv_files, surface=args.surface)
    if not matches:
        raise SystemExit("No matches loaded.")

    if args.cmd == "intransitivity-backtest":
        run_intransitivity_backtest(
            matches,
            min_hist_matches=args.min_hist_matches,
            score_threshold=args.score_threshold,
        )
    elif args.cmd == "calibration-report":
        run_calibration_report(matches, split_ratio=args.split)


if __name__ == "__main__":
    main()
