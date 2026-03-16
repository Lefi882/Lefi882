"""Final GUI app powered by TennisRatio live API data."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Dict, List

from tennisratio_api_client import PlayerRef, fetch_h2h_players, fetch_player_stats, metric_value


@dataclass(frozen=True)
class TournamentProfile:
    name: str
    tour: str
    surface: str
    boost: float


TOURNAMENTS = [
    TournamentProfile("ATP Hard", "atp", "hard", 1.02),
    TournamentProfile("ATP Clay", "atp", "clay", 0.92),
    TournamentProfile("ATP Grass", "atp", "grass", 1.12),
    TournamentProfile("WTA Hard", "wta", "hard", 1.00),
    TournamentProfile("WTA Clay", "wta", "clay", 0.90),
    TournamentProfile("WTA Grass", "wta", "grass", 1.06),
]


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FINAL ACE APP (TennisRatio API)")
        self.geometry("940x620")
        self.minsize(900, 580)
        self.configure(bg="#0f172a")

        self._init_style()

        self.tournament_var = tk.StringVar(value=TOURNAMENTS[0].name)
        self.player_a_var = tk.StringVar()
        self.player_b_var = tk.StringVar()
        self.player_a_filter_var = tk.StringVar()
        self.player_b_filter_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.result_var = tk.StringVar(value="Vyber profil, načti hráče z TennisRatio API a klikni VYPOČTI ESA.")

        self.players_list: List[str] = []
        self.player_refs_by_name: Dict[str, PlayerRef] = {}

        self._build_ui()

    def _init_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#111827")
        style.configure("Title.TLabel", background="#0f172a", foreground="#e2e8f0", font=("Segoe UI", 17, "bold"))
        style.configure("Sub.TLabel", background="#0f172a", foreground="#94a3b8", font=("Segoe UI", 10))
        style.configure("Field.TLabel", background="#111827", foreground="#cbd5e1", font=("Segoe UI", 10, "bold"))
        style.configure("Result.TLabel", background="#111827", foreground="#e2e8f0", font=("Consolas", 11))
        style.configure("Status.TLabel", background="#0f172a", foreground="#93c5fd", font=("Segoe UI", 10, "italic"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="🎾 Final Ace App", style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text="Data přímo z TennisRatio API (bez lokálních stale CSV)", style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        card = ttk.Frame(root, style="Card.TFrame", padding=14)
        card.pack(fill="x")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text="Profil", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4), padx=(0, 8))
        self.tournament_box = ttk.Combobox(
            card,
            textvariable=self.tournament_var,
            values=[t.name for t in TOURNAMENTS],
            state="readonly",
        )
        self.tournament_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 4))

        self.load_btn = ttk.Button(card, text="1) Načti hráče (TennisRatio API)", command=self.load_players, style="Accent.TButton")
        self.load_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(card, text="Filtr hráče A", style="Field.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 8))
        ttk.Label(card, text="Filtr hráče B", style="Field.TLabel").grid(row=3, column=1, sticky="w")

        self.player_a_filter = ttk.Entry(card, textvariable=self.player_a_filter_var)
        self.player_b_filter = ttk.Entry(card, textvariable=self.player_b_filter_var)
        self.player_a_filter.grid(row=4, column=0, sticky="ew", padx=(0, 8), pady=(2, 6))
        self.player_b_filter.grid(row=4, column=1, sticky="ew", pady=(2, 6))

        ttk.Label(card, text="Hráč A", style="Field.TLabel").grid(row=5, column=0, sticky="w", padx=(0, 8))
        ttk.Label(card, text="Hráč B", style="Field.TLabel").grid(row=5, column=1, sticky="w")

        self.player_a_box = ttk.Combobox(card, textvariable=self.player_a_var, values=self.players_list, state="readonly")
        self.player_b_box = ttk.Combobox(card, textvariable=self.player_b_var, values=self.players_list, state="readonly")
        self.player_a_box.grid(row=6, column=0, sticky="ew", padx=(0, 8), pady=(2, 6))
        self.player_b_box.grid(row=6, column=1, sticky="ew", pady=(2, 6))

        self.compute_btn = ttk.Button(card, text="2) VYPOČTI ESA", command=self.compute, style="Accent.TButton")
        self.compute_btn.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 4))

        result_card = ttk.Frame(root, style="Card.TFrame", padding=14)
        result_card.pack(fill="both", expand=True, pady=(12, 0))
        result_card.columnconfigure(0, weight=1)

        ttk.Label(result_card, text="Výsledek", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(result_card, textvariable=self.result_var, justify="left", style="Result.TLabel", wraplength=860).grid(
            row=1,
            column=0,
            sticky="nw",
            pady=(8, 0),
        )

        ttk.Label(root, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(8, 0))

        self.player_a_filter_var.trace_add("write", lambda *_: self._apply_filters())
        self.player_b_filter_var.trace_add("write", lambda *_: self._apply_filters())

    def _apply_filters(self) -> None:
        if not self.players_list:
            return
        a_query = self.player_a_filter_var.get().strip().lower()
        b_query = self.player_b_filter_var.get().strip().lower()
        a_items = [n for n in self.players_list if a_query in n.lower()][:80]
        b_items = [n for n in self.players_list if b_query in n.lower()][:80]
        self.player_a_box["values"] = a_items
        self.player_b_box["values"] = b_items
        if a_items and self.player_a_var.get() not in a_items:
            self.player_a_var.set(a_items[0])
        if b_items and self.player_b_var.get() not in b_items:
            self.player_b_var.set(b_items[0])

    def selected_tournament(self) -> TournamentProfile:
        for t in TOURNAMENTS:
            if t.name == self.tournament_var.get():
                return t
        return TOURNAMENTS[0]

    def load_players(self) -> None:
        t = self.selected_tournament()
        self.status_var.set(f"Načítám TennisRatio index hráčů ({t.tour.upper()})...")
        self.update_idletasks()
        try:
            players = fetch_h2h_players()
        except Exception as e:
            messagebox.showerror("Chyba API", f"Nepodařilo se načíst hráče z TennisRatio API.\n{e}")
            self.status_var.set("Chyba načítání TennisRatio API")
            return

        filtered = [p for p in players if p.category.lower() == t.tour]
        filtered.sort(key=lambda p: (p.rank is None, p.rank if p.rank is not None else 10**9, p.name))

        self.players_list = [p.name for p in filtered]
        self.player_refs_by_name = {p.name: p for p in filtered}

        self.player_a_box["values"] = self.players_list
        self.player_b_box["values"] = self.players_list

        if len(self.players_list) >= 2:
            self.player_a_var.set(self.players_list[0])
            self.player_b_var.set(self.players_list[1])

        self._apply_filters()
        self.status_var.set(f"Načteno {len(self.players_list)} hráčů z TennisRatio API ({t.tour.upper()}).")

    def _estimate_aces(self, own_stats: Dict, opp_stats: Dict, boost: float) -> float:
        own_aces = metric_value(own_stats, "aces_per_match", 3.0)
        own_sg = metric_value(own_stats, "service_games_won_ratio", 80.0)

        opp_ret = metric_value(opp_stats, "return_games_won_ratio", 20.0)
        opp_ret2 = metric_value(opp_stats, "return_2nd_serve_points", 45.0)

        defense_factor = 1.08 - ((opp_ret / 100.0) * 0.35 + (opp_ret2 / 100.0) * 0.25)
        defense_factor = max(0.70, min(1.20, defense_factor))

        service_factor = max(0.85, min(1.15, own_sg / 85.0))

        pred = own_aces * defense_factor * service_factor * boost
        return round(max(0.5, pred), 1)

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

        ref1 = self.player_refs_by_name.get(p1)
        ref2 = self.player_refs_by_name.get(p2)
        if not ref1 or not ref2:
            messagebox.showerror("Chyba", "Hráče nebylo možné mapovat na TennisRatio slug. Zkus načíst hráče znovu.")
            return

        self.status_var.set(f"Načítám live stats: {p1} vs {p2} ({t.surface.upper()})...")
        self.update_idletasks()

        try:
            s1 = fetch_player_stats(ref1.slugname, surface=t.surface)
            s2 = fetch_player_stats(ref2.slugname, surface=t.surface)
        except Exception as e:
            messagebox.showerror("Chyba API", f"Nepodařilo se načíst live stats z TennisRatio API.\n{e}")
            self.status_var.set("Chyba načítání live stats")
            return

        a_aces = self._estimate_aces(s1, s2, boost=t.boost)
        b_aces = self._estimate_aces(s2, s1, boost=t.boost)

        a_base = metric_value(s1, "aces_per_match", 0.0)
        b_base = metric_value(s2, "aces_per_match", 0.0)

        self.result_var.set(
            f"Profil: {t.name} (surface={t.surface})\n"
            f"Zdroj: TennisRatio API /stats-filtered\n\n"
            f"{p1}: odhad {a_aces} es (base aces/match: {a_base:.2f})\n"
            f"{p2}: odhad {b_aces} es (base aces/match: {b_base:.2f})\n\n"
            f"Pozn.: výpočet je přímo z live TennisRatio player statistik\n"
            f"(aces_per_match + return/service matchup + surface boost)."
        )
        self.status_var.set("Výpočet hotov (live TennisRatio data).")


if __name__ == "__main__":
    App().mainloop()
