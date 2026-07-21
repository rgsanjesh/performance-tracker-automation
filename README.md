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
2. Click **Share** → paste the service account email (found in the JSON under `"client_email"`)
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
- Replace placeholder URLs with the actual pharmeasy.in page URLs (lines marked `<- fill correct URL`)

### 6. Push to GitHub

```bash
gh repo create performance-tracker-automation --private --source=. --push
```

The workflow runs automatically every Monday at 5:30 PM IST.

## Manual trigger

GitHub repo → **Actions → Core Web Vitals Tracker → Run workflow**

Or via CLI:
```bash
gh workflow run cwv.yml
gh run list --workflow=cwv.yml
```

## Re-run safety

The script detects an existing week column on re-runs and overwrites values without duplicating headers.

## Local development

```bash
uv venv .venv
uv pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
```
