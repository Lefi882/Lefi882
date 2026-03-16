from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, Iterable, List

from odds.models import MarketOdds


TOKEN_REPLACEMENTS = {
    "praha": "",
    "prague": "",
    "fc": "",
    "ac": "",
    "viktoria": "",
    "banik": "banik",
    "plzen": "plzen",
    "plzen": "plzen",
}


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace(" vs ", " v ").replace(" - ", " v ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    tokens = [token for token in re.split(r"\s+", value) if token and token != "v"]

    normalized_tokens: list[str] = []
    for token in tokens:
        replaced = TOKEN_REPLACEMENTS.get(token, token)
        if replaced:
            normalized_tokens.append(replaced)

    normalized_tokens.sort()
    return " ".join(normalized_tokens)


def _event_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()


@dataclass
class MatchedEvent:
    canonical_name: str
    kickoff: datetime
    offers: List[MarketOdds]


def group_events(
    offers: Iterable[MarketOdds],
    similarity_threshold: float = 0.72,
    kickoff_tolerance_minutes: int = 15,
) -> List[MatchedEvent]:
    grouped: List[MatchedEvent] = []
    tolerance = timedelta(minutes=kickoff_tolerance_minutes)

    for offer in sorted(offers, key=lambda x: x.kickoff):
        assigned = False
        for group in grouped:
            name_similarity = _event_similarity(offer.event_name, group.canonical_name)
            kickoff_ok = abs(offer.kickoff - group.kickoff) <= tolerance
            if name_similarity >= similarity_threshold and kickoff_ok:
                group.offers.append(offer)
                assigned = True
                break
        if not assigned:
            grouped.append(MatchedEvent(canonical_name=offer.event_name, kickoff=offer.kickoff, offers=[offer]))

    return grouped


def best_prices_for_group(group: MatchedEvent) -> Dict[str, tuple[str, float]]:
    best: Dict[str, tuple[str, float]] = {}
    for offer in group.offers:
        for outcome, price in offer.outcomes.items():
            prev = best.get(outcome)
            if prev is None or price > prev[1]:
                best[outcome] = (offer.bookmaker, price)
    return best

