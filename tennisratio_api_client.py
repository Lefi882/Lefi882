"""Public TennisRatio API helper (no API key required)."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "https://www.tennisratio.com"


@dataclass(frozen=True)
class PlayerRef:
    slugname: str
    name: str
    rank: Optional[int]
    country: str
    category: str


def _get_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Lefi882/1.0)"})
    try:
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="ignore"))
    except URLError as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}") from e


def fetch_h2h_players() -> List[PlayerRef]:
    data = _get_json(f"{BASE}/api/h2h-players/")
    out: List[PlayerRef] = []
    for p in data.get("players", []):
        out.append(
            PlayerRef(
                slugname=str(p.get("slugname", "")).strip(),
                name=str(p.get("name", "")).strip(),
                rank=p.get("rank") if isinstance(p.get("rank"), int) else None,
                country=str(p.get("country", "")).strip(),
                category=str(p.get("category", "")).strip(),
            )
        )
    return out


def search_players(query: str, tour: str = "both", limit: int = 20) -> List[PlayerRef]:
    q = query.strip().lower()
    tour = tour.lower()
    players = fetch_h2h_players()
    if tour in {"atp", "wta"}:
        players = [p for p in players if p.category.lower() == tour]
    if q:
        players = [p for p in players if q in p.name.lower()]
    players.sort(key=lambda p: (p.rank is None, p.rank if p.rank is not None else 10**9, p.name))
    return players[:limit]


def resolve_slug(player_name: str, tour: str = "both") -> str:
    matches = search_players(player_name, tour=tour, limit=8)
    exact = [p for p in matches if p.name.lower() == player_name.strip().lower()]
    if exact:
        return exact[0].slugname
    if matches:
        return matches[0].slugname
    raise RuntimeError(f"Player '{player_name}' not found in TennisRatio h2h-players index")


def fetch_player_stats(slug: str, surface: str = "all", range_key: str = "52w", level: str = "main") -> Dict[str, Any]:
    s = quote(slug)
    surface = surface.lower()
    if surface not in {"all", "hard", "clay", "grass"}:
        raise ValueError("surface must be one of: all, hard, clay, grass")

    seasons = _get_json(f"{BASE}/api/player/{s}/seasons/")
    stats_filtered = _get_json(
        f"{BASE}/api/player/{s}/stats-filtered/?surface={surface}&range={quote(range_key)}&level={quote(level)}"
    )
    comparison = _get_json(
        f"{BASE}/api/player/{s}/stats-comparison?range={quote(range_key)}&level={quote(level)}&surface={surface}"
    )
    return {
        "slug": slug,
        "surface": surface,
        "range": range_key,
        "level": level,
        "seasons": seasons,
        "stats_filtered": stats_filtered,
        "stats_comparison": comparison,
    }


def metric_value(payload: Dict[str, Any], key: str, default: float = 0.0) -> float:
    stats = payload.get("stats_filtered", {}).get("stats", {})
    raw = stats.get(key)
    if isinstance(raw, dict):
        raw = raw.get("value", raw.get("percentage", default))
    try:
        return float(raw)
    except Exception:
        return default


def write_flat_csv(payload: Dict[str, Any], out_path: Path) -> None:
    stats = payload.get("stats_filtered", {}).get("stats", {})
    rows: List[Dict[str, Any]] = []
    if isinstance(stats, dict):
        for k, v in stats.items():
            if isinstance(v, dict):
                v = v.get("value", v.get("percentage"))
            if isinstance(v, (str, int, float, bool)) or v is None:
                rows.append({"metric": k, "value": v})

    if not rows:
        raise RuntimeError("No metrics found in stats_filtered.stats payload")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Consume public TennisRatio API endpoints (no API key).")
    ap.add_argument("--search", help="Search player name in TennisRatio h2h index")
    ap.add_argument("--player", help="Player name to resolve and fetch stats for")
    ap.add_argument("--slug", help="Player slugname (e.g., JannikSinner)")
    ap.add_argument("--tour", choices=["atp", "wta", "both"], default="both")
    ap.add_argument("--surface", choices=["all", "hard", "clay", "grass"], default="all")
    ap.add_argument("--range", dest="range_key", default="52w")
    ap.add_argument("--level", default="main")
    ap.add_argument("--format", choices=["json", "csv"], default="json")
    ap.add_argument("--out", default="data/tennisratio_api/player_stats.json")
    args = ap.parse_args()

    if args.search:
        matches = search_players(args.search, tour=args.tour, limit=30)
        for p in matches:
            print(f"{p.name:30} | {p.category:3} | rank {p.rank!s:>4} | {p.slugname}")
        print(f"Found: {len(matches)}")
        return

    slug = args.slug
    if not slug and args.player:
        slug = resolve_slug(args.player, tour=args.tour)
        print(f"Resolved '{args.player}' -> {slug}")
    if not slug:
        raise SystemExit("Use either --search, or --player/--slug")

    payload = fetch_player_stats(slug, surface=args.surface, range_key=args.range_key, level=args.level)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "json":
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        write_flat_csv(payload, out)

    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
