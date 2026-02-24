"""Jednoduchý model pro odhad pravděpodobnosti vítězství v tenise.

Model je záměrně transparentní: kombinuje několik faktorů do skóre,
které převádí na pravděpodobnost přes logistickou funkci.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp


@dataclass
class PlayerFeatures:
    name: str
    elo_surface: float  # ELO na povrchu turnaje
    recent_form: float  # 0..1 (posledních 5-10 zápasů)
    fatigue: float  # 0..1 (1 = velká únava)
    ace_rate: float  # esa na servis game
    return_points_won: float  # 0..1
    pressure_index: float  # 0..1 (výkon v TB / break pointech)


@dataclass
class MatchContext:
    importance: float  # 0..1 (finále > první kolo)
    weather_impact: float  # -1..1, + pomáhá hráči A
    speed_index: float  # -1..1, + rychlejší podmínky (hala/rychlý hard)


@dataclass
class Weights:
    elo: float = 0.006
    form: float = 1.2
    fatigue: float = 1.1
    ace_surface: float = 0.6
    return_skill: float = 1.0
    pressure: float = 0.5
    importance: float = 0.4
    weather: float = 0.35


def logistic(x: float) -> float:
    return 1.0 / (1.0 + exp(-x))


def estimate_win_probability(
    a: PlayerFeatures,
    b: PlayerFeatures,
    ctx: MatchContext,
    w: Weights = Weights(),
) -> float:
    """Vrátí P(výhra hráče A)."""
    elo_component = w.elo * (a.elo_surface - b.elo_surface)
    form_component = w.form * (a.recent_form - b.recent_form)
    fatigue_component = -w.fatigue * (a.fatigue - b.fatigue)

    # Výhoda esa je silnější v rychlých podmínkách.
    ace_delta = (a.ace_rate - b.ace_rate) * (1 + 0.6 * ctx.speed_index)
    ace_component = w.ace_surface * ace_delta

    return_component = w.return_skill * (a.return_points_won - b.return_points_won)
    pressure_component = w.pressure * (a.pressure_index - b.pressure_index) * (1 + 0.5 * ctx.importance)

    context_component = w.importance * ctx.importance + w.weather * ctx.weather_impact

    score = (
        elo_component
        + form_component
        + fatigue_component
        + ace_component
        + return_component
        + pressure_component
        + context_component
    )

    return logistic(score)


def demo() -> None:
    player_a = PlayerFeatures(
        name="Hráč A",
        elo_surface=1890,
        recent_form=0.72,
        fatigue=0.35,
        ace_rate=0.72,
        return_points_won=0.39,
        pressure_index=0.63,
    )
    player_b = PlayerFeatures(
        name="Hráč B",
        elo_surface=1850,
        recent_form=0.66,
        fatigue=0.44,
        ace_rate=0.55,
        return_points_won=0.37,
        pressure_index=0.57,
    )
    context = MatchContext(
        importance=0.55,
        weather_impact=0.10,
        speed_index=0.35,
    )

    p = estimate_win_probability(player_a, player_b, context)
    print(f"P({player_a.name} vyhraje) = {p:.3f}")


if __name__ == "__main__":
    demo()
