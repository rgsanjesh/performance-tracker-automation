# Core Web Vitals Tracker — Design Spec

**Date:** 2026-07-21  
**Status:** Approved

---

## Overview

Automate weekly Core Web Vitals (LCP, INP, CLS) data entry into the "Consumer Web - Core Web Vitals" Google Sheet. Currently done manually every Monday by fetching CrUX field data from PageSpeed Insights. A GitHub Actions cron job replaces the manual process entirely.

---

## Files

```
performance-tracker-automation/
├── tracker.py                   # main script
├── config.py                    # page URLs + sheet row mappings
├── requirements.txt             # gspread, requests
└── .github/workflows/
    └── cwv.yml                  # cron: Monday 5:30 PM IST (12:00 UTC)
```

---

## Config (`config.py`)

```python
SHEET_ID = "your-google-sheet-id-here"

# (url, mweb_row, dweb_row)
# dweb_row=None for pages with no desktop equivalent
PAGES = [
    ("https://pharmeasy.in/...", 3,  17),  # Home
    ("https://pharmeasy.in/...", 4,  18),  # Med PDP
    # ... fill in URLs when available
    ("https://pharmeasy.in/...", 16, None), # Dx Tests Local (mobile only)
]
```

User fills in URLs; everything else is wired.

---

## Data Flow

1. Script starts, opens Google Sheet via service account credentials
2. Calls PSI API for the first URL → extracts `collectionPeriod.lastDate` (CrUX end date)
3. Reads row 1 of sheet → parses the last existing week column's end date
4. Computes new column label: `start = last_end_date + 1 day`, `end = collectionPeriod.lastDate`
   - Fallback if no prior columns: `start = lastDate - 6 days`
5. If that label already exists in row 1 → skip header creation (safe re-run)
6. If new → appends 3 columns: merged date range in row 1, LCP/INP/CLS in row 2
7. For each page in `PAGES`:
   - Calls PSI API with `strategy=MOBILE` → writes p75 LCP, INP, CLS to `mweb_row`
   - Calls PSI API with `strategy=DESKTOP` → writes to `dweb_row` (skips if `None`)
8. Done

---

## PSI API — CrUX Extraction

Endpoint: `https://www.googleapis.com/pagespeedonline/v5/runPagespeed`  
Params: `url`, `strategy` (`MOBILE`/`DESKTOP`), `key`

Values extracted from `loadingExperience.metrics` at p75:

| Sheet column | API field                          | Transform         |
|-------------|-------------------------------------|-------------------|
| LCP         | `LARGEST_CONTENTFUL_PAINT_MS`       | ÷ 1000 (seconds)  |
| INP         | `INTERACTION_TO_NEXT_PAINT`         | ms, as-is         |
| CLS         | `CUMULATIVE_LAYOUT_SHIFT_SCORE`     | raw decimal       |

If a page has no CrUX data (low traffic), write empty string — no crash.

---

## Sheet Column Detection

Row 1 holds merged date range headers (`"July 12 - July 18"`), spanning 3 columns each.  
Row 2 holds sub-headers (`LCP`, `INP`, `CLS`) repeated per week.  
Data starts row 3.

The script always appends to the right of the last filled column — never overwrites existing data.

---

## GitHub Actions (`cwv.yml`)

- **Schedule:** `0 12 * * 1` (Monday 12:00 UTC = 5:30 PM IST)
- **Secrets required:**
  - `PSI_API_KEY` — PageSpeed Insights API key
  - `GOOGLE_SERVICE_ACCOUNT_JSON` — full service account JSON (editor on the sheet)

---

## One-Time Setup (documented in README)

1. Google Cloud Console → create project → enable **PageSpeed Insights API** → create API key → save as `PSI_API_KEY` secret
2. Same project → enable **Google Sheets API** → create service account → download JSON → save as `GOOGLE_SERVICE_ACCOUNT_JSON` secret
3. Open your Google Sheet → Share → add the service account email → Editor
4. Copy Sheet ID from the sheet URL → paste into `config.py`
5. Fill in page URLs in `config.py`

---

## Edge Cases

| Case | Behaviour |
|------|-----------|
| Page has no CrUX data | Write empty string, continue |
| Week column already exists (re-run) | Skip header creation, overwrite values |
| `dweb_row` is `None` | Skip desktop API call for that page |
| API rate limit / network error | Script fails, GitHub Actions marks run as failed + emails owner |
