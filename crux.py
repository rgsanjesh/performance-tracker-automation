import requests
from datetime import date

_PSI_URL  = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
_CRUX_URL = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"


def get_collection_end(api_key: str) -> date:
    """Get CrUX collection period end date via origin-level query."""
    resp = requests.post(
        f"{_CRUX_URL}?key={api_key}",
        json={"origin": "https://pharmeasy.in", "formFactor": "PHONE"},
        timeout=30,
    )
    resp.raise_for_status()
    last = resp.json()["record"]["collectionPeriod"]["lastDate"]
    return date(last["year"], last["month"], last["day"])


def fetch_cwv(url: str, strategy: str, api_key: str) -> dict | None:
    """Fetch p75 CWV metrics from PSI API. strategy: 'MOBILE' or 'DESKTOP'."""
    try:
        resp = requests.get(
            _PSI_URL,
            params={"url": url, "strategy": strategy, "key": api_key},
            timeout=60,
        )
    except requests.exceptions.Timeout:
        print(f"  PSI timeout for {url} ({strategy}) — skipping")
        return None
    if not resp.ok:
        print(f"  PSI {resp.status_code} for {url} ({strategy}) — skipping")
        return None
    metrics = resp.json().get("loadingExperience", {}).get("metrics")
    if not metrics:
        return None

    def p75(field: str):
        return metrics.get(field, {}).get("percentile", "")

    lcp_ms = p75("LARGEST_CONTENTFUL_PAINT_MS")
    inp    = p75("INTERACTION_TO_NEXT_PAINT")
    cls_raw = p75("CUMULATIVE_LAYOUT_SHIFT_SCORE")

    return {
        "lcp": round(lcp_ms / 1000, 1) if isinstance(lcp_ms, (int, float)) else "",
        "inp": inp,
        "cls": round(cls_raw / 100, 2) if isinstance(cls_raw, (int, float)) else "",
    }
