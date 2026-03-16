from datetime import datetime

from odds.matching import group_events
from odds.models import MarketOdds


def test_group_events_pairs_name_variants() -> None:
    offers = [
        MarketOdds("a", "Sparta Praha vs Slavia Praha", "football", "1X2", "Tipsport", datetime(2026, 2, 20, 18, 0), {"1": 2.3, "X": 3.5, "2": 3.1}),
        MarketOdds("b", "AC Sparta Praha v Slavia Praha", "football", "1X2", "Fortuna", datetime(2026, 2, 20, 18, 6), {"1": 2.4, "X": 3.4, "2": 3.0}),
        MarketOdds("c", "Plzen vs Banik Ostrava", "football", "1X2", "Allwyn", datetime(2026, 2, 21, 16, 0), {"1": 1.9, "X": 3.6, "2": 4.0}),
    ]

    groups = group_events(offers)

    assert len(groups) == 2
    sizes = sorted(len(group.offers) for group in groups)
    assert sizes == [1, 2]
