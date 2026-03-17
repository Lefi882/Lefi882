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

    events = scraper.parse_events(payload, bookmaker="DemoBookie")

    assert len(events) == 1
    assert events[0]["event_id"] == "99"
    assert events[0]["event_name"] == "Sparta vs Slavia"
    assert events[0]["odds"] == {"1": 2.4, "X": 3.3, "2": 2.9}
