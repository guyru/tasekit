"""The :class:`Index` class — TASE market index."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from tasekit.api import TaseClient, _ptype_for_days, _ptype_for_years, get_default_client
from tasekit.constants import DEFAULT_HISTORY_YEARS
from tasekit.exceptions import SecurityNotFoundError, TaseParsingError
from tasekit.parsers import parse_index_eod_csv


class Index:
    """Represents a TASE market index (e.g. TA-35, TA-125).

    Example::

        idx = tasekit.Index("142")       # TA-35
        df = idx.history(years=3)
        info = idx.info()

    Args:
        index_id: TASE index ID (e.g. ``"142"`` for TA-35).
        client: Optional :class:`~tasekit.api.TaseClient`.
    """

    def __init__(self, index_id: str, *, client: TaseClient | None = None) -> None:
        if not index_id.isdigit():
            raise ValueError(
                f"Invalid TASE index ID: {index_id!r} (must be numeric)"
            )
        self._id = index_id
        self._client = client or get_default_client()

    @property
    def id(self) -> str:
        """The TASE index ID."""
        return self._id

    def history(
        self,
        *,
        years: int | None = None,
        days: int | None = None,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch historical end-of-day data for this index.

        Args:
            years: How many years of history (max 5). Default 2.
            days: Calendar days of history. Takes precedence over *years*.
            start: Start date (inclusive), ``"YYYY-MM-DD"`` or datetime.
            end: End date (inclusive). Defaults to today.

        Returns:
            DataFrame with ``DatetimeIndex`` ("Date") and columns:
            ``Open`` (base rate), ``Close`` (closing rate), ``Market Cap``.

        Raises:
            SecurityNotFoundError: If the index returns no data.
        """
        ptype = self._resolve_ptype(years=years, days=days, start=start)
        csv_text = self._client.fetch_index_eod_csv(self._id, ptype)

        try:
            df = parse_index_eod_csv(csv_text)
        except TaseParsingError as exc:
            raise SecurityNotFoundError(
                f"No data found for index {self._id}"
            ) from exc

        if df.empty:
            raise SecurityNotFoundError(
                f"No data found for index {self._id}"
            )

        df = self._trim_dates(df, years=years, days=days, start=start, end=end)

        if df.empty:
            raise SecurityNotFoundError(
                f"No data for index {self._id} in the requested range"
            )

        return df

    def info(self) -> dict:
        """Fetch metadata for this index.

        Returns:
            dict with index name, description, rates, yields, market value, etc.
        """
        data = self._client.fetch_index_details(self._id)

        if not data.get("Name"):
            raise SecurityNotFoundError(
                f"No info found for index {self._id}"
            )

        return {
            "id": data.get("Id"),
            "name": data.get("Name"),
            "description": data.get("Description"),
            "last_rate": data.get("LastRate"),
            "change_pct": data.get("Change"),
            "base_rate": data.get("BaseRate"),
            "open_rate": data.get("OpenRate"),
            "high_rate": data.get("HighRate"),
            "low_rate": data.get("LowRate"),
            "month_yield": data.get("MonthYield"),
            "annual_yield": data.get("AnnualYield"),
            "market_value": data.get("MarketValue"),
            "market_value_date": data.get("MarketValueDate"),
            "trade_date": data.get("TradeDate"),
            "is_bond": data.get("IsBond"),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_ptype(
        *,
        years: int | None,
        days: int | None,
        start: str | datetime | None,
    ) -> int:
        if start is not None:
            delta = (pd.Timestamp.now() - pd.Timestamp(start)).days
            return _ptype_for_days(max(1, delta))
        if days is not None:
            return _ptype_for_days(max(1, days))
        if years is None:
            years = DEFAULT_HISTORY_YEARS
        return _ptype_for_years(years)

    @staticmethod
    def _trim_dates(
        df: pd.DataFrame,
        *,
        years: int | None,
        days: int | None,
        start: str | datetime | None,
        end: str | datetime | None,
    ) -> pd.DataFrame:
        if start is not None:
            df = df[df.index >= pd.Timestamp(start)]
        elif days is not None and days > 0 and not df.empty:
            cutoff = df.index.max() - timedelta(days=days)
            df = df[df.index >= cutoff]
        elif years is not None and years > 0 and not df.empty:
            cutoff = df.index.max() - timedelta(days=years * 365)
            df = df[df.index >= cutoff]

        if end is not None:
            df = df[df.index <= pd.Timestamp(end)]

        return df
