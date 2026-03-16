#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], dry_run: bool = False) -> int:
    printable = " ".join(shlex.quote(c) for c in cmd)
    print(f"\n>>> {printable}")
    if dry_run:
        return 0
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def build_steps(args: argparse.Namespace) -> list[list[str]]:
    py = args.python
    node = args.node

    steps: list[list[str]] = []

    tipsport_cmd = [node, "scripts/tipsport2.js"]
    if args.tipsport_sport:
        tipsport_cmd.extend(["--sport", str(args.tipsport_sport)])
    if args.tipsport_details:
        tipsport_cmd.append("--details")
        if args.tipsport_details_limit and args.tipsport_details_limit > 0:
            tipsport_cmd.extend(["--limit", str(args.tipsport_details_limit)])
    tipsport_cmd.append("--json")
    steps.append(tipsport_cmd)

    betano_cmd = [node, "scripts/betano.js"]
    if args.betano_all:
        betano_cmd.append("--all")
    betano_cmd.append("--json")
    steps.append(betano_cmd)

    value_cmd = [
        py,
        "scripts/valuebets_tipsport_betano.py",
        "--tipsport",
        args.tipsport_json,
        "--betano",
        args.betano_json,
        "--target",
        args.target,
        "--min-edge",
        str(args.min_edge),
        "--top",
        str(args.top),
        "--fallback-top",
        str(args.fallback_top),
    ]
    steps.append(value_cmd)

    if args.run_snapshot:
        snapshot_cmd = [py, "main.py", "--iterations", "1", "--providers-file", args.providers_file]
        steps.append(snapshot_cmd)

    return steps


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-command pipeline: scrape Tipsport + Betano and evaluate value bets"
    )
    parser.add_argument("--python", default=sys.executable or "python3", help="Python interpreter")
    parser.add_argument("--node", default="node", help="Node.js executable")
    parser.add_argument("--tipsport-sport", default="16", help="Tipsport sport id (16=fotbal, 188=esport, all=all configured)")
    parser.add_argument("--tipsport-details", action="store_true", help="Fetch detailed match markets (cards/corners/etc.)")
    parser.add_argument("--tipsport-details-limit", type=int, default=30, help="Max number of matches for detail fetch")
    parser.add_argument("--tipsport-json", default="tipsport_odds.json", help="Tipsport output JSON path")
    parser.add_argument("--betano-json", default="betano_odds.json", help="Betano output JSON path")
    parser.add_argument("--betano-all", action="store_true", help="Disable Betano sport filter (include all available sports)")
    parser.add_argument("--target", choices=["tipsport", "betano"], default="tipsport")
    parser.add_argument("--min-edge", type=float, default=1.0)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--fallback-top", type=int, default=10, help="When no value-bets, print strongest discrepancies")
    parser.add_argument("--run-snapshot", action="store_true", help="Run one `main.py` snapshot at end")
    parser.add_argument("--providers-file", default="providers.json")
    parser.add_argument("--dry-run", action="store_true", help="Only print commands")
    args = parser.parse_args()

    print("=== LEFI ODDS AUTO PIPELINE ===")
    print("1) Tipsport scrape -> tipsport_odds.json")
    print("2) Betano scrape   -> betano_odds.json")
    print("3) Value-bet evaluation")

    for step in build_steps(args):
        code = _run(step, dry_run=args.dry_run)
        if code != 0:
            print(f"\nPipeline stopped: command failed with exit code {code}")
            return code

    print("\nPipeline finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
