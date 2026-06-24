"""The :class:`HedgeFund` class — mutual hedge funds (קרן גידור בנאמנות)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from tasekit.api import TaseClient, get_default_client
from tasekit.constants import MAYA_HEDGE_MAX_PAGE_SIZE
from tasekit.exceptions import SecurityNotFoundError, TaseNetworkError, TaseParsingError
from tasekit.parsers import (
    add_hedge_fund_adj_close,
    parse_hedge_fund_history,
    parse_hedge_fund_list,
)

# Far-past sentinel used to request a series' full life when no start is given.
_INCEPTION_SENTINEL = "2000-01-01"


class HedgeFund:
    """Represents a mutual hedge fund (קרן גידור בנאמנות) on the Maya API.

    Unlike ordinary securities, a hedge fund mints a **new monthly security
    ID** for each subscription month, and at year-end crystallizes fees by
    converting all holdings into the oldest series.  The oldest series is
    therefore a continuous, full-life price anchor.  See
    :func:`~tasekit.parsers.add_hedge_fund_adj_close` for the fee mechanics.

    Hedge funds are not exchange traded and are not discoverable via the main
    TASE API (``company/securitydata`` returns ``null``), so use this class
    explicitly::

        fund = tasekit.HedgeFund("1194141")
        perf = fund.performance()      # net-of-fees total-return series

    Args:
        fund_id: Numeric Maya fund ID (e.g. ``"1194141"``).
        client: Optional :class:`~tasekit.api.TaseClient`.  Defaults to the
            module-level shared client.
    """

    def __init__(self, fund_id: str, *, client: TaseClient | None = None) -> None:
        self._id = self._normalize_id(fund_id)
        self._client = client or get_default_client()
        self._series_cache: list[dict] | None = None
        self._anchor_history_cache: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """The numeric (unpadded) Maya fund ID."""
        return self._id

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def list(cls, *, client: TaseClient | None = None) -> pd.DataFrame:
        """List every mutual hedge fund traded on TASE (via Maya).

        Paginates the ``funds/hedge`` listing (the source behind
        ``maya.tase.co.il/he/funds/hedge-funds``) until all funds are
        collected.

        Args:
            client: Optional :class:`~tasekit.api.TaseClient`.  Defaults to the
                module-level shared client.

        Returns:
            DataFrame indexed by ``Fund ID`` with columns ``Name``,
            ``Manager``, ``Trustee``, ``Management Fee``, ``Success Fee``,
            ``Trustee Fee``, ``AUM`` (NIS millions), ``Tax Status`` and
            ``Classification``.

        Raises:
            SecurityNotFoundError: If the listing is empty.
        """
        client = client or get_default_client()
        rows: list[dict] = []
        page = 1
        while True:
            page_rows = client.fetch_hedge_fund_list(
                page_size=MAYA_HEDGE_MAX_PAGE_SIZE, page_number=page
            )
            if not page_rows:
                break
            rows.extend(page_rows)
            if len(page_rows) < MAYA_HEDGE_MAX_PAGE_SIZE:
                break
            page += 1

        try:
            return parse_hedge_fund_list(rows)
        except TaseParsingError as exc:
            raise SecurityNotFoundError("No hedge funds found") from exc

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def series(self) -> list[dict]:
        """Return every monthly series of the fund, oldest first.

        Returns:
            A list of ``{"security_id": str, "label": str}`` dicts sorted
            ascending by series ID (the lowest ID is the oldest anchor).
        """
        if self._series_cache is None:
            meta = self._client.fetch_hedge_fund_metadata(self._id)
            securities = meta.get("securities") or []
            self._series_cache = sorted(
                (
                    {"security_id": str(s["key"]), "label": s.get("value", "")}
                    for s in securities
                ),
                key=lambda s: int(s["security_id"]),
            )
        return self._series_cache

    def anchor_id(self) -> str:
        """Return the oldest series ID (the fund's performance anchor)."""
        series = self.series()
        if not series:
            raise SecurityNotFoundError(
                f"No series found for hedge fund {self._id}"
            )
        return series[0]["security_id"]

    def info(self) -> dict:
        """Fetch fund metadata: fees, redemption schedule, current series.

        Returns:
            A flattened dict of the ``funds/hedge/{id}`` detail.

        Raises:
            SecurityNotFoundError: If the fund is not found on Maya.
        """
        try:
            data = self._client.fetch_hedge_fund_detail(self._id)
        except TaseNetworkError as exc:
            raise SecurityNotFoundError(
                f"No info found for hedge fund {self._id}"
            ) from exc
        return self._format_info(data)

    def redemption_snapshot(self) -> pd.DataFrame:
        """Return the current redemption snapshot (all live series, latest date).

        Returns:
            DataFrame indexed by series ID with columns ``Date``, ``Gross``,
            ``Net``.
        """
        rows = self._client.fetch_hedge_fund_history(self._id)
        df = parse_hedge_fund_history(rows)
        # Re-index by the redeemable security ID for a snapshot view.
        ids = [str(r["fundId"]).lstrip("0") for r in rows]
        df = df.reset_index()
        df["Security ID"] = ids
        return df.set_index("Security ID")

    def history(
        self,
        *,
        security_id: str | int | None = None,
        years: int | None = None,
        days: int | None = None,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch the monthly price history for one series of the fund.

        Args:
            security_id: A specific monthly series ID.  Defaults to the oldest
                series (:meth:`anchor_id`), which spans the fund's whole life.
            years: Years of history (used when *start* is not given).
            days: Days of history (takes precedence over *years*).
            start: Start date (inclusive).  ``"YYYY-MM-DD"`` or ``datetime``.
            end: End date (inclusive).  Defaults to today.

        Returns:
            DataFrame with a ``DatetimeIndex`` ("Date") and columns
            ``Gross``, ``Net`` and ``Adj Close`` (the continuous, fee-adjusted
            net price).

            .. warning::
                The raw ``Net`` column contains the unadjusted redemption
                price and includes an upward jump at every year-end
                crystallization.  It is **not** suitable for computing returns
                — use ``Adj Close`` (reset-adjusted) for net performance and
                ``Gross`` for gross performance.

        Raises:
            SecurityNotFoundError: If the series has no data.
        """
        sec_id = str(security_id) if security_id is not None else self.anchor_id()
        from_iso, to_iso, to_dt = self._resolve_window(
            years=years, days=days, start=start, end=end
        )

        rows = self._paginate_history(sec_id, from_iso, to_iso)
        try:
            df = parse_hedge_fund_history(rows)
        except TaseParsingError as exc:
            raise SecurityNotFoundError(
                f"No history found for hedge-fund series {sec_id}"
            ) from exc

        df = add_hedge_fund_adj_close(df)
        df = self._trim_dates(df, years=years, days=days, start=start, end=end)
        return df

    def performance(self, *, net: bool = True) -> pd.DataFrame:
        """Return the fund's full-life performance series from the anchor.

        Args:
            net: When ``True`` (default) return the net-of-fees total-return
                series (reset-adjusted ``Adj Close``).  When ``False`` return
                the gross (fee-free) ``Gross`` series.

        Returns:
            DataFrame with a ``DatetimeIndex`` ("Date") and a single
            ``Performance`` column.

        Note:
            The full-life anchor history is fetched once and cached on the
            instance, so calling ``performance(net=True)`` and
            ``performance(net=False)`` costs a single fetch.
        """
        df = self._anchor_history()
        col = "Adj Close" if net else "Gross"
        return df[[col]].rename(columns={col: "Performance"})

    def _anchor_history(self) -> pd.DataFrame:
        """Return the full-life anchor history, cached on the instance."""
        if self._anchor_history_cache is None:
            self._anchor_history_cache = self.history()
        return self._anchor_history_cache

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _paginate_history(
        self, security_id: str, from_iso: str, to_iso: str
    ) -> list[dict]:
        """Accumulate all history pages for *security_id*."""
        rows: list[dict] = []
        page = 1
        while True:
            page_rows = self._client.fetch_hedge_fund_history(
                self._id,
                security_id=security_id,
                from_date=from_iso,
                to_date=to_iso,
                page_size=MAYA_HEDGE_MAX_PAGE_SIZE,
                page_number=page,
            )
            if not page_rows:
                break
            rows.extend(page_rows)
            if len(page_rows) < MAYA_HEDGE_MAX_PAGE_SIZE:
                break
            page += 1
        return rows

    @staticmethod
    def _resolve_window(
        *,
        years: int | None,
        days: int | None,
        start: str | datetime | None,
        end: str | datetime | None,
    ) -> tuple[str, str, pd.Timestamp]:
        """Resolve the (from_iso, to_iso, to_dt) request window."""
        to_dt = pd.Timestamp(end) if end else pd.Timestamp.now()
        if start is not None:
            from_dt = pd.Timestamp(start)
        elif days is not None:
            from_dt = to_dt - timedelta(days=days)
        elif years is not None:
            from_dt = to_dt - timedelta(days=years * 365)
        else:
            # No window given -> fetch the series' whole life.
            from_dt = pd.Timestamp(_INCEPTION_SENTINEL)

        fmt = "%Y-%m-%dT00:00:00.000Z"
        return from_dt.strftime(fmt), to_dt.strftime(fmt), to_dt

    @staticmethod
    def _trim_dates(
        df: pd.DataFrame,
        *,
        years: int | None,
        days: int | None,
        start: str | datetime | None,
        end: str | datetime | None,
    ) -> pd.DataFrame:
        """Trim *df* to the requested window (Adj Close stays anchored to full life)."""
        if start is not None:
            df = df[df.index >= pd.Timestamp(start)]
        elif days is not None and days > 0 and not df.empty:
            df = df[df.index >= df.index.max() - timedelta(days=days)]
        elif years is not None and years > 0 and not df.empty:
            df = df[df.index >= df.index.max() - timedelta(days=years * 365)]
        if end is not None:
            df = df[df.index <= pd.Timestamp(end)]
        return df

    @staticmethod
    def _format_info(data: dict) -> dict:
        """Flatten the ``funds/hedge/{id}`` JSON into a user-friendly dict."""
        result: dict = {
            "fund_id": data.get("fundId"),
            "name": data.get("name"),
            "long_name": data.get("longName"),
            "fund_type": data.get("fundType"),
            "manager": data.get("managerName"),
            "trustee": data.get("trusteeName"),
            "management_fee": data.get("managementFee"),
            "trustee_fee": data.get("trusteeFee"),
            "success_fee": data.get("successFee"),
            "aum_nis_millions": data.get("assetValueNISMillions"),
            "aum_as_of": data.get("assetValueAsOf"),
            "tax_status": data.get("taxStatusName"),
        }

        redemption = {
            "period": data.get("redemptionPeriodName"),
            "first_or_last": data.get("redemptionFirstOrLast"),
            "days": data.get("redemptionDays"),
        }
        if any(redemption.values()):
            result["redemption"] = redemption

        cls = data.get("classification", {})
        if cls:
            result["classification"] = {
                "major": cls.get("major"),
                "main": cls.get("main"),
                "secondary": cls.get("secondary"),
            }

        redemptions = data.get("securityRedemptions") or []
        if redemptions:
            result["current_series"] = [
                {
                    "security_id": str(r.get("securityId")),
                    "name": r.get("securityName"),
                    "created": r.get("createdDate"),
                    "net": r.get("nav"),
                    "gross": r.get("gav"),
                }
                for r in redemptions
            ]

        return result

    @staticmethod
    def _normalize_id(fund_id: str) -> str:
        """Validate and normalise a numeric fund ID (strip leading zeros)."""
        if not fund_id.isdigit():
            raise ValueError(
                f"Invalid hedge-fund ID: {fund_id!r} (must be numeric)"
            )
        return fund_id.lstrip("0") or "0"
