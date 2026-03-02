"""Interaktivní CLI appka pro odhad pravděpodobnosti tenisového zápasu."""

from __future__ import annotations

from tenis_probability_model import (
    MatchContext,
    PlayerFeatures,
    Weights,
    estimate_win_probability,
)


def ask_float(prompt: str, min_value: float | None = None, max_value: float | None = None) -> float:
    while True:
        raw = input(prompt).strip().replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            print("❌ Zadej číslo.")
            continue

        if min_value is not None and value < min_value:
            print(f"❌ Hodnota musí být >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"❌ Hodnota musí být <= {max_value}.")
            continue
        return value


def ask_player(name_label: str) -> PlayerFeatures:
    print(f"\n--- {name_label} ---")
    name = input("Jméno hráče: ").strip() or name_label
    elo_surface = ask_float("ELO na povrchu (např. 1750): ")
    recent_form = ask_float("Forma 0-1 (např. 0.65): ", 0, 1)
    fatigue = ask_float("Únava 0-1 (1 = velká únava): ", 0, 1)
    ace_rate = ask_float("Esa na servis game (např. 0.55): ", 0)
    return_points_won = ask_float("Vyhrané return pointy 0-1 (např. 0.38): ", 0, 1)
    pressure_index = ask_float("Pressure index 0-1 (TB/break pointy): ", 0, 1)

    return PlayerFeatures(
        name=name,
        elo_surface=elo_surface,
        recent_form=recent_form,
        fatigue=fatigue,
        ace_rate=ace_rate,
        return_points_won=return_points_won,
        pressure_index=pressure_index,
    )


def ask_context() -> MatchContext:
    print("\n--- Kontext zápasu ---")
    importance = ask_float("Důležitost zápasu 0-1 (finále ~ 1): ", 0, 1)
    weather_impact = ask_float("Počasí (-1 až 1, + pomáhá hráči 1): ", -1, 1)
    speed_index = ask_float("Rychlost podmínek (-1 až 1, + rychlé): ", -1, 1)

    return MatchContext(
        importance=importance,
        weather_impact=weather_impact,
        speed_index=speed_index,
    )


def run_app() -> None:
    print("=== Tenis predikce (CLI appka) ===")
    print("Zadej parametry pro 2 hráče a kontext zápasu.\n")

    player1 = ask_player("Hráč 1")
    player2 = ask_player("Hráč 2")
    context = ask_context()

    p1 = estimate_win_probability(player1, player2, context, Weights())
    p2 = 1 - p1

    print("\n=== Odhad výsledku ===")
    print(f"{player1.name}: {p1 * 100:.1f} %")
    print(f"{player2.name}: {p2 * 100:.1f} %")


if __name__ == "__main__":
    run_app()
