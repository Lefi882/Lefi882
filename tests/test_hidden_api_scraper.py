from scripts.hidden_api_scraper import HiddenApiOddsScraper


def test_parse_hidden_api_events_to_normalized_events() -> None:
    scraper = HiddenApiOddsScraper()
    payload = {
        "events": [
            {
                "id": 99,
                "home": "Sparta",
                "away": "Slavia",
                "commence_time": "2026-02-20T18:00:00",
                "odds": {"h2h": [2.4, 3.3, 2.9]},
            },
            {
                "id": 100,
                "home": "A",
                "away": "B",
                "odds": {"h2h": [1.9]},
            },
        ]
    }

    events = scraper.parse_payload(payload, bookmaker="DemoBookie", feed_format="events")

    assert len(events) == 1
    assert events[0]["event_id"] == "99"
    assert events[0]["event_name"] == "Sparta vs Slavia"
    assert events[0]["odds"] == {"1": 2.4, "X": 3.3, "2": 2.9}


def test_parse_tipsport_offer_v2_payload() -> None:
    scraper = HiddenApiOddsScraper()
    payload = {
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
                                        "nameFull": "Sparta - Slavia",
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
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        ]
    }

    events = scraper.parse_payload(payload, bookmaker="Tipsport", feed_format="tipsport_offer_v2")

    assert len(events) == 1
    assert events[0]["event_id"] == "11"
    assert events[0]["sport"] == "football"
    assert events[0]["market"] == "1X2"
    assert events[0]["odds"] == {"1": 2.0, "X": 3.4, "2": 3.8}
