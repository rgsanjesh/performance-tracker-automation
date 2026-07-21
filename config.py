SHEET_ID = "1t7C5a_6Q1OJ_cOXXpbD50DBr8CdSbN-QdIs6LrDwIQY"

# (url, mweb_row, dweb_row)
# dweb_row=None for pages with no desktop equivalent
PAGES: list[tuple[str, int, int | None]] = [
    # --- mWeb rows 3-11 / DWeb rows 17-25 ---
    ("https://pharmeasy.in/",                               3,  17),  # Home
    ("https://pharmeasy.in/online-medicine-order/dolo-650mg-strip-of-15-tablets-44140/",              4,  18),  # Med PDP         <- fill correct URL
    ("https://pharmeasy.in/online-medicine-order/deworm-400mg-tab-43305/",              5,  19),  # PDP w/o image   <- fill correct URL
    ("https://pharmeasy.in/cart",                           6,  20),  # Cart
    ("https://pharmeasy.in/online-medicine-order",                7,  21),  # Order Medicine
    ("https://pharmeasy.in/health-care/",                   8,  22),  # OTC Landing
    ("https://pharmeasy.in/health-care/skin-care-93/",          9,  23),  # OTC Listing     <- fill correct URL
    ("https://pharmeasy.in/health-care/products/prega-news-pregnancy-test-kit-177505",          10, 24),  # OTC PDP         <- fill correct URL
    ("https://pharmeasy.in/offers",                         11, 25),  # Offers
    # --- mWeb-Diagnostics rows 12-16 / DWeb-Diagnostics rows 26-29 ---
    ("https://pharmeasy.in/diagnostics/profile/408",        12, 26),  # Dx PDP Profile-408
    ("https://pharmeasy.in/diagnostics/package/2142",       13, 27),  # Dx PDP Package-2142
    ("https://pharmeasy.in/diagnostics/test/154",           14, 28),  # Dx PDP Test-154
    ("https://pharmeasy.in/diagnostics/cart",               15, 29),  # Dx Cart
    ("https://pharmeasy.in/diagnostics/tests",              16, None), # Dx Tests Local (mobile only)
]
