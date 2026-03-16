import json
from pathlib import Path

from odds.providers import fetch_offers


def test_fetch_offers_from_providers_config(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    sample = {
        "events": [
            {
                "event_id": "a1",
                "event_name": "A vs B",
                "sport": "football",
                "market": "1X2",
                "kickoff": "2026-02-20T18:00:00",
                "odds": {"1": 2.1, "X": 3.2, "2": 3.7},
            }
        ]
    }
    (data_dir / "one.json").write_text(json.dumps(sample), encoding="utf-8")

    providers = {
        "providers": [
            {"bookmaker": "Book1", "data_file": "data/one.json"}
        ]
    }
    (tmp_path / "providers.custom.json").write_text(json.dumps(providers), encoding="utf-8")

    offers = fetch_offers(root=tmp_path, providers_file="providers.custom.json")

    assert len(offers) == 1
    assert offers[0].bookmaker == "Book1"
    assert offers[0].event_id == "a1"


def test_parse_tipsport_offer_v2_format(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    sample = {
        "offerSuperSports": [
            {
                "id": {"superSportId": 16},
                "tabs": [
                    {
                        "matchView": "WINNER_WHOLE_MATCH",
                        "offerCompetitionAnnuals": [
                            {
                                "matches": [
                                    {
                                        "id": 11,
                                        "nameFull": "A - B",
                                        "dateClosed": "2026-02-26T18:45:00.000+01:00",
                                        "race": False,
                                        "oppRows": [
                                            {
                                                "oppsTab": [
                                                    {"type": "1", "odd": 2.0},
                                                    {"type": "x", "odd": 3.4},
                                                    {"type": "2", "odd": 3.8},
                                                ]
                                            }
                                        ],
                                    },
                                    {
                                        "id": 22,
                                        "nameFull": "Outright",
                                        "dateClosed": "2026-02-26T18:45:00.000+01:00",
                                        "race": True,
                                        "oppRows": [{"oppsTab": [{"type": "1", "odd": 4.0}]}],
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        ]
    }
    (data_dir / "tipsport.json").write_text(json.dumps(sample), encoding="utf-8")

    providers = {
        "providers": [
            {
                "bookmaker": "Tipsport",
                "data_file": "data/tipsport.json",
                "format": "tipsport_offer_v2",
            }
        ]
    }
    (tmp_path / "providers.custom.json").write_text(json.dumps(providers), encoding="utf-8")

    offers = fetch_offers(root=tmp_path, providers_file="providers.custom.json")

    assert len(offers) == 1
    assert offers[0].event_id == "11"
    assert offers[0].outcomes == {"1": 2.0, "X": 3.4, "2": 3.8}
