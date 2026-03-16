from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    tokens = [t for t in value.split() if t not in {"fc", "ac", "fk", "cf", "sk", "the"}]
    return " ".join(tokens)


def _event_key(match: ExportMatch) -> str:
    home = _normalize_text(match.home)
    away = _normalize_text(match.away)
    parts = sorted([home, away])
    return " vs ".join(parts)


def _event_similarity(a: ExportMatch, b: ExportMatch) -> float:
    return SequenceMatcher(None, _event_key(a), _event_key(b)).ratio()




def _to_utc_timestamp(dt: datetime) -> float:
    if dt.tzinfo is None:
        # treat naive timestamps as UTC to avoid local-time dependent matching
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.timestamp()


def _kickoff_score(a: ExportMatch, b: ExportMatch, tolerance_hours: float) -> float:
    if not a.start_time or not b.start_time:
        return 0.5
    delta_hours = abs(_to_utc_timestamp(a.start_time) - _to_utc_timestamp(b.start_time)) / 3600.0
def _kickoff_score(a: ExportMatch, b: ExportMatch, tolerance_hours: float) -> float:
    if not a.start_time or not b.start_time:
        return 0.5
    delta_hours = abs((a.start_time - b.start_time).total_seconds()) / 3600.0
    if delta_hours > tolerance_hours:
        return 0.0
    return max(0.0, 1.0 - (delta_hours / tolerance_hours))


def _within_kickoff_tolerance(a: ExportMatch, b: ExportMatch, tolerance_hours: float) -> bool:
    if not a.start_time or not b.start_time:
        return True
    delta_hours = abs(_to_utc_timestamp(a.start_time) - _to_utc_timestamp(b.start_time)) / 3600.0
    delta_hours = abs((a.start_time - b.start_time).total_seconds()) / 3600.0
    return delta_hours <= tolerance_hours


def _pair_score(a: ExportMatch, b: ExportMatch, kickoff_tolerance_hours: float) -> float:
    # prioritize team-name similarity; kickoff proximity is a tie-breaker
    sim = _event_similarity(a, b)
    return sim * 0.85 + _kickoff_score(a, b, kickoff_tolerance_hours) * 0.15


def _normalized_probabilities_from_odds(odds_1x2: Dict[str, float]) -> Dict[str, float]:
    inv = {k: 1 / v for k, v in odds_1x2.items()}
    total = sum(inv.values())
    return {k: v / total for k, v in inv.items()}


def match_events(
    target_matches: Iterable[ExportMatch],
    reference_matches: Iterable[ExportMatch],
    similarity_threshold: float = 0.68,
    kickoff_tolerance_hours: float = 24.0,
) -> List[tuple[ExportMatch, ExportMatch]]:
    refs = list(reference_matches)
    pairs: List[tuple[ExportMatch, ExportMatch]] = []
    used_refs: set[int] = set()

    for tm in target_matches:
        best_idx: Optional[int] = None
        best_score = 0.0

        for idx, rm in enumerate(refs):
            if idx in used_refs:
                continue
            if not _within_kickoff_tolerance(tm, rm, kickoff_tolerance_hours):
                continue
            score = _pair_score(tm, rm, kickoff_tolerance_hours)
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is not None and best_score >= similarity_threshold:
            used_refs.add(best_idx)
            pairs.append((tm, refs[best_idx]))

    return pairs


def find_value_bets(
    target_matches: Iterable[ExportMatch],
    reference_matches: Iterable[ExportMatch],
    min_edge_percent: float = 1.0,
    similarity_threshold: float = 0.68,
    kickoff_tolerance_hours: float = 24.0,
) -> List[ValueBet]:
    scored_bets: List[ValueBet] = []

    for target, reference in match_events(
        target_matches,
        reference_matches,
        similarity_threshold=similarity_threshold,
        kickoff_tolerance_hours=kickoff_tolerance_hours,
    ):
        needed = {"1", "X", "2"}
        if not needed.issubset(target.odds.keys()) or not needed.issubset(reference.odds.keys()):
            continue

        fair_probs = _normalized_probabilities_from_odds({k: reference.odds[k] for k in needed})

        for outcome in sorted(needed):
            target_odds = target.odds[outcome]
            fair_probability = fair_probs[outcome]
            ev = target_odds * fair_probability - 1
            edge_percent = ev * 100
            scored_bets.append(
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

    return sorted(
        [vb for vb in scored_bets if vb.edge_percent >= min_edge_percent],
        key=lambda x: x.edge_percent,
        reverse=True,
    )


def find_best_edges(
    target_matches: Iterable[ExportMatch],
    reference_matches: Iterable[ExportMatch],
    top: int = 20,
    similarity_threshold: float = 0.62,
    kickoff_tolerance_hours: float = 48.0,
) -> List[ValueBet]:
    """Return strongest price discrepancies even if they are below value-bet threshold."""
    bets = find_value_bets(
        target_matches,
        reference_matches,
        min_edge_percent=-100.0,
        similarity_threshold=similarity_threshold,
        kickoff_tolerance_hours=kickoff_tolerance_hours,
    )
    return bets[:top]
