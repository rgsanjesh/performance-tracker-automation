import requests
from datetime import date
from urllib.parse import urlparse

_CRUX_URL = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
_METRICS = [
    "largest_contentful_paint",
    "interaction_to_next_paint",
    "cumulative_layout_shift",
]


def _query(payload: dict, api_key: str) -> dict | None:
    resp = requests.post(f"{_CRUX_URL}?key={api_key}", json=payload, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()["record"]


def fetch_cwv(url: str, form_factor: str, api_key: str) -> dict | None:
    # Try URL-level first, fall back to origin-level (mirrors PSI website behaviour)
    record = _query({"url": url, "formFactor": form_factor, "metrics": _METRICS}, api_key)
    if record is None:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        record = _query({"origin": origin, "formFactor": form_factor, "metrics": _METRICS}, api_key)
    if record is None:
        return None

    metrics = record["metrics"]
    last = record["collectionPeriod"]["lastDate"]

    def p75(name: str) -> float | int | str:
        return metrics.get(name, {}).get("percentiles", {}).get("p75", "")

    lcp_ms = p75("largest_contentful_paint")
    inp    = p75("interaction_to_next_paint")
    cls    = p75("cumulative_layout_shift")

    return {
        "lcp": round(lcp_ms / 1000, 1) if isinstance(lcp_ms, (int, float)) else "",
        "inp": inp,
        "cls": cls,
        "collection_end": date(last["year"], last["month"], last["day"]),
    }
