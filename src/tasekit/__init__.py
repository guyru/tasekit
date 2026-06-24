"""tasekit — Fetch financial data from the Tel Aviv Stock Exchange (TASE)."""

from tasekit._version import __version__
from tasekit.security import Security
from tasekit.hedge_fund import HedgeFund
from tasekit.index import Index
from tasekit.exceptions import (
    TaseError,
    TaseNetworkError,
    TaseParsingError,
    SecurityNotFoundError,
)

import pandas as pd


def download(
    security_id: str,
    *,
    years: int | None = None,
    days: int | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Convenience function: fetch historical EOD data for a security.

    Args:
        security_id: TASE security ID (e.g., "00604611").
        years: Number of years of history (default 2). Ignored if *start* is given.
        days: Number of calendar days of history. Ignored if *start* is given.
            Takes precedence over *years*.
        start: Start date (inclusive), "YYYY-MM-DD".
        end: End date (inclusive), "YYYY-MM-DD". Defaults to today.

    Returns:
        DataFrame with DatetimeIndex and columns:
        Open, High, Low, Close, Adj Close, Volume
        (or just Close for mutual funds).
    """
    return Security(security_id).history(
        years=years, days=days, start=start, end=end
    )


__all__ = [
    "__version__",
    "Security",
    "HedgeFund",
    "Index",
    "download",
    "TaseError",
    "TaseNetworkError",
    "TaseParsingError",
    "SecurityNotFoundError",
]
