from datetime import date

from sheet import compute_label, find_last_week_col, find_week_col

# Mirrors actual row 1: col 1=empty, 2=Platform, 3=Metric,
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
