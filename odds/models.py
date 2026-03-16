from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass(frozen=True)
class MarketOdds:
    event_id: str
    event_name: str
    sport: str
    market: str
    bookmaker: str
    kickoff: datetime
    outcomes: Dict[str, float]

