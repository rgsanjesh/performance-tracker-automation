import re
from datetime import date, datetime, timedelta

import gspread
from gspread.utils import rowcol_to_a1, a1_range_to_grid_range

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
    return d.strftime("%B %-d")  # "July 12" — no leading zero (Linux/Mac)


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


def _rgb(r: int, g: int, b: int) -> dict:
    return {"red": r / 255, "green": g / 255, "blue": b / 255}

_GREEN = _rgb(39,  78, 19)   # Dark green 1 #274E13
_RED   = _rgb(153,  0,  0)   # Dark red 1   #990000
_BLACK = _rgb(0,    0,  0)   # default text


def _cwv_color(value, metric: str) -> dict:
    if not isinstance(value, (int, float)):
        return _BLACK
    good = (
        (metric == "lcp" and value <= 2.5) or
        (metric == "inp" and value <= 200) or
        (metric == "cls" and value <= 0.1)
    )
    return _GREEN if good else _RED


def color_cwv_row(ws: gspread.Worksheet, sheet_row: int, col: int, lcp, inp, cls) -> None:
    pairs = [(lcp, "lcp"), (inp, "inp"), (cls, "cls")]
    # foregroundColorStyle takes precedence over foregroundColor in the Sheets API.
    # Must set foregroundColorStyle with explicit dot-notation fields mask.
    requests = [
        {
            "repeatCell": {
                "range": a1_range_to_grid_range(rowcol_to_a1(sheet_row, col + i), ws.id),
                "cell": {"userEnteredFormat": {"textFormat": {"foregroundColorStyle": {"rgbColor": _cwv_color(val, metric)}}}},
                "fields": "userEnteredFormat.textFormat.foregroundColorStyle",
            }
        }
        for i, (val, metric) in enumerate(pairs)
    ]
    ws._spreadsheet.batch_update({"requests": requests})
