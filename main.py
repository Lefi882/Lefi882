from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from odds.engine import detect_arbitrage, overround, stakes_for_bankroll
from odds.matching import best_prices_for_group, group_events
from odds.providers import fetch_offers


def run_snapshot(root: Path, bankroll: float, providers_file: str) -> list[dict]:
    offers = fetch_offers(root=root, sport="football", market="1X2", providers_file=providers_file)
    groups = group_events(offers)
    records: list[dict] = []

    print(f"\nSnapshot @ {datetime.utcnow().isoformat()}Z")
    print(f"Načteno nabídek: {len(offers)} | Spárovaných eventů: {len(groups)}")

    for group in groups:
        print(f"\nEvent: {group.canonical_name} | kickoff: {group.kickoff.isoformat()}")
        for offer in group.offers:
            print(f"- {offer.bookmaker:<10} overround: {overround(offer.outcomes):.4f}")

        best = best_prices_for_group(group)
        result = detect_arbitrage(
            [offer for offer in group.offers]
        )

        print("  Nejlepší kurzy:")
        for outcome, (bookmaker, price) in sorted(best.items()):
            print(f"  - {outcome}: {price:.2f} ({bookmaker})")
        print(f"  Arbitráž: {'ANO' if result.is_arbitrage else 'NE'} | implied={result.implied_total:.4f}")

        record = {
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "event": group.canonical_name,
            "kickoff": group.kickoff.isoformat(),
            "best_odds": {k: {"bookmaker": v[0], "price": v[1]} for k, v in best.items()},
            "implied_total": result.implied_total,
            "is_arbitrage": result.is_arbitrage,
        }

        if result.is_arbitrage:
            stakes = stakes_for_bankroll(bankroll, best)
            record["stakes"] = stakes

        records.append(record)

    return records


def append_snapshot(root: Path, rows: list[dict]) -> None:
    output_dir = root / "snapshots"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "pregame_offers.jsonl"
    with output_file.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pregame porovnání 1X2 kurzů")
    parser.add_argument("--bankroll", type=float, default=10000, help="Bankroll v Kč")
    parser.add_argument("--interval-sec", type=int, default=60, help="Interval stahování v sekundách")
    parser.add_argument("--iterations", type=int, default=1, help="Počet snapshotů (0 = nekonečně)")
    parser.add_argument("--providers-file", default="providers.json", help="Konfigurace providerů (JSON)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    iteration = 0

    while True:
        records = run_snapshot(root=root, bankroll=args.bankroll, providers_file=args.providers_file)
        append_snapshot(root=root, rows=records)

        iteration += 1
        if args.iterations != 0 and iteration >= args.iterations:
            break
        time.sleep(args.interval_sec)


if __name__ == "__main__":
    main()

