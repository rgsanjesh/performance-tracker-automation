import requests
from datetime import date

_CRUX_HISTORY = "https://chromeuxreport.googleapis.com/v1/records:queryHistoryRecord"


def _query(url: str, form_factor: str, api_key: str) -> dict | None:
    resp = requests.post(
        f"{_CRUX_HISTORY}?key={api_key}",
        json={"url": url, "formFactor": form_factor, "collectionPeriodCount": 2},
        timeout=15,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()["record"]


def _fetch_record(url: str, form_factor: str, api_key: str) -> dict | None:
    # CrUX History API is strict about trailing slashes — try both
    record = _query(url, form_factor, api_key)
    if record is None and url.endswith("/"):
        record = _query(url.rstrip("/"), form_factor, api_key)
    return record


def get_collection_end(api_key: str) -> date:
    record = _fetch_record("https://pharmeasy.in/", "PHONE", api_key)
    last = record["collectionPeriods"][-1]["lastDate"]
    return date(last["year"], last["month"], last["day"])


def fetch_cwv(url: str, strategy: str, api_key: str) -> dict | None:
    form_factor = "PHONE" if strategy == "MOBILE" else "DESKTOP"
    record = _fetch_record(url, form_factor, api_key)
    if record is None:
        print(f"  no CrUX data for {url} ({strategy}) — skipping")
        return None

    metrics = record["metrics"]

    def p75(name: str, idx: int = -1):
        vals = metrics.get(name, {}).get("percentilesTimeseries", {}).get("p75s", [])
        if not vals or abs(idx) > len(vals):
            return None
        return vals[idx]

    def to_lcp(v): return round(v / 1000, 1) if isinstance(v, (int, float)) else None
    def to_inp(v): return v if isinstance(v, (int, float)) else None
    def to_cls(v): return round(float(v), 2) if v not in (None, "") else None

    def blank(v): return v if v is not None else ""

    return {
        "lcp":      blank(to_lcp(p75("largest_contentful_paint"))),
        "inp":      blank(to_inp(p75("interaction_to_next_paint"))),
        "cls":      blank(to_cls(p75("cumulative_layout_shift"))),
        "prev_lcp": to_lcp(p75("largest_contentful_paint", -2)),
        "prev_inp": to_inp(p75("interaction_to_next_paint", -2)),
        "prev_cls": to_cls(p75("cumulative_layout_shift", -2)),
    }
