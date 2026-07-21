# Core Web Vitals Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate weekly CrUX data entry (LCP, INP, CLS) into the "Consumer Web - Core Web Vitals" Google Sheet via a Python script running on GitHub Actions every Monday at 5:30 PM IST.

**Architecture:** `crux.py` fetches CWV metrics + collection period from the Chrome UX Report API. `sheet.py` handles column detection and Google Sheets writes via gspread. `tracker.py` orchestrates both. Config (URLs, sheet ID, row mappings) lives in `config.py`. GitHub Actions cron triggers weekly.

**Tech Stack:** Python 3.11, gspread ≥6.0, google-auth ≥2.0, requests ≥2.28, GitHub Actions

## Global Constraints

- All credentials via env vars only: `PSI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`
- CrUX form factors: `"PHONE"` for mWeb rows, `"DESKTOP"` for DWeb rows
- LCP: divide p75 ms by 1000, round to 1 decimal → seconds (e.g. `1.7`)
- INP: p75 milliseconds, integer as-is (e.g. `192`)
- CLS: p75 raw decimal (e.g. `0.01`)
- No CrUX data for a page → write `""`, never crash
- Safe re-run: detect existing week column, overwrite values, never duplicate headers
- Cron: `0 12 * * 1` (Monday 12:00 UTC = 5:30 PM IST)

---

### Task 1: Scaffold — config.py + requirements.txt

**Files:**
- Create: `config.py`
- Create: `requirements.txt`
- Create: `tests/__init__.py` (empty)

**Interfaces:**
- Produces: `SHEET_ID: str`, `PAGES: list[tuple[str, int, int | None]]`

- [ ] **Step 1: Create `requirements.txt`**

```
gspread>=6.0.0
google-auth>=2.0.0
requests>=2.28.0
```

- [ ] **Step 2: Create `config.py`**

```python
SHEET_ID = "your-google-sheet-id-here"

# (url, mweb_row, dweb_row)
# dweb_row=None for pages with no desktop equivalent
PAGES: list[tuple[str, int, int | None]] = [
    # --- mWeb rows 3-11 / DWeb rows 17-25 ---
    ("https://pharmeasy.in/",                               3,  17),  # Home
    ("https://pharmeasy.in/online-medicines/",              4,  18),  # Med PDP         ← fill correct URL
    ("https://pharmeasy.in/online-medicines/",              5,  19),  # PDP w/o image   ← fill correct URL
    ("https://pharmeasy.in/cart",                           6,  20),  # Cart
    ("https://pharmeasy.in/order-medicines",                7,  21),  # Order Medicine
    ("https://pharmeasy.in/health-care/",                   8,  22),  # OTC Landing
    ("https://pharmeasy.in/health-care/products/",          9,  23),  # OTC Listing     ← fill correct URL
    ("https://pharmeasy.in/health-care/products/",          10, 24),  # OTC PDP         ← fill correct URL
    ("https://pharmeasy.in/offers",                         11, 25),  # Offers
    # --- mWeb-Diagnostics rows 12-16 / DWeb-Diagnostics rows 26-29 ---
    ("https://pharmeasy.in/diagnostics/profile/408",        12, 26),  # Dx PDP Profile-408
    ("https://pharmeasy.in/diagnostics/package/2142",       13, 27),  # Dx PDP Package-2142
    ("https://pharmeasy.in/diagnostics/test/154",           14, 28),  # Dx PDP Test-154
    ("https://pharmeasy.in/diagnostics/cart",               15, 29),  # Dx Cart
    ("https://pharmeasy.in/diagnostics/tests",              16, None), # Dx Tests Local (mobile only)
]
```

- [ ] **Step 3: Create `tests/__init__.py`** (empty file)

- [ ] **Step 4: Install dependencies and verify**

```bash
pip install -r requirements.txt
python -c "import gspread, requests; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git init
git add config.py requirements.txt tests/__init__.py
git commit -m "feat: scaffold config and dependencies"
```

---

### Task 2: CrUX API module

**Files:**
- Create: `crux.py`
- Create: `tests/test_crux.py`

**Interfaces:**
- Produces: `fetch_cwv(url: str, form_factor: str, api_key: str) -> dict | None`
- Return dict shape: `{"lcp": float | str, "inp": int | str, "cls": float | str, "collection_end": date}`
- Returns `None` when CrUX has no data for the URL (404 from API)

- [ ] **Step 1: Write failing tests**

Create `tests/test_crux.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
python -m pytest tests/test_crux.py -v
```
Expected: `ModuleNotFoundError: No module named 'crux'`

- [ ] **Step 3: Create `crux.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
python -m pytest tests/test_crux.py -v
```
Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add crux.py tests/test_crux.py
git commit -m "feat: add CrUX API module"
```

---

### Task 3: Sheet utilities module

**Files:**
- Create: `sheet.py`
- Create: `tests/test_sheet.py`

**Interfaces:**
- Produces:
  - `find_last_week_col(row1: list[str]) -> int | None` — 1-based index of last date-range header
  - `find_week_col(row1: list[str], label: str) -> int | None` — 1-based index of exact label match
  - `compute_label(collection_end: date, row1: list[str]) -> tuple[str, int]` — (label, new_col_1based)
  - `add_week_headers(ws: gspread.Worksheet, label: str, col: int) -> None`
  - `write_cwv_row(ws: gspread.Worksheet, sheet_row: int, col: int, lcp, inp, cls) -> None`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sheet.py`:

```python
from datetime import date

from sheet import compute_label, find_last_week_col, find_week_col

# Mirrors actual row 1 of the sheet: col 1=empty, 2=Platform, 3=Metric,
# then week groups of 3 (label + 2 empty merged cells), then trailing cols.
_ROW1 = [
    "", "Platform", "Metric",
    "Apr 19 - Apr 25", "", "",
    "Apr 26 - May 2",  "", "",
    "July 5 - July 11", "", "",
    "", "", "", "Overall Trend",
]


def test_find_last_week_col():
    # "July 5 - July 11" is at index 9 (0-based) → 1-based = 10
    assert find_last_week_col(_ROW1) == 10


def test_find_last_week_col_empty():
    assert find_last_week_col(["", "Platform", "Metric"]) is None


def test_find_week_col_exists():
    assert find_week_col(_ROW1, "Apr 19 - Apr 25") == 4


def test_find_week_col_not_exists():
    assert find_week_col(_ROW1, "July 12 - July 18") is None


def test_compute_label_derives_start_from_last_col():
    # Last col ends "July 11" → new start = July 12
    label, new_col = compute_label(date(2025, 7, 18), _ROW1)
    assert label == "July 12 - July 18"
    assert new_col == 13  # last_col(10) + 3


def test_compute_label_fallback_when_no_prior_cols():
    label, new_col = compute_label(date(2025, 7, 18), ["", "Platform", "Metric"])
    assert label == "July 12 - July 18"
    assert new_col == 4  # first data column
```

- [ ] **Step 2: Run tests — expect failure**

```bash
python -m pytest tests/test_sheet.py -v
```
Expected: `ModuleNotFoundError: No module named 'sheet'`

- [ ] **Step 3: Create `sheet.py`**

```python
import re
from datetime import date, datetime, timedelta

import gspread
from gspread.utils import rowcol_to_a1

_DATE_RE = re.compile(r'^[A-Za-z]+ \d{1,2} - [A-Za-z]+ \d{1,2}$')


def find_last_week_col(row1: list[str]) -> int | None:
    last = None
    for i, val in enumerate(row1):
        if _DATE_RE.match(val.strip()):
            last = i + 1  # 1-based
    return last


def find_week_col(row1: list[str], label: str) -> int | None:
    for i, val in enumerate(row1):
        if val.strip() == label:
            return i + 1
    return None


def _parse_date(s: str, year: int) -> date:
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(f"{s} {year}", fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date string: '{s}'")


def _fmt(d: date) -> str:
    return d.strftime("%B %-d")  # "July 12"  (%-d = no leading zero, Linux/Mac)


def compute_label(collection_end: date, row1: list[str]) -> tuple[str, int]:
    last_col = find_last_week_col(row1)
    if last_col:
        end_str = row1[last_col - 1].split(" - ")[1].strip()
        last_end = _parse_date(end_str, collection_end.year)
        new_start = last_end + timedelta(days=1)
        new_col = last_col + 3
    else:
        new_start = collection_end - timedelta(days=6)
        new_col = 4  # column D — first data column

    return f"{_fmt(new_start)} - {_fmt(collection_end)}", new_col


def add_week_headers(ws: gspread.Worksheet, label: str, col: int) -> None:
    start_a1 = rowcol_to_a1(1, col)
    end_a1   = rowcol_to_a1(1, col + 2)
    ws.update_cell(1, col, label)
    ws.merge_cells(f"{start_a1}:{end_a1}")
    ws.batch_update([{
        "range": f"{rowcol_to_a1(2, col)}:{rowcol_to_a1(2, col + 2)}",
        "values": [["LCP", "INP", "CLS"]],
    }])


def write_cwv_row(ws: gspread.Worksheet, sheet_row: int, col: int, lcp, inp, cls) -> None:
    ws.batch_update([{
        "range": f"{rowcol_to_a1(sheet_row, col)}:{rowcol_to_a1(sheet_row, col + 2)}",
        "values": [[lcp, inp, cls]],
    }])
```

- [ ] **Step 4: Run tests — expect pass**

```bash
python -m pytest tests/test_sheet.py -v
```
Expected: 6 tests PASSED

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: 9 tests PASSED (3 from test_crux + 6 from test_sheet)

- [ ] **Step 6: Commit**

```bash
git add sheet.py tests/test_sheet.py
git commit -m "feat: add sheet utilities module"
```

---

### Task 4: Main script (tracker.py)

**Files:**
- Create: `tracker.py`

**Interfaces:**
- Consumes: `crux.fetch_cwv`, `sheet.*`, `config.SHEET_ID`, `config.PAGES`
- Consumes env vars: `PSI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`

- [ ] **Step 1: Create `tracker.py`**

```python
import json
import os
import sys

import gspread
from google.oauth2.service_account import Credentials

from config import PAGES, SHEET_ID
from crux import fetch_cwv
from sheet import add_week_headers, compute_label, find_week_col, write_cwv_row

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main() -> None:
    api_key = os.environ["PSI_API_KEY"]
    sa_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])

    creds = Credentials.from_service_account_info(sa_info, scopes=_SCOPES)
    ws = gspread.authorize(creds).open_by_key(SHEET_ID).sheet1

    # Collection period is the same across all pages — fetch from first URL
    first = fetch_cwv(PAGES[0][0], "PHONE", api_key)
    if not first:
        print("ERROR: no CrUX data for first page — aborting")
        sys.exit(1)

    collection_end = first["collection_end"]
    row1 = ws.row_values(1)
    label, new_col = compute_label(collection_end, row1)

    existing = find_week_col(row1, label)
    if existing:
        print(f"Week '{label}' already exists — overwriting values")
        new_col = existing
    else:
        print(f"Adding new week column: {label}")
        add_week_headers(ws, label, new_col)

    for url, mweb_row, dweb_row in PAGES:
        print(f"  {url}")

        mobile = fetch_cwv(url, "PHONE", api_key)
        if mobile:
            write_cwv_row(ws, mweb_row, new_col, mobile["lcp"], mobile["inp"], mobile["cls"])
        else:
            write_cwv_row(ws, mweb_row, new_col, "", "", "")

        if dweb_row is not None:
            desktop = fetch_cwv(url, "DESKTOP", api_key)
            if desktop:
                write_cwv_row(ws, dweb_row, new_col, desktop["lcp"], desktop["inp"], desktop["cls"])
            else:
                write_cwv_row(ws, dweb_row, new_col, "", "", "")

    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add tracker.py
git commit -m "feat: add main tracker script"
```

---

### Task 5: GitHub Actions workflow + README

**Files:**
- Create: `.github/workflows/cwv.yml`
- Create: `README.md`

- [ ] **Step 1: Create `.github/workflows/cwv.yml`**

```yaml
name: Core Web Vitals Tracker

on:
  schedule:
    - cron: "0 12 * * 1"   # Monday 12:00 UTC = 5:30 PM IST
  workflow_dispatch:         # allow manual trigger from GitHub UI

jobs:
  track:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - run: pip install -r requirements.txt

      - run: python tracker.py
        env:
          PSI_API_KEY: ${{ secrets.PSI_API_KEY }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
```

- [ ] **Step 2: Create `README.md`**

```markdown
# Core Web Vitals Tracker

Runs every **Monday at 5:30 PM IST** via GitHub Actions. Fetches CrUX field data (LCP, INP, CLS) from the Chrome UX Report API and writes the week's values to the "Consumer Web - Core Web Vitals" Google Sheet.

## One-Time Setup

### 1. Google Cloud — Chrome UX Report API key
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create or select a project
2. **APIs & Services → Library** → search **"Chrome UX Report API"** → Enable
3. **APIs & Services → Credentials → Create Credentials → API Key**
4. Copy the key — this becomes the `PSI_API_KEY` GitHub secret

### 2. Google Sheets API — Service Account
1. In the same project, **APIs & Services → Library** → search **"Google Sheets API"** → Enable
2. **APIs & Services → Credentials → Create Credentials → Service Account**
3. Give it any name (e.g. `cwv-tracker`) → Done
4. Click the service account → **Keys tab → Add Key → Create new key → JSON** → Download
5. The full contents of this JSON file become the `GOOGLE_SERVICE_ACCOUNT_JSON` GitHub secret

### 3. Share the Google Sheet with the service account
1. Open your "Consumer Web - Core Web Vitals" Google Sheet
2. **Share** → paste the service account email (found in the JSON under `"client_email"`)
3. Set access to **Editor**
4. Copy the **Sheet ID** from the URL:
   `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`

### 4. Add GitHub Secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|-------------|-------|
| `PSI_API_KEY` | API key from step 1 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON contents from step 2 |

### 5. Fill in config.py
- Replace `your-google-sheet-id-here` with the Sheet ID from step 3
- Replace placeholder URLs with the actual pharmeasy.in page URLs

### 6. Push to GitHub
```bash
gh repo create performance-tracker-automation --private --source=. --push
```
The workflow runs automatically every Monday at 5:30 PM IST.

## Manual trigger
Repo → **Actions → Core Web Vitals Tracker → Run workflow**

Or via CLI: `gh workflow run cwv.yml`

## Re-run safety
The script detects the existing week column on re-runs and overwrites values without duplicating headers.
```

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/cwv.yml README.md
git commit -m "feat: add GitHub Actions workflow and README"
```

- [ ] **Step 4: Create GitHub repo and push**

```bash
gh repo create performance-tracker-automation --private --source=. --push
```
Expected: repo created, code pushed

- [ ] **Step 5: Add secrets**

```bash
gh secret set PSI_API_KEY
# paste API key when prompted

gh secret set GOOGLE_SERVICE_ACCOUNT_JSON
# paste the full contents of the service account JSON when prompted
```

- [ ] **Step 6: Trigger manual run and verify**

```bash
gh workflow run cwv.yml
gh run list --workflow=cwv.yml
```
Expected: run status shows `completed` ✓. Check the Google Sheet — new week column should be populated.
```
