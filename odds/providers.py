from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from odds.models import MarketOdds

def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class JsonBookmakerProvider:
    def __init__(
        self,
        bookmaker: str,
        data_path: Optional[Path] = None,
        source_url: Optional[str] = None,
        feed_format: str = "events",
    ) -> None:
        self.bookmaker = bookmaker
        self.data_path = data_path
        self.source_url = source_url
        self.feed_format = feed_format

    def _read_payload(self) -> dict:
        if self.source_url:
            request = Request(
                self.source_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (odds-mvp-fetcher)",
                    "Accept": "application/json,text/plain,*/*",
                },
            )
            try:
                with urlopen(request, timeout=15) as response:
                    return json.loads(response.read().decode("utf-8"))
            except URLError as exc:
                raise RuntimeError(f"Failed to fetch {self.bookmaker} from URL: {self.source_url}") from exc

        if self.data_path is None:
            raise ValueError(f"Provider {self.bookmaker} missing both source_url and data_path")

        return json.loads(self.data_path.read_text(encoding="utf-8"))

    def _parse_events_format(self, payload: dict, sport: str, market: str) -> List[MarketOdds]:
        events = payload.get("events", [])
        markets: List[MarketOdds] = []
        for event in events:
            if event.get("sport", "football") != sport:
                continue
            markets.append(
                MarketOdds(
                    event_id=event["event_id"],
                    event_name=event["event_name"],
                    sport=event.get("sport", "football"),
                    market=event.get("market", market),
                    bookmaker=self.bookmaker,
                    kickoff=_parse_dt(event["kickoff"]),
                    outcomes=event["odds"],
                )
            )
        return markets

    def _parse_tipsport_offer_v2(self, payload: dict, sport: str, market: str) -> List[MarketOdds]:
        if sport != "football" or market != "1X2":
            return []

        markets: List[MarketOdds] = []
        for super_sport in payload.get("offerSuperSports", []):
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
                                if odd_type in {"1", "x", "2"}:
                                    odds_1x2[odd_type.upper() if odd_type == "x" else odd_type] = odd_row["odd"]

                        if set(odds_1x2.keys()) != {"1", "X", "2"}:
                            continue

                        markets.append(
                            MarketOdds(
                                event_id=str(match["id"]),
                                event_name=match.get("nameFull")
                                or f"{match.get('participantHome', '')} vs {match.get('participantVisiting', '')}",
                                sport="football",
                                market="1X2",
                                bookmaker=self.bookmaker,
                                kickoff=_parse_dt(match["dateClosed"].replace(".000", "")),
                                outcomes=odds_1x2,
                            )
                        )
        return markets

    def fetch_all(self, sport: str = "football", market: str = "1X2") -> List[MarketOdds]:
        payload = self._read_payload()

        if self.feed_format == "tipsport_offer_v2":
            return self._parse_tipsport_offer_v2(payload, sport, market)
        return self._parse_events_format(payload, sport, market)


def _load_providers_from_json(root: Path, providers_file: Path) -> List[JsonBookmakerProvider]:
    payload = json.loads(providers_file.read_text(encoding="utf-8"))
    providers: List[JsonBookmakerProvider] = []
    for entry in payload.get("providers", []):
        providers.append(
            JsonBookmakerProvider(
                bookmaker=entry["bookmaker"],
                data_path=(root / entry["data_file"]) if entry.get("data_file") else None,
                source_url=entry.get("source_url"),
                feed_format=entry.get("format", "events"),
            )
        )
    return providers


def load_default_providers(root: Path, providers_file: str = "providers.json") -> Iterable[JsonBookmakerProvider]:
    config_path = root / providers_file
    if config_path.exists():
        return _load_providers_from_json(root, config_path)

    return [
        JsonBookmakerProvider("Tipsport", data_path=root / "data" / "tipsport.json"),
        JsonBookmakerProvider("Fortuna", data_path=root / "data" / "fortuna.json"),
        JsonBookmakerProvider("Allwyn", data_path=root / "data" / "allwyn.json"),
        JsonBookmakerProvider("BetanoCZ", data_path=root / "data" / "betanocz.json"),
    ]


def fetch_offers(
    root: Path,
    sport: str = "football",
    market: str = "1X2",
    providers_file: str = "providers.json",
) -> List[MarketOdds]:
    markets: List[MarketOdds] = []
    for provider in load_default_providers(root, providers_file=providers_file):
        markets.extend(provider.fetch_all(sport=sport, market=market))
    return markets
