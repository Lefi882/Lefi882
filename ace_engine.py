"""Core engine for high-quality ace estimation.

Focuses on reusable data loading + model calculations so both CLI and GUI can use it.
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ace_estimator import fetch_year_matches, read_local_matches, safe_float


@dataclass
class RichAceProfile:
    name: str
    ace_rate_weighted: float
    ace_allowed_weighted: float
    service_points_avg: float
    aces_avg: float
    aces_std: float


def load_rows(tour: str, years: List[int], csv_files: Optional[List[str]] = None) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    csv_files = csv_files or []
    if csv_files:
        for f in csv_files:
            rows.extend(read_local_matches(f))
        return rows

    normalized_years = sorted(set(years))
    current_year = datetime.utcnow().year
    if current_year not in normalized_years:
        normalized_years.append(current_year)

    for y in normalized_years:
        rows.extend(fetch_year_matches(tour, y))

    # fallback to bundled samples
    if not rows:
        fallback = Path("sample_wta_matches.csv" if tour == "wta" else "sample_atp_matches.csv")
        if fallback.exists():
            rows.extend(read_local_matches(str(fallback)))
    return rows


def _player_matches(rows: Iterable[Dict[str, str]], player: str, surface: Optional[str]) -> List[Dict[str, str]]:
    out = []
    for r in rows:
        if surface and r.get("surface", "").lower() != surface.lower():
            continue
        if r.get("winner_name") == player or r.get("loser_name") == player:
            out.append(r)
    out.sort(key=lambda x: x.get("tourney_date", ""), reverse=True)
    return out


def _row_stats_for_player(row: Dict[str, str], player: str) -> Tuple[float, float, float, float]:
    """Return own_ace_rate, opp_ace_allowed_rate, own_svpt, own_aces"""
    is_winner = row.get("winner_name") == player
    if is_winner:
        own_ace = safe_float(row.get("w_ace"))
        own_svpt = max(1.0, safe_float(row.get("w_svpt"), 1.0))
        opp_ace = safe_float(row.get("l_ace"))
        opp_svpt = max(1.0, safe_float(row.get("l_svpt"), 1.0))
    else:
        own_ace = safe_float(row.get("l_ace"))
        own_svpt = max(1.0, safe_float(row.get("l_svpt"), 1.0))
        opp_ace = safe_float(row.get("w_ace"))
        opp_svpt = max(1.0, safe_float(row.get("w_svpt"), 1.0))
    return own_ace / own_svpt, opp_ace / opp_svpt, own_svpt, own_ace


def _exp_weights(n: int, decay: float = 0.90) -> List[float]:
    ws = [decay**i for i in range(n)]
    s = sum(ws)
    return [w / s for w in ws]


def _wmean(values: List[float], weights: List[float]) -> float:
    return sum(v * w for v, w in zip(values, weights)) if values else 0.0


def _parse_tourney_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y%m%d")
    except Exception:
        return None


def build_rich_profile(player: str, rows: List[Dict[str, str]], surface: str, recent_n: int = 40) -> RichAceProfile:
    matches = _player_matches(rows, player, surface)
    if len(matches) < 6:
        matches = _player_matches(rows, player, None)
    if not matches:
        raise ValueError(f"Hráč '{player}' nebyl v datech.")

    recent = matches[:recent_n]
    stats = [_row_stats_for_player(r, player) for r in recent]
    own_rate = [x[0] for x in stats]
    opp_allow = [x[1] for x in stats]
    svpt = [x[2] for x in stats]
    aces = [x[3] for x in stats]
    w = _exp_weights(len(stats), decay=0.92)

    return RichAceProfile(
        name=player,
        ace_rate_weighted=_wmean(own_rate, w),
        ace_allowed_weighted=_wmean(opp_allow, w),
        service_points_avg=_wmean(svpt, w),
        aces_avg=_wmean(aces, w),
        aces_std=statistics.pstdev(aces) if len(aces) > 1 else 1.2,
    )


def tournament_surface_multiplier(surface: str, tournament_boost: float = 1.0) -> float:
    base = {"grass": 1.18, "hard": 1.00, "clay": 0.84, "carpet": 1.20}.get(surface.lower(), 1.0)
    return base * tournament_boost


def h2h_adjustment(rows: List[Dict[str, str]], p1: str, p2: str, surface: str, max_n: int = 8) -> float:
    h2h = []
    for r in rows:
        a = r.get("winner_name")
        b = r.get("loser_name")
        if {a, b} == {p1, p2}:
            if r.get("surface", "").lower() == surface.lower():
                h2h.append(r)
            elif len(h2h) < 2:
                h2h.append(r)
    h2h.sort(key=lambda x: x.get("tourney_date", ""), reverse=True)
    h2h = h2h[:max_n]
    if not h2h:
        return 0.0

    deltas = []
    weights = []
    newest_date = _parse_tourney_date(h2h[0].get("tourney_date", ""))
    for i, r in enumerate(h2h):
        p1_is_w = r.get("winner_name") == p1
        p1_ace = safe_float(r.get("w_ace") if p1_is_w else r.get("l_ace"))
        p2_ace = safe_float(r.get("l_ace") if p1_is_w else r.get("w_ace"))
        deltas.append((p1_ace - p2_ace) / 20.0)  # scaled

        d = _parse_tourney_date(r.get("tourney_date", ""))
        if newest_date and d:
            months = max(0.0, (newest_date - d).days / 30.0)
            recency_w = 0.94 ** months
        else:
            recency_w = 0.9 ** i
        weights.append(recency_w)

    if not weights or sum(weights) <= 0:
        raw = statistics.mean(deltas)
    else:
        raw = sum(v * w for v, w in zip(deltas, weights)) / sum(weights)

    # If we have strong and consistent H2H gap, allow slightly larger impact.
    consistency = abs(raw)
    cap = 0.18 if consistency >= 0.25 else 0.12
    return max(-cap, min(cap, raw))


def estimate_aces_for_match(
    rows: List[Dict[str, str]],
    player_a: str,
    player_b: str,
    surface: str,
    tournament_boost: float = 1.0,
) -> Tuple[float, float, Tuple[float, float], Tuple[float, float]]:
    a = build_rich_profile(player_a, rows, surface)
    b = build_rich_profile(player_b, rows, surface)

    h2h_ab = h2h_adjustment(rows, player_a, player_b, surface)
    h2h_ba = -h2h_ab
    sf = tournament_surface_multiplier(surface, tournament_boost)

    rate_a = 0.70 * a.ace_rate_weighted + 0.30 * b.ace_allowed_weighted + h2h_ab * 0.35
    rate_b = 0.70 * b.ace_rate_weighted + 0.30 * a.ace_allowed_weighted + h2h_ba * 0.35

    rate_a = max(0.01, min(0.45, rate_a))
    rate_b = max(0.01, min(0.45, rate_b))

    a_aces = max(0.0, rate_a * a.service_points_avg * sf)
    b_aces = max(0.0, rate_b * b.service_points_avg * sf)

    # rough 80% intervals from historical variance
    a_ci = (max(0.0, a_aces - 1.28 * max(0.8, a.aces_std)), a_aces + 1.28 * max(0.8, a.aces_std))
    b_ci = (max(0.0, b_aces - 1.28 * max(0.8, b.aces_std)), b_aces + 1.28 * max(0.8, b.aces_std))

    return round(a_aces, 1), round(b_aces, 1), (round(a_ci[0], 1), round(a_ci[1], 1)), (round(b_ci[0], 1), round(b_ci[1], 1))



def latest_data_date(rows: List[Dict[str, str]]) -> datetime | None:
    dates = []
    for r in rows:
        d = _parse_tourney_date(r.get("tourney_date", ""))
        if d:
            dates.append(d)
    return max(dates) if dates else None


def is_active_player(rows: List[Dict[str, str]], player: str, max_inactive_days: int = 420) -> bool:
    newest = latest_data_date(rows)
    if not newest:
        return True
    last = None
    for r in rows:
        if r.get("winner_name") == player or r.get("loser_name") == player:
            d = _parse_tourney_date(r.get("tourney_date", ""))
            if d and (last is None or d > last):
                last = d
    if not last:
        return False
    return (newest - last).days <= max_inactive_days


def ranked_player_pool(rows: List[Dict[str, str]], tour: str, limit: int = 200) -> List[str]:
    """Build a practical top-player pool from loaded match data.

    Score is based on match activity + wins, which keeps current top players near the top
    when recent years are loaded.
    """
    stats: Dict[str, Dict[str, float]] = {}
    for r in rows:
        w = r.get("winner_name")
        l = r.get("loser_name")
        if w:
            stats.setdefault(w, {"m": 0, "w": 0})
            stats[w]["m"] += 1
            stats[w]["w"] += 1
        if l:
            stats.setdefault(l, {"m": 0, "w": 0})
            stats[l]["m"] += 1

    scored = []
    for name, d in stats.items():
        if not is_active_player(rows, name):
            continue
        matches = d["m"]
        wins = d["w"]
        win_rate = wins / matches if matches else 0.0
        score = matches * 0.65 + wins * 0.35 + 10 * win_rate
        scored.append((score, name))

    scored.sort(reverse=True)
    return [n for _, n in scored[:limit]]


def search_players(players: List[str], query: str, limit: int = 40) -> List[str]:
    q = (query or "").strip().lower()
    if not q:
        return players[:limit]
    starts = [p for p in players if p.lower().startswith(q)]
    contains = [p for p in players if q in p.lower() and p not in starts]
    return (starts + contains)[:limit]



def over_under_probabilities(expected_aces: float, lines: List[float]) -> Dict[float, Tuple[float, float]]:
    """Return over/under probabilities for half-lines using a Poisson model."""
    lam = max(0.05, float(expected_aces))

    # Stable iterative Poisson pmf/cdf computation.
    pmf = math.exp(-lam)  # P(X=0)
    cdf = pmf
    probs: Dict[int, float] = {0: pmf}
    k = 0
    target_k = max(20, int(max(lines) + 12)) if lines else 20
    while k < target_k:
        k += 1
        pmf = pmf * lam / k
        probs[k] = pmf
        cdf += pmf

    out: Dict[float, Tuple[float, float]] = {}
    for line in lines:
        threshold = int(math.floor(line))
        under = sum(probs.get(i, 0.0) for i in range(threshold + 1))
        under = max(0.0, min(1.0, under))
        over = 1.0 - under
        out[line] = (over, under)
    return out


def suggested_lines(expected_aces: float, count: int = 3) -> List[float]:
    center = int(round(expected_aces))
    base = max(0, center - 1)
    lines = [base + i + 0.5 for i in range(count)]
    return lines
