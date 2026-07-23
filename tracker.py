import json
import os

import gspread
from google.oauth2.service_account import Credentials

from config import PAGES, SHEET_ID
from crux import fetch_cwv, get_collection_end
from notify import send_report
from sheet import add_week_headers, color_cwv_row, compute_label, find_week_col, write_cwv_row

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def main() -> None:
    api_key = os.environ["PSI_API_KEY"]
    sa_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])

    creds = Credentials.from_service_account_info(sa_info, scopes=_SCOPES)
    ws = gspread.Client(auth=creds).open_by_key(SHEET_ID).sheet1

    collection_end = get_collection_end(api_key)
    row1 = ws.row_values(1)
    label, new_col = compute_label(collection_end, row1)

    existing = find_week_col(row1, label)
    if existing:
        print(f"Week '{label}' already exists — overwriting values")
        new_col = existing
    else:
        print(f"Adding new week column: {label}")
        add_week_headers(ws, label, new_col)

    notify_results = []

    for url, name, mweb_row, dweb_row in PAGES:
        print(f"  {url}")

        mobile = fetch_cwv(url, "MOBILE", api_key)
        m = mobile or {"lcp": "", "inp": "", "cls": ""}
        write_cwv_row(ws, mweb_row, new_col, m["lcp"], m["inp"], m["cls"])
        color_cwv_row(ws, mweb_row, new_col, m["lcp"], m["inp"], m["cls"])

        desktop = None
        if dweb_row is not None:
            desktop = fetch_cwv(url, "DESKTOP", api_key)
            d = desktop or {"lcp": "", "inp": "", "cls": ""}
            write_cwv_row(ws, dweb_row, new_col, d["lcp"], d["inp"], d["cls"])
            color_cwv_row(ws, dweb_row, new_col, d["lcp"], d["inp"], d["cls"])

        notify_results.append({"name": name, "url": url, "mobile": mobile, "desktop": desktop})

    send_report(label, notify_results)
    print("Done.")


if __name__ == "__main__":
    main()
