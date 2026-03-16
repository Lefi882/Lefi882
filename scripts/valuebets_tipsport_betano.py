#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from odds.valuebets import ExportMatch, find_best_edges, find_value_bets


def parse_start_time(value):
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        # Betano exports often use unix milliseconds
        ts = float(value)
        if ts > 10_000_000_000:  # looks like milliseconds
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00").replace(".000", ""))
        except ValueError:
            return None

    return None


def load_export(path: Path, bookmaker: str) -> list[ExportMatch]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    matches = payload.get("matches", [])
    out: list[ExportMatch] = []
    for m in matches:
        odds = m.get("odds", {})
        if not isinstance(odds, dict):
            continue
        out.append(
            ExportMatch(
                bookmaker=bookmaker,
                home=str(m.get("home", "")).strip(),
                away=str(m.get("away", "")).strip(),
                start_time=parse_start_time(m.get("startTime")),
                odds={str(k): float(v) for k, v in odds.items() if isinstance(v, (int, float))},
            )
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Value bet evaluator: Tipsport vs Betano")
    parser.add_argument("--tipsport", default="tipsport_odds.json", help="Path to Tipsport export JSON")
    parser.add_argument("--betano", default="betano_odds.json", help="Path to Betano export JSON")
    parser.add_argument("--target", choices=["tipsport", "betano"], default="tipsport", help="Bookmaker where we want to place value bets")
    parser.add_argument("--min-edge", type=float, default=1.0, help="Minimum edge percent")
    parser.add_argument("--top", type=int, default=20, help="Maximum rows to print")
    parser.add_argument("--fallback-top", type=int, default=10, help="If no value-bets, print top discrepancies")
    args = parser.parse_args()

    tipsport = load_export(Path(args.tipsport), "Tipsport")
    betano = load_export(Path(args.betano), "Betano")

    if args.target == "tipsport":
        target, reference = tipsport, betano
    else:
        target, reference = betano, tipsport

    value_bets = find_value_bets(target, reference, min_edge_percent=args.min_edge)

    print(f"Loaded: Tipsport={len(tipsport)} matches, Betano={len(betano)} matches")
    print(f"Target bookmaker: {args.target.title()} | min_edge={args.min_edge:.2f}%")
    print(f"Found value bets: {len(value_bets)}\n")

    rows = value_bets[: args.top]
    if not rows and args.fallback_top > 0:
        rows = find_best_edges(target, reference, top=args.fallback_top)
        if rows:
            print(
                "No bets passed min-edge threshold; showing strongest discrepancies instead "
                f"(top {len(rows)}).\n"
            )

    for vb in rows:
        ko = vb.kickoff.isoformat() if vb.kickoff else "?"
        print(
            f"[{vb.edge_percent:6.2f}%] {vb.event} | {vb.outcome} | "
            f"{vb.target_bookmaker}={vb.target_odds:.2f} vs {vb.reference_bookmaker}={vb.reference_odds:.2f} "
            f"| ratio={vb.ratio:.3f} | kickoff={ko}"
        )


if __name__ == "__main__":
    main()
