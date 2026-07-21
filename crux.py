import requests
from datetime import date

_CRUX_URL = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"


def fetch_cwv(url: str, form_factor: str, api_key: str) -> dict | None:
    payload = {
        "url": url,
        "formFactor": form_factor,
        "metrics": [
            "largest_contentful_paint",
            "interaction_to_next_paint",
            "cumulative_layout_shift",
        ],
    }
    resp = requests.post(f"{_CRUX_URL}?key={api_key}", json=payload, timeout=30)

    if resp.status_code == 404:
        return None

    resp.raise_for_status()
    record = resp.json()["record"]
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
