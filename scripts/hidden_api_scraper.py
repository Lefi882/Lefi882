from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class HiddenApiOddsScraper:
    """Simple HTTP scraper for bookmaker hidden JSON endpoints."""

    def __init__(self, timeout: int = 10) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
        }
        self.timeout = timeout

    def fetch_odds(self, api_url: str) -> dict[str, Any] | None:
        try:
            request = Request(api_url, headers=self.headers)
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, json.JSONDecodeError):
            return None

    def parse_events(self, raw_data: dict[str, Any], bookmaker: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for index, match in enumerate(raw_data.get("events", [])):
            odds = match.get("odds", {}).get("h2h", [])
            event = {
                "event_id": str(match.get("id") or match.get("event_id") or f"{bookmaker}-{index}"),
                "event_name": f"{match.get('home', 'Unknown')} vs {match.get('away', 'Unknown')}",
                "sport": match.get("sport", "football"),
                "market": "1X2",
                "kickoff": match.get("commence_time") or datetime.utcnow().isoformat(),
                "odds": {
                    "1": odds[0] if len(odds) > 0 else None,
                    "X": odds[1] if len(odds) > 2 else None,
                    "2": odds[-1] if len(odds) > 1 else None,
                },
            }
            if event["odds"]["1"] and event["odds"]["2"]:
                events.append(event)
        return events


def scrape_with_delay(
    urls: list[str],
    bookmaker: str,
    min_delay: float = 1.0,
    max_delay: float = 3.0,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    scraper = HiddenApiOddsScraper(timeout=timeout)
    normalized_events: list[dict[str, Any]] = []

    for url in urls:
        data = scraper.fetch_odds(url)
        if data:
            normalized_events.extend(scraper.parse_events(data, bookmaker=bookmaker))
        time.sleep(random.uniform(min_delay, max_delay))

    return normalized_events


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch bookmaker odds from hidden JSON endpoints.")
    parser.add_argument("--bookmaker", default="UnknownBookmaker")
    parser.add_argument("--url", action="append", required=True, help="Hidden API endpoint URL.")
    parser.add_argument("--min-delay", type=float, default=1.0)
    parser.add_argument("--max-delay", type=float, default=2.5)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--output", default="data/hidden_api_events.json")
    args = parser.parse_args()

    events = scrape_with_delay(
        urls=args.url,
        bookmaker=args.bookmaker,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        timeout=args.timeout,
    )

    payload = {"events": events, "scraped_at": datetime.utcnow().isoformat()}
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved {len(events)} events to {output_path}")


if __name__ == "__main__":
    main()
