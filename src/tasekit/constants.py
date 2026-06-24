"""Constants for the TASE API."""

# ---------------------------------------------------------------------------
# API base URLs
# ---------------------------------------------------------------------------
BASE_URL = "https://api.tase.co.il/api"
MAYA_BASE_URL = "https://maya.tase.co.il/api/v1"

# ---------------------------------------------------------------------------
# Default HTTP headers required by the TASE API
# ---------------------------------------------------------------------------
DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.4 Safari/605.1.15"
    ),
    "Origin": "https://market.tase.co.il",
    "Referer": "https://market.tase.co.il/",
    "Accept-Language": "en-US",
}

# ---------------------------------------------------------------------------
# pType mapping — maps a *requested* number of years to the smallest TASE
# pType value that covers at least that many years.
#
# pType values:
#   0 = 1 day, 1 = 1 month, 2 = 3 months, 3 = 6 months,
#   4 = 1 year, 5 = 2 years, 6 = 3 years, 7 = 5 years
# ---------------------------------------------------------------------------
PTYPE_MAP: dict[int, int] = {
    0: 0,  # < 1 month  → 1 day
    1: 4,  # 1 year
    2: 5,  # 2 years
    3: 6,  # 3 years
    4: 7,  # 4 years → 5 years (next available)
    5: 7,  # 5 years (max)
}

# Maximum years the API can return.
MAX_HISTORY_YEARS = 5

# Maya fundTypeId for mutual hedge funds (קרן גידור בנאמנות).
MAYA_HEDGE_FUND_TYPE_ID = 6

# Maximum pageSize accepted by the Maya hedge-fund history endpoint.
MAYA_HEDGE_MAX_PAGE_SIZE = 30

# Default history span when the caller does not specify years or start/end.
DEFAULT_HISTORY_YEARS = 2

# ---------------------------------------------------------------------------
# pType mapping (days) — for requests specified in days rather than years.
# Maps a number of days to the smallest pType that covers it.
# ---------------------------------------------------------------------------
PTYPE_DAYS_THRESHOLDS: list[tuple[int, int]] = [
    # (max_days, ptype)
    (1, 0),      # 1 day
    (30, 1),     # 1 month
    (90, 2),     # 3 months
    (180, 3),    # 6 months
    (365, 4),    # 1 year
    (730, 5),    # 2 years
    (1095, 6),   # 3 years
    (1825, 7),   # 5 years
]

# ---------------------------------------------------------------------------
# Maya API headers (different Origin from the main API)
# ---------------------------------------------------------------------------
MAYA_HEADERS: dict[str, str] = {
    "User-Agent": DEFAULT_HEADERS["User-Agent"],
    "Origin": "https://maya.tase.co.il",
    "Referer": "https://maya.tase.co.il/",
    "Accept-Language": "he-IL",
}

# ---------------------------------------------------------------------------
# Column name prefixes for CSV export endpoints.
#
# With ``Accept-Language: en-US`` the API returns English column headers.
# We match with str.startswith() for robustness.
# ---------------------------------------------------------------------------
COL_DATE = "Date"
COL_ADJ_CLOSE = "Adjusted Closing Price"
COL_CLOSE = "Closing Price"  # the unadjusted column includes "(0.01 ILS)"
COL_OPEN = "Opening Price"
COL_HIGH = "High Price"
COL_LOW = "Low Price"
COL_VOLUME_UNITS = "Volume"
COL_VOLUME_TRADE = "Turnover"

# ETF-specific column name prefixes (English)
COL_PURCHASE_PRICE = "Purchase Price"
COL_REDEMPTION_PRICE = "Redemption Price"
COL_UNIT_PRICE = "Unit Price"
COL_MANAGEMENT_FEE = "Management Fee"
COL_TRUSTEE_FEE = "Trustee Fee"
COL_MARKET_CAP = "Market Cap"
