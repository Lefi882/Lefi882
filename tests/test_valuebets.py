from datetime import datetime

from odds.valuebets import ExportMatch, find_value_bets, match_events


def test_match_events_pairs_variants() -> None:
    target = [
        ExportMatch("Tipsport", "AC Sparta Praha", "Slavia Praha", datetime(2026, 2, 20, 18, 0), {"1": 2.5, "X": 3.5, "2": 3.0}),
    ]
    reference = [
        ExportMatch("Betano", "Sparta", "Slavia Prague", datetime(2026, 2, 20, 18, 0), {"1": 2.2, "X": 3.2, "2": 3.4}),
    ]

    pairs = match_events(target, reference)

    assert len(pairs) == 1


def test_find_value_bets_detects_positive_edge() -> None:
    target = [
        ExportMatch("Tipsport", "A", "B", datetime(2026, 2, 20, 18, 0), {"1": 2.4, "X": 3.6, "2": 3.4}),
    ]
    reference = [
        ExportMatch("Betano", "A", "B", datetime(2026, 2, 20, 18, 0), {"1": 2.1, "X": 3.2, "2": 3.6}),
    ]

    value_bets = find_value_bets(target, reference, min_edge_percent=0.1)

    assert len(value_bets) >= 1
    assert all(vb.edge_percent > 0 for vb in value_bets)
