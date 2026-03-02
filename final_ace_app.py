"""Final GUI app: choose profile + players and click compute aces."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Dict, List

from ace_engine import (
    DataLoadMeta,
    estimate_aces_for_match,
    load_rows,
    load_rows_with_meta,
    ranked_player_pool,
    search_players,
    suggested_lines,
    over_under_probabilities,
)


@dataclass(frozen=True)
class TournamentProfile:
    name: str
    tour: str
    surface: str
    boost: float


TOURNAMENTS = [
    TournamentProfile("ATP Hard (obecný)", "atp", "Hard", 1.02),
    TournamentProfile("ATP Clay / Antuka (obecný)", "atp", "Clay", 0.88),
    TournamentProfile("WTA Hard (obecný)", "wta", "Hard", 1.00),
    TournamentProfile("WTA Clay / Antuka (obecný)", "wta", "Clay", 0.90),
]


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FINAL ACE APP")
        self.geometry("900x580")
        self.minsize(860, 540)
        self.configure(bg="#0f172a")

        self._init_style()

        self.rows_by_tour: Dict[str, List[Dict[str, str]]] = {}

        self.tournament_var = tk.StringVar(value=TOURNAMENTS[0].name)
        self.player_a_var = tk.StringVar()
        self.player_b_var = tk.StringVar()
        self.player_a_filter_var = tk.StringVar()
        self.player_b_filter_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.result_var = tk.StringVar(value="Vyber profil, načti hráče a klikni VYPOČTI ESA.")

        self.players_list: List[str] = []
        self.current_meta: DataLoadMeta | None = None

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
        ttk.Label(root, text="Live-ish data + filtr hráčů + odhad počtu es", style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

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

        self.load_btn = ttk.Button(card, text="1) Načti hráče (live data)", command=self.load_players, style="Accent.TButton")
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
        ttk.Label(result_card, textvariable=self.result_var, justify="left", style="Result.TLabel", wraplength=820).grid(
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
        a_items = search_players(self.players_list, self.player_a_filter_var.get(), limit=60)
        b_items = search_players(self.players_list, self.player_b_filter_var.get(), limit=60)
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
        self.status_var.set(f"Načítám data pro {t.name} ({t.tour.upper()})...")
        self.update_idletasks()

        # always reload to get fresh data (cache in fetch has 24h freshness)
        rows, meta = load_rows_with_meta(t.tour, years=[2023, 2024, 2025, 2026], csv_files=[])
        self.current_meta = meta
        self.rows_by_tour[t.tour] = rows

        names = ranked_player_pool(rows, t.tour, limit=200)
        self.players_list = names
        self.player_a_box["values"] = names
        self.player_b_box["values"] = names

        if len(names) >= 2:
            self.player_a_var.set(names[0])
            self.player_b_var.set(names[1])

        if meta.latest_date:
            age_days = max(0, meta.age_days or 0)
            fresh_info = f"Poslední zápas v datech: {meta.latest_date.strftime('%Y-%m-%d')} (stáří {age_days} dnů)"
        else:
            age_days = 9999
            fresh_info = "Poslední zápas v datech: neznámé"

        if meta.source == "sample_fallback":
            fresh_info += " | ZDROJ: sample fallback ⚠️"
        elif meta.source == "remote_or_cache":
            fresh_info += " | ZDROJ: remote/cache"
        else:
            fresh_info += " | ZDROJ: csv"

        if age_days > 3 or meta.source == "sample_fallback":
            self.status_var.set(f"⛔ Data příliš stará pro production predikci. {fresh_info}")
        elif len(names) < 20:
            self.status_var.set(f"Načteno {len(names)} hráčů (nízký vzorek). {fresh_info}")
        else:
            self.status_var.set(f"Načteno {len(names)} aktivních hráčů. {fresh_info}")

        self._apply_filters()

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
            messagebox.showerror("Chyba", "Nejdřív klikni 'Načti hráče (live data)'.")
            return

        if self.current_meta and (self.current_meta.source == "sample_fallback" or (self.current_meta.age_days is not None and self.current_meta.age_days > 3)):
            messagebox.showerror(
                "Production safeguard",
                "Data jsou příliš stará nebo jen ze sample fallbacku.\n"
                "Predikce je zablokovaná. Nejprve obnov live data.",
            )
            return

        try:
            a_aces, b_aces, a_ci, b_ci = estimate_aces_for_match(rows, p1, p2, t.surface, t.boost)
        except Exception as e:
            messagebox.showerror("Chyba výpočtu", str(e))
            return

        lines_a = suggested_lines(a_aces, count=3)
        lines_b = suggested_lines(b_aces, count=3)
        probs_a = over_under_probabilities(a_aces, lines_a)
        probs_b = over_under_probabilities(b_aces, lines_b)

        a_ou = "\n".join(
            f"  O/U {line:.1f}: Over {probs_a[line][0]*100:.1f}% | Under {probs_a[line][1]*100:.1f}%"
            for line in lines_a
        )
        b_ou = "\n".join(
            f"  O/U {line:.1f}: Over {probs_b[line][0]*100:.1f}% | Under {probs_b[line][1]*100:.1f}%"
            for line in lines_b
        )

        self.result_var.set(
            f"Profil: {t.name} ({t.tour.upper()}, {t.surface})\n"
            f"{p1}: {a_aces} es  | interval 80%: {a_ci[0]} - {a_ci[1]}\n"
            f"{p2}: {b_aces} es  | interval 80%: {b_ci[0]} - {b_ci[1]}\n\n"
            f"{p1} line probabilities:\n{a_ou}\n\n"
            f"{p2} line probabilities:\n{b_ou}"
        )
        self.status_var.set("Výpočet hotov.")


if __name__ == "__main__":
    App().mainloop()
