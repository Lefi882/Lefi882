from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from odds.models import MarketOdds


@dataclass(frozen=True)
class ArbitrageResult:
    is_arbitrage: bool
    implied_total: float
    best_odds: Dict[str, Tuple[str, float]]


def overround(odds: Dict[str, float]) -> float:
    return sum(1 / price for price in odds.values())


def best_prices(markets: Iterable[MarketOdds]) -> Dict[str, Tuple[str, float]]:
    best: Dict[str, Tuple[str, float]] = {}
    for market in markets:
        for outcome, price in market.outcomes.items():
            current = best.get(outcome)
            if current is None or price > current[1]:
                best[outcome] = (market.bookmaker, price)
    return best


def detect_arbitrage(markets: Iterable[MarketOdds]) -> ArbitrageResult:
    best = best_prices(markets)
    total = sum(1 / price for _, price in best.values())
    return ArbitrageResult(is_arbitrage=total < 1, implied_total=total, best_odds=best)


def stakes_for_bankroll(bankroll: float, best_odds: Dict[str, Tuple[str, float]]) -> Dict[str, float]:
    denominator = sum(1 / price for _, price in best_odds.values())
    return {
        outcome: bankroll * ((1 / price) / denominator)
        for outcome, (_, price) in best_odds.items()
    }

