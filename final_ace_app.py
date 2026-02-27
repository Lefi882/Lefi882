"""Final GUI app: choose tournament + players and click compute aces."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import Dict, List

from ace_engine import load_rows, estimate_aces_for_match, ranked_player_pool
from ace_engine import load_rows, estimate_aces_for_match


@dataclass(frozen=True)
class TournamentProfile:
    name: str
    tour: str
    surface: str
    boost: float


TOURNAMENTS = [
    TournamentProfile("Mérida Open Akron", "wta", "Hard", 1.03),
    TournamentProfile("Guadalajara Open", "wta", "Hard", 1.04),
    TournamentProfile("Dubai", "atp", "Hard", 1.08),
    TournamentProfile("Acapulco (Abierto Mexicano)", "atp", "Hard", 1.06),
    TournamentProfile("Los Cabos", "atp", "Hard", 1.05),
    TournamentProfile("Indian Wells", "atp", "Hard", 0.98),
    TournamentProfile("Miami Open", "atp", "Hard", 1.01),
    TournamentProfile("Madrid", "atp", "Clay", 0.90),
    TournamentProfile("Rome", "atp", "Clay", 0.86),
    TournamentProfile("Roland Garros", "atp", "Clay", 0.84),
    TournamentProfile("Wimbledon", "atp", "Grass", 1.18),
    TournamentProfile("US Open", "atp", "Hard", 1.02),
]


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FINAL ACE APP")
        self.geometry("760x520")

        self.rows_by_tour: Dict[str, List[Dict[str, str]]] = {}

        self.tournament_var = tk.StringVar(value=TOURNAMENTS[0].name)
        self.player_a_var = tk.StringVar()
        self.player_b_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.result_var = tk.StringVar(value="Vyber turnaj a hráče, pak klikni VYPOČTI ESA.")

        ttk.Label(self, text="Turnaj:").pack(anchor="w", padx=12, pady=(12, 2))
        self.tournament_box = ttk.Combobox(self, textvariable=self.tournament_var, values=[t.name for t in TOURNAMENTS], state="readonly")
        self.tournament_box.pack(fill="x", padx=12)

        ttk.Button(self, text="1) Načti hráče pro turnaj", command=self.load_players).pack(fill="x", padx=12, pady=8)

        self.players_list: List[str] = []
        self.player_a_box = ttk.Combobox(self, textvariable=self.player_a_var, values=self.players_list)
        self.player_b_box = ttk.Combobox(self, textvariable=self.player_b_var, values=self.players_list)

        ttk.Label(self, text="Hráč A:").pack(anchor="w", padx=12)
        self.player_a_box.pack(fill="x", padx=12)
        ttk.Label(self, text="Hráč B:").pack(anchor="w", padx=12, pady=(8, 0))
        self.player_b_box.pack(fill="x", padx=12)

        ttk.Button(self, text="2) VYPOČTI ESA", command=self.compute).pack(fill="x", padx=12, pady=12)

        ttk.Label(self, text="Výsledek:").pack(anchor="w", padx=12)
        ttk.Label(self, textvariable=self.result_var, justify="left", wraplength=720).pack(anchor="w", padx=12, pady=8)
        ttk.Label(self, textvariable=self.status_var).pack(anchor="w", padx=12, pady=(16, 0))

    def selected_tournament(self) -> TournamentProfile:
        for t in TOURNAMENTS:
            if t.name == self.tournament_var.get():
                return t
        return TOURNAMENTS[0]

    def load_players(self) -> None:
        t = self.selected_tournament()
        self.status_var.set(f"Načítám data pro {t.name} ({t.tour.upper()})...")
        self.update_idletasks()

        if t.tour not in self.rows_by_tour:
            # Primary mode: fetch broad recent history to get a rich player pool.
            rows = load_rows(t.tour, years=[2022, 2023, 2024, 2025, 2026], csv_files=[])
            self.rows_by_tour[t.tour] = rows

        rows = self.rows_by_tour[t.tour]
        names = ranked_player_pool(rows, t.tour, limit=200)
        if len(names) < 20:
            # likely offline / blocked fetch => sample fallback already used by engine
            self.status_var.set("Pozn.: běží fallback data (málo hráčů). Zkus internet pro top 200.")
            csv_files = ["sample_wta_matches.csv"] if t.tour == "wta" else ["sample_atp_matches.csv"]
            rows = load_rows(t.tour, years=[2023, 2024, 2025, 2026], csv_files=csv_files)
            self.rows_by_tour[t.tour] = rows

        rows = self.rows_by_tour[t.tour]
        names = sorted({r.get("winner_name") for r in rows if r.get("winner_name")} | {r.get("loser_name") for r in rows if r.get("loser_name")})
        self.players_list = names
        self.player_a_box["values"] = names
        self.player_b_box["values"] = names

        if len(names) >= 2:
            self.player_a_var.set(names[0])
            self.player_b_var.set(names[1])
        self.status_var.set(f"Načteno {len(names)} hráčů (cíleno na top 200).")
        self.status_var.set(f"Načteno {len(names)} hráčů.")

    def compute(self) -> None:
        t = self.selected_tournament()
        p1 = self.player_a_var.get().strip()
        p2 = self.player_b_var.get().strip()
        if not p1 or not p2:
            messagebox.showerror("Chyba", "Nejdřív načti hráče a vyber oba hráče.")
            return
        if p1 == p2:
            messagebox.showerror("Chyba", "Hráč A a B musí být různí.")
            return

        rows = self.rows_by_tour.get(t.tour)
        if not rows:
            messagebox.showerror("Chyba", "Nejdřív klikni 'Načti hráče pro turnaj'.")
            return

        try:
            a_aces, b_aces, a_ci, b_ci = estimate_aces_for_match(rows, p1, p2, t.surface, t.boost)
        except Exception as e:
            messagebox.showerror("Chyba výpočtu", str(e))
            return

        self.result_var.set(
            f"Turnaj: {t.name} ({t.tour.upper()}, {t.surface})\n"
            f"{p1}: {a_aces} es  | interval 80%: {a_ci[0]} - {a_ci[1]}\n"
            f"{p2}: {b_aces} es  | interval 80%: {b_ci[0]} - {b_ci[1]}"
        )
        self.status_var.set("Výpočet hotov.")


if __name__ == "__main__":
    App().mainloop()
