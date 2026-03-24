"""Edge research utility for tennis betting experiments.

This script provides three practical reports:
1) intransitivity-backtest - checks cyclical match-up effects (A > B > C > A)
2) calibration-report      - evaluates probabilistic calibration (Brier + ECE)
3) clv-report              - evaluates CLV and ROI from a bet log
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class IntransitivityRow:
    player_a: str
    player_b: str
    winner: str
    price_a: float | None
    price_b: float | None


@dataclass
class CalibRow:
    probability: float
    outcome: int


@dataclass
class BetRow:
    timestamp: str
    market: str
    taken_odds: float
    close_odds: float
    stake: float
    pnl: float


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    return float(v)


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def _implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError(f"Invalid decimal odds: {decimal_odds}")
    return 1.0 / decimal_odds


def _normalize_two_way_margin(prob_a: float, prob_b: float) -> tuple[float, float]:
    overround = prob_a + prob_b
    if overround <= 0:
        return 0.5, 0.5
    return prob_a / overround, prob_b / overround


def load_intransitivity_rows(path: Path) -> list[IntransitivityRow]:
    raw = _read_csv(path)
    rows: list[IntransitivityRow] = []
    for row in raw:
        pa = row.get("player_a") or row.get("player1") or row.get("home")
        pb = row.get("player_b") or row.get("player2") or row.get("away")
        winner = row.get("winner")
        if not pa or not pb or not winner:
            continue
        price_a = _to_float(row.get("odds_a") or row.get("price_a") or row.get("odds_player_a"))
        price_b = _to_float(row.get("odds_b") or row.get("price_b") or row.get("odds_player_b"))
        rows.append(
            IntransitivityRow(
                player_a=pa.strip(),
                player_b=pb.strip(),
                winner=winner.strip(),
                price_a=price_a,
                price_b=price_b,
            )
        )
    return rows


def build_win_graph(rows: list[IntransitivityRow], min_h2h_matches: int) -> tuple[set[str], dict[str, set[str]]]:
    pair_counter: Counter[tuple[str, str]] = Counter()
    win_counter: Counter[tuple[str, str]] = Counter()
    players: set[str] = set()

    for row in rows:
        a = row.player_a
        b = row.player_b
        w = row.winner
        players.update([a, b])
        pair = tuple(sorted((a, b)))
        pair_counter[pair] += 1
        if w == a:
            win_counter[(a, b)] += 1
        elif w == b:
            win_counter[(b, a)] += 1

    edges: dict[str, set[str]] = defaultdict(set)
    for (p1, p2), count in pair_counter.items():
        if count < min_h2h_matches:
            continue
        w12 = win_counter[(p1, p2)]
        w21 = win_counter[(p2, p1)]
        if w12 > w21:
            edges[p1].add(p2)
        elif w21 > w12:
            edges[p2].add(p1)
    return players, edges


def count_triads(players: set[str], edges: dict[str, set[str]]) -> tuple[int, int]:
    plist = sorted(players)
    triads_total = 0
    cyclical = 0

    for i in range(len(plist)):
        for j in range(i + 1, len(plist)):
            for k in range(j + 1, len(plist)):
                a, b, c = plist[i], plist[j], plist[k]
                directed_pairs = [
                    (a, b) if b in edges.get(a, set()) else (b, a) if a in edges.get(b, set()) else None,
                    (a, c) if c in edges.get(a, set()) else (c, a) if a in edges.get(c, set()) else None,
                    (b, c) if c in edges.get(b, set()) else (c, b) if b in edges.get(c, set()) else None,
                ]
                if any(x is None for x in directed_pairs):
                    continue
                triads_total += 1

                edge_set = {(u, v) for u, v in directed_pairs if u is not None and v is not None}
                if (a, b) in edge_set and (b, c) in edge_set and (c, a) in edge_set:
                    cyclical += 1
                elif (b, a) in edge_set and (c, b) in edge_set and (a, c) in edge_set:
                    cyclical += 1

    return triads_total, cyclical


def run_intransitivity_backtest(path: Path, min_h2h_matches: int, upset_odds_threshold: float) -> None:
    rows = load_intransitivity_rows(path)
    players, edges = build_win_graph(rows, min_h2h_matches=min_h2h_matches)
    triads_total, cyclical = count_triads(players, edges)

    upset_total = 0
    upset_hits = 0
    baseline_total = 0
    baseline_hits = 0

    for r in rows:
        if r.price_a is None or r.price_b is None:
            continue
        p_a_raw = _implied_probability(r.price_a)
        p_b_raw = _implied_probability(r.price_b)
        p_a_fair, p_b_fair = _normalize_two_way_margin(p_a_raw, p_b_raw)

        fav = r.player_a if p_a_fair >= p_b_fair else r.player_b
        dog = r.player_b if fav == r.player_a else r.player_a
        dog_odds = r.price_b if fav == r.player_a else r.price_a

        baseline_total += 1
        if r.winner == dog:
            baseline_hits += 1

        has_cycle_signal = fav in edges.get(dog, set())
        if has_cycle_signal and dog_odds is not None and dog_odds >= upset_odds_threshold:
            upset_total += 1
            if r.winner == dog:
                upset_hits += 1

    baseline_rate = baseline_hits / baseline_total if baseline_total else 0.0
    upset_rate = upset_hits / upset_total if upset_total else 0.0
    lift = upset_rate - baseline_rate

    print("=== Intransitivity backtest ===")
    print(f"Input file: {path}")
    print(f"Rows loaded: {len(rows)}")
    print(f"Players: {len(players)}")
    print(f"Resolved triads: {triads_total}")
    print(f"Cyclical triads: {cyclical} ({(cyclical / triads_total * 100) if triads_total else 0:.2f}%)")
    print("-")
    print(f"Baseline upset rate: {baseline_rate:.4f} ({baseline_hits}/{baseline_total})")
    print(
        f"Cycle-signal upset rate (odds >= {upset_odds_threshold:.2f}): "
        f"{upset_rate:.4f} ({upset_hits}/{upset_total})"
    )
    print(f"Upset lift vs baseline: {lift:+.4f}")


def load_calibration_rows(path: Path) -> list[CalibRow]:
    raw = _read_csv(path)
    out: list[CalibRow] = []
    for row in raw:
        p_raw = row.get("pred_prob") or row.get("probability") or row.get("p")
        y_raw = row.get("outcome") or row.get("label") or row.get("y")
        if p_raw is None or y_raw is None:
            continue
        p = float(p_raw)
        y = int(float(y_raw))
        if not (0 <= p <= 1):
            continue
        if y not in (0, 1):
            continue
        out.append(CalibRow(probability=p, outcome=y))
    return out


def expected_calibration_error(rows: list[CalibRow], bins: int = 10) -> float:
    if not rows:
        return 0.0
    buckets: list[list[CalibRow]] = [[] for _ in range(bins)]
    for r in rows:
        idx = min(int(r.probability * bins), bins - 1)
        buckets[idx].append(r)

    n = len(rows)
    ece = 0.0
    for bucket in buckets:
        if not bucket:
            continue
        conf = _mean(x.probability for x in bucket)
        acc = _mean(float(x.outcome) for x in bucket)
        ece += (len(bucket) / n) * abs(acc - conf)
    return ece


def run_calibration_report(path: Path, bins: int) -> None:
    rows = load_calibration_rows(path)
    if not rows:
        print("No usable rows found. Required columns: pred_prob/probability/p and outcome/label/y")
        return

    brier = _mean((r.probability - r.outcome) ** 2 for r in rows)
    ece = expected_calibration_error(rows, bins=bins)

    bucket_stats = []
    for b in range(bins):
        lo = b / bins
        hi = (b + 1) / bins
        seg = [r for r in rows if lo <= r.probability < hi or (b == bins - 1 and r.probability == 1.0)]
        if not seg:
            bucket_stats.append((b, 0, 0.0, 0.0))
            continue
        bucket_stats.append(
            (
                b,
                len(seg),
                _mean(r.probability for r in seg),
                _mean(float(r.outcome) for r in seg),
            )
        )

    print("=== Calibration report ===")
    print(f"Input file: {path}")
    print(f"Rows loaded: {len(rows)}")
    print(f"Brier score: {brier:.6f}")
    print(f"ECE ({bins} bins): {ece:.6f}")
    print("-")
    print("Bin\tCount\tAvgProb\tHitRate")
    for b, cnt, avg_p, hit in bucket_stats:
        print(f"{b:02d}\t{cnt}\t{avg_p:.4f}\t{hit:.4f}")


def load_bet_rows(path: Path) -> list[BetRow]:
    raw = _read_csv(path)
    out: list[BetRow] = []
    for row in raw:
        required = ["timestamp", "market", "taken_odds", "close_odds", "stake", "pnl"]
        if any(row.get(k) is None or str(row.get(k)).strip() == "" for k in required):
            continue
        out.append(
            BetRow(
                timestamp=row["timestamp"].strip(),
                market=row["market"].strip(),
                taken_odds=float(row["taken_odds"]),
                close_odds=float(row["close_odds"]),
                stake=float(row["stake"]),
                pnl=float(row["pnl"]),
            )
        )
    return out


def run_clv_report(path: Path) -> None:
    rows = load_bet_rows(path)
    if not rows:
        print("No usable rows found in bet log CSV.")
        return

    stakes = sum(r.stake for r in rows)
    pnl = sum(r.pnl for r in rows)
    roi = pnl / stakes if stakes else 0.0

    clv_pct_samples = []
    beat_close_count = 0
    for r in rows:
        clv_pct = (r.taken_odds / r.close_odds) - 1.0
        clv_pct_samples.append(clv_pct)
        if r.taken_odds > r.close_odds:
            beat_close_count += 1

    mean_clv = _mean(clv_pct_samples)
    beat_close_rate = beat_close_count / len(rows)

    by_market: dict[str, list[BetRow]] = defaultdict(list)
    for r in rows:
        by_market[r.market].append(r)

    print("=== CLV report ===")
    print(f"Input file: {path}")
    print(f"Bets: {len(rows)}")
    print(f"Turnover (sum stake): {stakes:.2f}")
    print(f"PnL: {pnl:.2f}")
    print(f"ROI: {roi * 100:.2f}%")
    print(f"Mean CLV%: {mean_clv * 100:.2f}%")
    print(f"Beat closing line rate: {beat_close_rate * 100:.2f}%")
    print("-")
    print("Market\tBets\tROI%\tMeanCLV%")
    for market, bets in sorted(by_market.items(), key=lambda x: x[0]):
        m_stake = sum(b.stake for b in bets)
        m_pnl = sum(b.pnl for b in bets)
        m_roi = (m_pnl / m_stake) if m_stake else 0.0
        m_clv = _mean((b.taken_odds / b.close_odds) - 1.0 for b in bets)
        print(f"{market}\t{len(bets)}\t{m_roi * 100:.2f}%\t{m_clv * 100:.2f}%")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Edge research lab utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("intransitivity-backtest", help="Backtest cyclical matchup signals")
    p1.add_argument("--matches", type=Path, required=True, help="CSV with player_a, player_b, winner, odds_a, odds_b")
    p1.add_argument("--min-h2h", type=int, default=2, help="Minimum H2H matches to define directed edge")
    p1.add_argument("--upset-odds-threshold", type=float, default=2.30, help="Only evaluate dogs above this odds")

    p2 = sub.add_parser("calibration-report", help="Brier + ECE report from predictions")
    p2.add_argument("--predictions", type=Path, required=True, help="CSV with pred_prob/probability/p and outcome/label/y")
    p2.add_argument("--bins", type=int, default=10, help="Number of ECE bins")

    p3 = sub.add_parser("clv-report", help="CLV + ROI report from bet log")
    p3.add_argument("--bets", type=Path, required=True, help="CSV with timestamp,market,taken_odds,close_odds,stake,pnl")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "intransitivity-backtest":
        run_intransitivity_backtest(
            path=args.matches,
            min_h2h_matches=args.min_h2h,
            upset_odds_threshold=args.upset_odds_threshold,
        )
    elif args.command == "calibration-report":
        run_calibration_report(path=args.predictions, bins=args.bins)
    elif args.command == "clv-report":
        run_clv_report(path=args.bets)
    else:
        raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
