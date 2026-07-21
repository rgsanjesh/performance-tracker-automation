from datetime import date
from unittest.mock import Mock, patch

from crux import fetch_cwv

_MOCK_RESP = {
    "record": {
        "key": {"url": "https://pharmeasy.in/", "formFactor": "PHONE"},
        "metrics": {
            "largest_contentful_paint":  {"percentiles": {"p75": 1700}},
            "interaction_to_next_paint": {"percentiles": {"p75": 192}},
            "cumulative_layout_shift":   {"percentiles": {"p75": 0.01}},
        },
        "collectionPeriod": {
            "firstDate": {"year": 2025, "month": 7, "day": 21},
            "lastDate":  {"year": 2025, "month": 7, "day": 28},
        },
    }
}


def _mock_post(status: int, body: dict) -> Mock:
    m = Mock()
    m.status_code = status
    m.json.return_value = body
    m.raise_for_status = Mock()
    return m


def test_fetch_cwv_success():
    with patch("crux.requests.post", return_value=_mock_post(200, _MOCK_RESP)):
        result = fetch_cwv("https://pharmeasy.in/", "PHONE", "fake-key")

    assert result["lcp"] == 1.7
    assert result["inp"] == 192
    assert result["cls"] == 0.01
    assert result["collection_end"] == date(2025, 7, 28)


def test_fetch_cwv_no_data_returns_none():
    with patch("crux.requests.post", return_value=_mock_post(404, {})):
        assert fetch_cwv("https://pharmeasy.in/unknown", "PHONE", "fake-key") is None


def test_fetch_cwv_missing_metric_returns_empty_string():
    body = {
        "record": {
            "key": {},
            "metrics": {
                "largest_contentful_paint": {"percentiles": {"p75": 1700}},
                # INP and CLS intentionally missing
            },
            "collectionPeriod": {
                "firstDate": {"year": 2025, "month": 7, "day": 21},
                "lastDate":  {"year": 2025, "month": 7, "day": 28},
            },
        }
    }
    with patch("crux.requests.post", return_value=_mock_post(200, body)):
        result = fetch_cwv("https://pharmeasy.in/", "PHONE", "fake-key")

    assert result["lcp"] == 1.7
    assert result["inp"] == ""
    assert result["cls"] == ""
