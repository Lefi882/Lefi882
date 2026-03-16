from datetime import datetime

from odds.engine import detect_arbitrage, stakes_for_bankroll
from odds.models import MarketOdds


def test_detect_arbitrage_true() -> None:
    markets = [
        MarketOdds("e1", "A vs B", "football", "1X2", "Tipsport", datetime(2026, 2, 20, 18, 0), {"1": 2.5, "X": 3.6, "2": 3.6}),
        MarketOdds("e1", "A vs B", "football", "1X2", "Fortuna", datetime(2026, 2, 20, 18, 0), {"1": 2.6, "X": 3.5, "2": 3.5}),
    ]

    result = detect_arbitrage(markets)

    assert result.is_arbitrage is True
    assert result.implied_total < 1


def test_stakes_sum_to_bankroll() -> None:
    best = {"1": ("A", 2.5), "X": ("B", 3.6), "2": ("C", 3.6)}

    stakes = stakes_for_bankroll(1000, best)

    assert round(sum(stakes.values()), 5) == 1000
