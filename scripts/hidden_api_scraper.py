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

TIPSPORT_FOOTBALL_URL = "https://www.tipsport.cz/rest/offer/v2/offer?limit=200"


class HiddenApiOddsScraper:
    """HTTP scraper for hidden bookmaker JSON endpoints."""

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
        except (URLError, TimeoutError, json.JSONDecodeError):
            return None

    def parse_generic_events(self, raw_data: dict[str, Any], bookmaker: str) -> list[dict[str, Any]]:
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

    def parse_tipsport_offer_v2(self, raw_data: dict[str, Any], bookmaker: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        for super_sport in raw_data.get("offerSuperSports", []):
            if super_sport.get("id", {}).get("superSportId") != 16:
                continue

            for tab in super_sport.get("tabs", []):
                if tab.get("matchView") != "WINNER_WHOLE_MATCH":
                    continue

                for competition in tab.get("offerCompetitionAnnuals", []):
                    for match in competition.get("matches", []):
                        if match.get("race") is True:
                            continue

                        odds_1x2: dict[str, float] = {}
                        for row in match.get("oppRows", []):
                            for odd_row in row.get("oppsTab", []):
                                if odd_row is None:
                                    continue
                                odd_type = odd_row.get("type")
                                if odd_type == "1":
                                    odds_1x2["1"] = odd_row.get("odd")
                                elif odd_type == "x":
                                    odds_1x2["X"] = odd_row.get("odd")
                                elif odd_type == "2":
                                    odds_1x2["2"] = odd_row.get("odd")

                        if set(odds_1x2.keys()) != {"1", "X", "2"}:
                            continue

                        events.append(
                            {
                                "event_id": str(match.get("id")),
                                "event_name": match.get("nameFull")
                                or f"{match.get('participantHome', '')} vs {match.get('participantVisiting', '')}",
                                "sport": "football",
                                "market": "1X2",
                                "kickoff": str(match.get("dateClosed", ""))
                                .replace(".000", "")
                                .strip(),
                                "odds": odds_1x2,
                                "bookmaker": bookmaker,
                            }
                        )
        return events

    def parse_payload(self, raw_data: dict[str, Any], bookmaker: str, feed_format: str = "auto") -> list[dict[str, Any]]:
        effective_format = feed_format
        if feed_format == "auto":
            effective_format = "tipsport_offer_v2" if "offerSuperSports" in raw_data else "events"

        if effective_format == "tipsport_offer_v2":
            return self.parse_tipsport_offer_v2(raw_data, bookmaker=bookmaker)
        return self.parse_generic_events(raw_data, bookmaker=bookmaker)


def scrape_with_delay(
    urls: list[str],
    bookmaker: str,
    feed_format: str = "auto",
    min_delay: float = 1.0,
    max_delay: float = 3.0,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    scraper = HiddenApiOddsScraper(timeout=timeout)
    normalized_events: list[dict[str, Any]] = []

    for url in urls:
        data = scraper.fetch_odds(url)
        if data:
            normalized_events.extend(
                scraper.parse_payload(data, bookmaker=bookmaker, feed_format=feed_format)
            )
        time.sleep(random.uniform(min_delay, max_delay))

    return normalized_events


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch bookmaker odds from hidden JSON endpoints.")
    parser.add_argument("--bookmaker", default="UnknownBookmaker")
    parser.add_argument("--url", action="append", default=[], help="Hidden API endpoint URL.")
    parser.add_argument(
        "--format",
        default="auto",
        choices=["auto", "events", "tipsport_offer_v2"],
        help="Format parser for returned JSON.",
    )
    parser.add_argument("--tipsport", action="store_true", help="Use Tipsport pregame endpoint preset.")
    parser.add_argument("--min-delay", type=float, default=1.0)
    parser.add_argument("--max-delay", type=float, default=2.5)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--output", default="data/hidden_api_events.json")
    args = parser.parse_args()

    urls = list(args.url)
    if args.tipsport:
        urls.append(TIPSPORT_FOOTBALL_URL)
        if args.bookmaker == "UnknownBookmaker":
            args.bookmaker = "Tipsport"
        if args.format == "auto":
            args.format = "tipsport_offer_v2"

    if not urls:
        raise SystemExit("No endpoints selected. Use --url or --tipsport.")

    events = scrape_with_delay(
        urls=urls,
        bookmaker=args.bookmaker,
        feed_format=args.format,
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
