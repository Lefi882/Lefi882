from datetime import datetime, timezone

from odds.valuebets import ExportMatch, find_best_edges, find_value_bets, match_events


def test_match_events_pairs_variants() -> None:
    target = [
        ExportMatch("Tipsport", "AC Sparta Praha", "Slavia Praha", datetime(2026, 2, 20, 18, 0), {"1": 2.5, "X": 3.5, "2": 3.0}),
    ]
    reference = [
        ExportMatch("Betano", "Sparta", "Slavia Prague", datetime(2026, 2, 20, 18, 0), {"1": 2.2, "X": 3.2, "2": 3.4}),
    ]

    pairs = match_events(target, reference)

    assert len(pairs) == 1


def test_match_events_uses_kickoff_tolerance() -> None:
    target = [
        ExportMatch("Tipsport", "Arsenal", "Chelsea", datetime(2026, 2, 20, 18, 0), {"1": 2.2, "X": 3.4, "2": 3.1}),
    ]
    reference = [
        ExportMatch("Betano", "Arsenal", "Chelsea", datetime(2026, 2, 22, 18, 0), {"1": 2.0, "X": 3.2, "2": 3.5}),
    ]

    pairs = match_events(target, reference, kickoff_tolerance_hours=24)

    assert len(pairs) == 0


def test_match_events_handles_mixed_timezone_datetimes() -> None:
    target = [
        ExportMatch("Tipsport", "Arsenal", "Chelsea", datetime(2026, 2, 20, 18, 0), {"1": 2.2, "X": 3.4, "2": 3.1}),
    ]
    reference = [
        ExportMatch("Betano", "Chelsea", "Arsenal", datetime(2026, 2, 20, 18, 0, tzinfo=timezone.utc), {"1": 2.0, "X": 3.2, "2": 3.5}),
    ]

    pairs = match_events(target, reference, kickoff_tolerance_hours=24)

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


def test_find_best_edges_returns_candidates_even_without_positive_edge() -> None:
    target = [
        ExportMatch("Tipsport", "A", "B", datetime(2026, 2, 20, 18, 0), {"1": 1.8, "X": 3.1, "2": 5.0}),
    ]
    reference = [
        ExportMatch("Betano", "A", "B", datetime(2026, 2, 20, 18, 0), {"1": 1.7, "X": 3.0, "2": 4.9}),
    ]

    edges = find_best_edges(target, reference, top=2)

    assert len(edges) == 2
