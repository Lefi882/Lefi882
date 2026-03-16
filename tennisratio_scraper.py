"""Scrape TennisRatio ATP/WTA analysis tables to local CSV files.

Usage:
  python3 tennisratio_scraper.py --tour atp
  python3 tennisratio_scraper.py --tour wta
  python3 tennisratio_scraper.py --tour both --out-dir data/tennisratio
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List
from urllib.request import urlopen
from urllib.error import URLError

ANALYSIS_URLS = {
    "atp": "https://www.tennisratio.com/analysis-atp.html",
    "wta": "https://www.tennisratio.com/analysis-wta.html",
}


def _extract_tables(html: str) -> List[List[List[str]]]:
    # lightweight HTML table extraction to avoid third-party dependencies
    tables: List[List[List[str]]] = []
    lower = html.lower()
    pos = 0
    while True:
        t0 = lower.find("<table", pos)
        if t0 == -1:
            break
        t1 = lower.find("</table>", t0)
        if t1 == -1:
            break
        table_html = html[t0 : t1 + len("</table>")]
        pos = t1 + len("</table>")

        rows: List[List[str]] = []
        rpos = 0
        table_lower = table_html.lower()
        while True:
            tr0 = table_lower.find("<tr", rpos)
            if tr0 == -1:
                break
            tr1 = table_lower.find("</tr>", tr0)
            if tr1 == -1:
                break
            tr_html = table_html[tr0 : tr1 + len("</tr>")]
            rpos = tr1 + len("</tr>")

            cells: List[str] = []
            cpos = 0
            tr_lower = tr_html.lower()
            while True:
                td0 = tr_lower.find("<td", cpos)
                th0 = tr_lower.find("<th", cpos)
                if td0 == -1 and th0 == -1:
                    break
                if td0 == -1 or (th0 != -1 and th0 < td0):
                    c0 = th0
                    tag = "th"
                else:
                    c0 = td0
                    tag = "td"
                c1 = tr_lower.find(f"</{tag}>", c0)
                if c1 == -1:
                    break
                gt = tr_html.find(">", c0)
                if gt == -1:
                    break
                text = tr_html[gt + 1 : c1]
                text = " ".join(text.replace("&nbsp;", " ").split())
                cells.append(text)
                cpos = c1 + len(f"</{tag}>")

            if cells:
                rows.append(cells)

        if rows:
            tables.append(rows)

    return tables


def _best_table(tables: List[List[List[str]]]) -> List[List[str]]:
    # pick the widest non-trivial table
    best = []
    best_score = -1
    for t in tables:
        width = max((len(r) for r in t), default=0)
        score = width * len(t)
        if score > best_score and width >= 4 and len(t) >= 5:
            best = t
            best_score = score
    return best


def scrape_analysis(tour: str) -> List[Dict[str, str]]:
    url = ANALYSIS_URLS[tour]
    try:
        with urlopen(url, timeout=30) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except URLError as e:
        raise RuntimeError(f"Failed to download {url}: {e}") from e

    tables = _extract_tables(html)
    table = _best_table(tables)
    if not table:
        raise RuntimeError(f"No usable table found for {tour.upper()} at {url}")

    header = table[0]
    data_rows = table[1:]
    normalized: List[Dict[str, str]] = []
    for row in data_rows:
        if len(row) < 2:
            continue
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        normalized.append({header[i]: row[i] for i in range(len(header))})
    return normalized


def write_csv(rows: List[Dict[str, str]], path: Path) -> None:
    if not rows:
        raise RuntimeError("No rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape TennisRatio analysis tables to CSV")
    ap.add_argument("--tour", choices=["atp", "wta", "both"], default="both")
    ap.add_argument("--out-dir", default="data/tennisratio")
    args = ap.parse_args()

    tours = ["atp", "wta"] if args.tour == "both" else [args.tour]
    for t in tours:
        rows = scrape_analysis(t)
        out = Path(args.out_dir) / f"tennisratio_{t}_analysis.csv"
        write_csv(rows, out)
        print(f"{t.upper()}: {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
