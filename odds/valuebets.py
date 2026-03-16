from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ExportMatch:
    bookmaker: str
    home: str
    away: str
    start_time: Optional[datetime]
    odds: Dict[str, float]


@dataclass(frozen=True)
class ValueBet:
    outcome: str
    event: str
    kickoff: Optional[datetime]
    target_bookmaker: str
    reference_bookmaker: str
    target_odds: float
    reference_odds: float
    fair_probability: float
    edge_percent: float
    ratio: float


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    tokens = [t for t in value.split() if t not in {"fc", "ac", "fk", "cf", "sk"}]
    return " ".join(tokens)


def _event_key(match: ExportMatch) -> str:
    home = _normalize_text(match.home)
    away = _normalize_text(match.away)
    parts = sorted([home, away])
    return " vs ".join(parts)


def _event_similarity(a: ExportMatch, b: ExportMatch) -> float:
    return SequenceMatcher(None, _event_key(a), _event_key(b)).ratio()


def _normalized_probabilities_from_odds(odds_1x2: Dict[str, float]) -> Dict[str, float]:
    inv = {k: 1 / v for k, v in odds_1x2.items()}
    total = sum(inv.values())
    return {k: v / total for k, v in inv.items()}


def match_events(
    target_matches: Iterable[ExportMatch],
    reference_matches: Iterable[ExportMatch],
    similarity_threshold: float = 0.72,
) -> List[tuple[ExportMatch, ExportMatch]]:
    refs = list(reference_matches)
    pairs: List[tuple[ExportMatch, ExportMatch]] = []

    for tm in target_matches:
        best: Optional[ExportMatch] = None
        best_score = 0.0
        for rm in refs:
            score = _event_similarity(tm, rm)
            if score > best_score:
                best_score = score
                best = rm
        if best and best_score >= similarity_threshold:
            pairs.append((tm, best))
    return pairs


def find_value_bets(
    target_matches: Iterable[ExportMatch],
    reference_matches: Iterable[ExportMatch],
    min_edge_percent: float = 1.0,
) -> List[ValueBet]:
    value_bets: List[ValueBet] = []

    for target, reference in match_events(target_matches, reference_matches):
        needed = {"1", "X", "2"}
        if not needed.issubset(target.odds.keys()) or not needed.issubset(reference.odds.keys()):
            continue

        fair_probs = _normalized_probabilities_from_odds({k: reference.odds[k] for k in needed})

        for outcome in sorted(needed):
            target_odds = target.odds[outcome]
            fair_probability = fair_probs[outcome]
            ev = target_odds * fair_probability - 1
            edge_percent = ev * 100
            if edge_percent < min_edge_percent:
                continue
            value_bets.append(
                ValueBet(
                    outcome=outcome,
                    event=f"{target.home} vs {target.away}",
                    kickoff=target.start_time,
                    target_bookmaker=target.bookmaker,
                    reference_bookmaker=reference.bookmaker,
                    target_odds=target_odds,
                    reference_odds=reference.odds[outcome],
                    fair_probability=fair_probability,
                    edge_percent=edge_percent,
                    ratio=target_odds / reference.odds[outcome],
                )
            )

    return sorted(value_bets, key=lambda x: x.edge_percent, reverse=True)
