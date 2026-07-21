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
    ws = gspread.Client(auth=creds).open_by_key(SHEET_ID).sheet1

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
